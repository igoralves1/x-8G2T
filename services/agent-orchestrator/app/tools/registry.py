"""Tool registry shared by all agents.

A Tool wraps an async python function with a name, a natural-language
description and a JSON-schema for its arguments. The agent loop renders these
specs into the system prompt and dispatches the model's chosen tool call.
"""
from __future__ import annotations

import json
from dataclasses import dataclass
from typing import Any, Awaitable, Callable

import httpx
import numpy as np
from loguru import logger
from scipy import stats

from ..core import db
from ..core.config import settings
from ..core.llm_clients import embedder
from ..rag.retriever import retrieve_and_format

ToolFn = Callable[..., Awaitable[Any]]


@dataclass
class Tool:
    name: str
    description: str
    parameters: dict[str, Any]      # JSON-schema "properties"
    required: list[str]
    func: ToolFn

    def spec(self) -> dict[str, Any]:
        return {
            "name": self.name,
            "description": self.description,
            "parameters": {"type": "object", "properties": self.parameters,
                           "required": self.required},
        }


_REGISTRY: dict[str, Tool] = {}


def tool(name: str, description: str, parameters: dict, required: list[str]):
    def deco(fn: ToolFn) -> ToolFn:
        _REGISTRY[name] = Tool(name, description, parameters, required, fn)
        return fn
    return deco


def get(name: str) -> Tool | None:
    return _REGISTRY.get(name)


def specs(names: list[str] | None = None) -> list[dict]:
    items = _REGISTRY.values() if names is None else [_REGISTRY[n] for n in names if n in _REGISTRY]
    return [t.spec() for t in items]


async def dispatch(name: str, args: dict[str, Any]) -> str:
    t = _REGISTRY.get(name)
    if not t:
        return f"ERROR: unknown tool '{name}'"
    try:
        result = await t.func(**args)
        return result if isinstance(result, str) else json.dumps(result, default=str)
    except TypeError as exc:
        return f"ERROR: bad arguments for {name}: {exc}"
    except Exception as exc:  # noqa: BLE001
        logger.exception(f"tool {name} failed")
        return f"ERROR: tool {name} raised {type(exc).__name__}: {exc}"


# =============================================================================
# Tool implementations
# =============================================================================

@tool(
    "rag_search",
    "Search the engineering knowledge base (device manuals, runbooks, past "
    "incident reports, maintenance SOPs, and the SPC/Six-Sigma reference books) "
    "for information relevant to a question. Set domain='spc' to restrict the "
    "search to the Statistical Process Control literature.",
    {"query": {"type": "string", "description": "what to look up"},
     "device_id": {"type": "string", "description": "optional device external id to scope results"},
     "domain": {"type": "string", "description": "optional domain filter, e.g. 'spc' or 'ops'"}},
    ["query"],
)
async def rag_search(query: str, device_id: str | None = None,
                     domain: str | None = None) -> str:
    context, chunks = await retrieve_and_format(query, device_id=device_id, domain=domain)
    return context if chunks else "No relevant documents found in the knowledge base."


@tool(
    "get_device",
    "Look up metadata for a device by its external id (e.g. 'sensor_001').",
    {"external_id": {"type": "string"}},
    ["external_id"],
)
async def get_device(external_id: str) -> str:
    row = await db.fetchrow(
        "SELECT external_id, name, device_type, location, status, last_seen, metadata "
        "FROM devices WHERE external_id = $1", external_id)
    return json.dumps(row, default=str) if row else f"No device '{external_id}'."


@tool(
    "get_recent_alarms",
    "Get the most recent alarms for a device (newest first).",
    {"external_id": {"type": "string"}, "limit": {"type": "integer", "description": "default 5"}},
    ["external_id"],
)
async def get_recent_alarms(external_id: str, limit: int = 5) -> str:
    rows = await db.fetch(
        """SELECT a.severity, a.message, a.metric_name, a.metric_value, a.source,
                  a.resolved, a.created_at
           FROM alarms a JOIN devices d ON d.device_id = a.device_id
           WHERE d.external_id = $1 ORDER BY a.created_at DESC LIMIT $2""",
        external_id, min(limit, 50))
    return json.dumps(rows, default=str) if rows else "No alarms recorded."


@tool(
    "query_telemetry",
    "Query recent time-series telemetry for a device/metric from IoTDB. "
    "Returns up to `limit` most recent (timestamp, value) points.",
    {"external_id": {"type": "string"},
     "metric": {"type": "string", "description": "e.g. temperature, humidity, vibration"},
     "limit": {"type": "integer", "description": "default 50"}},
    ["external_id", "metric"],
)
async def query_telemetry(external_id: str, metric: str, limit: int = 50) -> str:
    path = f"root.iot.telemetry.{external_id}.{metric}"
    sql = f"SELECT {metric} FROM root.iot.telemetry.{external_id} ORDER BY time DESC LIMIT {min(limit, 500)}"
    url = f"http://{settings.iotdb_host}:{settings.iotdb_rest_port}/rest/v2/query"
    try:
        async with httpx.AsyncClient(timeout=15.0) as client:
            r = await client.post(url, json={"sql": sql},
                                  auth=(settings.iotdb_user, settings.iotdb_password))
            r.raise_for_status()
            data = r.json()
    except Exception as exc:  # noqa: BLE001
        return f"ERROR querying IoTDB ({path}): {exc}"
    ts = data.get("timestamps", [])
    cols = data.get("values", [[]])
    vals = cols[0] if cols else []
    points = [{"t": t, "v": v} for t, v in zip(ts, vals)]
    return json.dumps({"metric": metric, "count": len(points), "points": points}, default=str)


