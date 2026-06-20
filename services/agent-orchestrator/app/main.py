"""X-8G2T Agent Orchestrator - FastAPI entrypoint.

Exposes the multi-agent system, the RAG pipeline and direct inference helpers.
All model compute happens on the Jetson GPU via the llama.cpp servers; this
service is the coordination/brain layer.
"""
from __future__ import annotations

import time
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, File, Form, HTTPException, UploadFile
from fastapi.responses import HTMLResponse
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
from loguru import logger
from pydantic import BaseModel, Field

from . import __version__
from .agents.definitions import spc_agent
from .agents.supervisor import run_supervised
from .core import db, mcp_client
from .core.config import settings
from .core.llm_clients import embedder, health, llm, vlm
from .rag.retriever import retrieve
from .rag.vectorstore import vector_store
from .tools import spc_tools  # noqa: F401  (import registers SPC tools)
from .tools.registry import query_telemetry

security = HTTPBearer(auto_error=False)


def auth(cred: HTTPAuthorizationCredentials | None = Depends(security)) -> None:
    if not settings.ai_api_key:        # auth disabled if no key configured
        return
    if cred is None or cred.credentials != settings.ai_api_key:
        raise HTTPException(status_code=401, detail="Invalid or missing API key")


@asynccontextmanager
async def lifespan(app: FastAPI):
    await db.connect()
    try:
        await vector_store.ensure_collection()
    except Exception as exc:  # noqa: BLE001
        logger.warning(f"Qdrant not ready yet: {exc}")
    logger.info("Agent Orchestrator started")
    yield
    await db.close()


app = FastAPI(
    title="X-8G2T Agent Orchestrator",
    description="Agentic edge-AI with RAG for IoT telemetry analysis on Jetson",
    version=__version__,
    lifespan=lifespan,
)


# =============================================================================
# Schemas
# =============================================================================
class InvestigateRequest(BaseModel):
    objective: str = Field(..., description="What you want the agents to do")
    device_id: str | None = Field(None, description="optional device external id")
    triggered_by: str = "api"


class RagSearchRequest(BaseModel):
    query: str
    device_id: str | None = None
    top_k: int | None = None


class TimeseriesRequest(BaseModel):
    device_id: str
    values: list[float]
    threshold: float = 3.0


class SpcAnalyzeRequest(BaseModel):
    device_id: str | None = None
    metric: str | None = None
    values: list[float] | None = Field(None, description="explicit data; else pulled from IoTDB")
    limit: int = 100
    subgroup_size: int = 1
    usl: float | None = None
    lsl: float | None = None
    target: float | None = None
    interpret: bool = True       # run the SPC agent for a grounded narrative


# =============================================================================
# System endpoints
# =============================================================================
@app.get("/")
async def root():
    return {"service": "x-8g2t-agent-orchestrator", "version": __version__,
            "docs": "/docs"}


@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "components": {
            "llm": await health(settings.llm_base_url),
            "vlm": await health(settings.vlm_base_url),
            "embeddings": await health(settings.embed_base_url),
            "qdrant_vectors": await vector_store.count(),
            "spc_mcp_tools": await mcp_client.healthy(),
        },
    }


# =============================================================================
# Agentic endpoint
# =============================================================================
@app.post("/agent/investigate", dependencies=[Depends(auth)])
async def investigate(req: InvestigateRequest):
    """Run the supervisor + specialist agents on an objective."""
    objective = req.objective
    if req.device_id:
        objective = f"[device: {req.device_id}] {objective}"

    run_id = await db.create_run(objective, req.device_id, req.triggered_by)
    start = time.time()
    try:
        answer, steps = await run_supervised(objective, run_id)
        status = "done"
    except Exception as exc:  # noqa: BLE001
        logger.exception("agent run failed")
        answer, steps, status = f"Agent run failed: {exc}", [], "failed"
    duration = int((time.time() - start) * 1000)
    await db.finish_run(run_id, answer, status, len(steps), duration)

    return {
        "run_id": run_id,
        "status": status,
        "answer": answer,
        "duration_ms": duration,
        "trace": [
            {"step": s.index, "agent": s.agent, "thought": s.thought,
             "tool": s.tool, "tool_input": s.tool_input,
             "observation": s.observation, "final_answer": s.final_answer}
            for s in steps
        ],
    }


@app.get("/agent/runs/{run_id}", dependencies=[Depends(auth)])
async def get_run(run_id: str):
    run = await db.fetchrow("SELECT * FROM agent_runs WHERE run_id=$1", run_id)
    if not run:
        raise HTTPException(404, "run not found")
    steps = await db.fetch(
        "SELECT * FROM agent_steps WHERE run_id=$1 ORDER BY step_index", run_id)
    return {"run": run, "steps": steps}


# =============================================================================
# RAG endpoint
# =============================================================================
@app.post("/rag/search", dependencies=[Depends(auth)])
async def rag_search(req: RagSearchRequest):
    chunks = await retrieve(req.query, top_k=req.top_k, device_id=req.device_id)
    return {"query": req.query, "results": chunks}


# =============================================================================
# Direct inference helpers
# =============================================================================
@app.post("/infer/vlm", dependencies=[Depends(auth)])
async def infer_vlm(
    device_id: str = Form(...),
    prompt: str = Form("Inspect this image for defects, leaks, smoke, fire or safety hazards."),
    image: UploadFile = File(...),
):
    data = await image.read()
    mime = image.content_type or "image/jpeg"
    start = time.time()
    result = await vlm.analyze(data, prompt, mime=mime)
    elapsed = int((time.time() - start) * 1000)
    flagged = any(k in result.lower() for k in
                  ("anomaly", "damage", "leak", "smoke", "fire", "hazard", "crack"))
    dev = await db.fetchrow("SELECT device_id FROM devices WHERE external_id=$1", device_id)
    if dev:
        await db.execute(
            """INSERT INTO ai_inferences
               (device_id, model_type, input_summary, result, anomaly_score, confidence, inference_time_ms)
               VALUES ($1,'vlm',$2,$3,$4,$5,$6)""",
            dev["device_id"], f"{image.filename}: {prompt[:120]}", result,
            0.9 if flagged else 0.1, 0.8, elapsed)
    return {"device_id": device_id, "result": result, "flagged": flagged,
            "inference_time_ms": elapsed}


@app.post("/infer/timeseries", dependencies=[Depends(auth)])
async def infer_timeseries(req: TimeseriesRequest):
    from .tools.registry import detect_anomaly
    import json as _json
    out = _json.loads(await detect_anomaly(req.values, req.threshold))
    return {"device_id": req.device_id, **out}


# =============================================================================
# SPC / Six Sigma endpoints (local MCP-powered control-chart analysis)
# =============================================================================
async def _fetch_values(device_id: str, metric: str, limit: int) -> list[float]:
    """Pull the most recent telemetry from IoTDB in chronological (ascending) order."""
    import json as _json
    raw = await query_telemetry(device_id, metric, limit)
    try:
        data = _json.loads(raw)
        pts = data.get("points", [])
    except (ValueError, AttributeError):
        return []
    # query_telemetry returns newest-first; reverse to time-ascending for charts.
    return [p["v"] for p in reversed(pts) if p.get("v") is not None]


async def _spc_payload(req: SpcAnalyzeRequest) -> dict:
    values = req.values
    if not values:
        if not (req.device_id and req.metric):
            raise HTTPException(400, "Provide either `values`, or both `device_id` and `metric`.")
        values = await _fetch_values(req.device_id, req.metric, req.limit)
    if len(values) < 2:
        raise HTTPException(400, "Not enough data points for an SPC chart (need >= 2).")

    import json as _json
    args = {"values": values, "subgroup_size": req.subgroup_size}
    for k in ("usl", "lsl", "target"):
        v = getattr(req, k)
        if v is not None:
            args[k] = v

    summary = _json.loads(await mcp_client.call_text("spc_control_chart", args))
    title = f"{req.metric or 'process'} — {req.device_id or 'data'}"
    _, chart_b64, mime = await mcp_client.call_image(
        "spc_render_chart",
        {"values": values, "subgroup_size": req.subgroup_size, "title": title})

    return {"values": values, "spc": summary,
            "chart_image_base64": chart_b64, "chart_mime": mime or "image/png"}