@tool(
    "detect_anomaly",
    "Run statistical anomaly detection (modified Z-score) over a list of numeric "
    "values. Returns anomaly indices, the max score and basic stats.",
    {"values": {"type": "array", "items": {"type": "number"},
                "description": "at least 8 numeric samples"},
     "threshold": {"type": "number", "description": "z-score threshold, default 3.0"}},
    ["values"],
)
async def detect_anomaly(values: list[float], threshold: float = 3.0) -> str:
    arr = np.asarray(values, dtype=float)
    if arr.size < 8:
        return "ERROR: need at least 8 values."
    z = np.abs(stats.zscore(arr, nan_policy="omit"))
    idx = np.where(z > threshold)[0].tolist()
    return json.dumps({
        "anomaly_count": len(idx),
        "anomaly_indices": idx,
        "max_score": float(np.nanmax(z)) if z.size else 0.0,
        "mean": float(np.nanmean(arr)),
        "std": float(np.nanstd(arr)),
        "min": float(np.nanmin(arr)),
        "max": float(np.nanmax(arr)),
    })


@tool(
    "create_alarm",
    "Raise an alarm for a device. Use ONLY after you have evidence of a real "
    "issue. Severity must be info, warning or critical.",
    {"external_id": {"type": "string"},
     "severity": {"type": "string", "enum": ["info", "warning", "critical"]},
     "message": {"type": "string"},
     "metric_name": {"type": "string"},
     "metric_value": {"type": "number"}},
    ["external_id", "severity", "message"],
)
async def create_alarm(external_id: str, severity: str, message: str,
                       metric_name: str | None = None, metric_value: float | None = None) -> str:
    dev = await db.fetchrow("SELECT device_id FROM devices WHERE external_id=$1", external_id)
    if not dev:
        return f"ERROR: no device '{external_id}'."
    await db.execute(
        """INSERT INTO alarms (device_id, severity, message, metric_name, metric_value, source)
           VALUES ($1,$2,$3,$4,$5,'agent')""",
        dev["device_id"], severity, message, metric_name, metric_value)
    return f"Alarm created ({severity}) for {external_id}: {message}"


@tool(
    "recall_memory",
    "Semantic search over the agent's long-term memory of past insights and "
    "incident resolutions for similar situations.",
    {"query": {"type": "string"},
     "external_id": {"type": "string", "description": "optional device scope"},
     "limit": {"type": "integer", "description": "default 3"}},
    ["query"],
)
async def recall_memory(query: str, external_id: str | None = None, limit: int = 3) -> str:
    vec = await embedder.embed_one(query)
    vec_literal = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
    if external_id:
        rows = await db.fetch(
            """SELECT m.kind, m.content, m.created_at,
                      1 - (m.embedding <=> $1::vector) AS similarity
               FROM agent_memory m JOIN devices d ON d.device_id = m.device_id
               WHERE d.external_id = $2 AND m.embedding IS NOT NULL
               ORDER BY m.embedding <=> $1::vector LIMIT $3""",
            vec_literal, external_id, min(limit, 10))
    else:
        rows = await db.fetch(
            """SELECT kind, content, created_at,
                      1 - (embedding <=> $1::vector) AS similarity
               FROM agent_memory WHERE embedding IS NOT NULL
               ORDER BY embedding <=> $1::vector LIMIT $2""",
            vec_literal, min(limit, 10))
    return json.dumps(rows, default=str) if rows else "No relevant memories."


@tool(
    "save_memory",
    "Persist a concise, reusable insight or incident resolution to long-term "
    "memory so future investigations can recall it.",
    {"external_id": {"type": "string"},
     "content": {"type": "string", "description": "one or two sentences, self-contained"},
     "kind": {"type": "string", "enum": ["insight", "incident", "resolution"]}},
    ["content"],
)
async def save_memory(content: str, external_id: str | None = None, kind: str = "insight") -> str:
    vec = await embedder.embed_one(content)
    vec_literal = "[" + ",".join(f"{x:.6f}" for x in vec) + "]"
    device_id = None
    if external_id:
        dev = await db.fetchrow("SELECT device_id FROM devices WHERE external_id=$1", external_id)
        device_id = dev["device_id"] if dev else None
    await db.execute(
        """INSERT INTO agent_memory (device_id, kind, content, embedding)
           VALUES ($1, $2, $3, $4::vector)""",
        device_id, kind, content, vec_literal)
    return "Memory saved."