@app.post("/spc/analyze", dependencies=[Depends(auth)])
async def spc_analyze(req: SpcAnalyzeRequest):
    """Run a full SPC study (control chart + rules + capability) via the local
    SPC MCP, render the chart, and optionally have the SPC agent interpret it
    grounded in the SPC books."""
    payload = await _spc_payload(req)
    interpretation = None
    if req.interpret:
        import json as _json
        objective = (
            f"Interpret this SPC result for {req.metric or 'the process'} on "
            f"{req.device_id or 'the dataset'} and recommend corrective actions. "
            f"Decide if it is in statistical control and (if specs were given) capable. "
            f"Cite the SPC books with rag_search(domain='spc').\n\n"
            f"SPC_RESULT = {_json.dumps(payload['spc'])}"
        )
        interpretation, _ = await spc_agent.run(objective)
    payload["interpretation"] = interpretation
    return payload


@app.get("/spc/report", response_class=HTMLResponse, dependencies=[Depends(auth)])
async def spc_report(device_id: str, metric: str, limit: int = 100,
                     subgroup_size: int = 1, usl: float | None = None,
                     lsl: float | None = None, target: float | None = None):
    """Human-friendly HTML report with the control chart + agent narrative."""
    req = SpcAnalyzeRequest(device_id=device_id, metric=metric, limit=limit,
                            subgroup_size=subgroup_size, usl=usl, lsl=lsl,
                            target=target, interpret=True)
    payload = await spc_analyze(req)  # type: ignore[arg-type]
    spc = payload["spc"]
    img = (f'<img src="data:{payload["chart_mime"]};base64,{payload["chart_image_base64"]}" '
           f'style="max-width:100%;border:1px solid #ddd;border-radius:8px"/>'
           if payload.get("chart_image_base64") else "<p><em>chart unavailable</em></p>")
    viol_rows = "".join(
        f"<tr><td>{v['label']}</td><td>Rule {v['rule']}</td><td>{v['value']}</td>"
        f"<td>{v['description']}</td></tr>" for v in spc.get("violations", []))
    cap = spc.get("capability", {})
    cap_html = ("".join(f"<li><b>{k}</b>: {cap[k]}</li>" for k in
                ("Cp", "Cpk", "Pp", "Ppk", "sigma_level", "DPMO", "verdict") if k in cap)
                or "<li>No spec limits provided.</li>")
    status = "✅ IN CONTROL" if spc.get("in_control") else f"⛔ OUT OF CONTROL ({spc.get('n_violations')})"
    return f"""<!doctype html><html><head><meta charset="utf-8">
<title>SPC Report — {metric} / {device_id}</title>
<style>body{{font-family:system-ui,Arial;margin:2rem;max-width:920px;color:#222}}
h1{{font-size:1.4rem}} table{{border-collapse:collapse;width:100%;margin:1rem 0}}
td,th{{border:1px solid #ddd;padding:.4rem .6rem;text-align:left;font-size:.9rem}}
.box{{background:#f7f7f9;border-radius:8px;padding:1rem;margin:1rem 0}}</style></head>
<body>
<h1>SPC / Six Sigma Report — {metric} on {device_id}</h1>
<p><b>Chart:</b> {spc.get('chart_type')} &nbsp; | &nbsp; <b>Status:</b> {status}
&nbsp; | &nbsp; CL={spc.get('center')} UCL={spc.get('ucl')} LCL={spc.get('lcl')}</p>
{img}
<div class="box"><h3>Process capability</h3><ul>{cap_html}</ul></div>
<h3>Special-cause signals</h3>
<table><tr><th>Point</th><th>Rule</th><th>Value</th><th>Description</th></tr>
{viol_rows or '<tr><td colspan=4>None</td></tr>'}</table>
<div class="box"><h3>SPC analyst recommendation</h3>
<p style="white-space:pre-wrap">{payload.get('interpretation') or 'n/a'}</p></div>
</body></html>"""


@app.get("/spc/mcp/tools", dependencies=[Depends(auth)])
async def spc_mcp_tools():
    """List the tools exposed by the local SPC MCP server (proves connectivity)."""
    return {"spc_mcp_url": settings.spc_mcp_url, "tools": await mcp_client.list_tools()}


# =============================================================================
# Read-only data endpoints (for dashboards / API consumers)
# =============================================================================
@app.get("/devices", dependencies=[Depends(auth)])
async def list_devices():
    return await db.fetch("SELECT * FROM device_health_summary ORDER BY name")


@app.get("/alarms", dependencies=[Depends(auth)])
async def list_alarms(limit: int = 50):
    return await db.fetch(
        """SELECT a.*, d.external_id, d.name AS device_name
           FROM alarms a JOIN devices d ON d.device_id=a.device_id
           ORDER BY a.created_at DESC LIMIT $1""", min(limit, 200))
