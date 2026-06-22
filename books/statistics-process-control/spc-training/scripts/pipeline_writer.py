"""
Pipeline status writer — shared by host (run_training.py) and container scripts.
Writes /output/pipeline.json atomically so the metrics server can serve it.
"""

import json
from datetime import datetime
from pathlib import Path

# ── Step definitions (single source of truth) ──────────────────────────────────
PIPELINE_STEPS = [
    {
        "id": "preflight",
        "label": "Pre-flight",
        "icon": "shield-check",
        "description": "Docker + GPU verified",
        "explanation": (
            "Checks that Docker Desktop is running, the NVIDIA Container Toolkit is "
            "installed, and your RTX 5080 is accessible inside containers via GPU "
            "passthrough. Without this, no training can begin."
        ),
    },
    {
        "id": "metrics_server",
        "label": "Metrics Server",
        "icon": "activity",
        "description": "Live monitoring on port 8765",
        "explanation": (
            "Starts a FastAPI server on your Windows machine that reads metrics.json "
            "written by the training container and serves them to this dashboard in "
            "real time via REST polling and Server-Sent Events (SSE)."
        ),
    },
    {
        "id": "docker_build",
        "label": "Docker Build",
        "icon": "box",
        "description": "Build CUDA 12.8 + Miniforge + PyTorch 2.7 image",
        "explanation": (
            "Builds the training Docker image: Ubuntu 22.04, CUDA 12.8 toolkit, "
            "Miniforge (conda), Python 3.11, PyTorch 2.7+cu128, Unsloth (fast LoRA), "
            "and the full HuggingFace training stack. "
            "First run: 10–20 min. Subsequent runs use Docker layer cache (~30s)."
        ),
    },
    {
        "id": "extract",
        "label": "PDF Extraction",
        "icon": "file-text",
        "description": "Parse SPC textbooks → JSONL dataset",
        "explanation": (
            "Parses 2 SPC textbooks (Statistical Process Control + The Book of SPC) "
            "using PyMuPDF and pdfminer, then generates question-answer pairs formatted "
            "for instruction fine-tuning. Output: /output/spc-qa-pairs.jsonl."
        ),
    },
    {
        "id": "llm_download",
        "label": "LLM Download",
        "icon": "download",
        "description": "Download Llama-3.2-3B from HuggingFace (~6 GB)",
        "explanation": (
            "Downloads the Llama-3.2-3B base model from HuggingFace Hub (~6 GB). "
            "This only happens on the first run — subsequent runs load from the "
            "spc_training_hf_cache Docker volume. Unsloth loads it in 4-bit "
            "quantization to fit in 17 GB VRAM."
        ),
    },
    {
        "id": "lora_apply",
        "label": "Apply LoRA",
        "icon": "layers",
        "description": "Inject LoRA adapter layers into the model",
        "explanation": (
            "Applies LoRA (Low-Rank Adaptation) to the attention layers of Llama-3.2-3B. "
            "This adds ~4M trainable parameters on top of the frozen 3B base — only "
            "these adapter weights will be updated during training, keeping memory "
            "usage low and training fast."
        ),
    },
    {
        "id": "training",
        "label": "LoRA Training",
        "icon": "cpu",
        "description": "Fine-tune on RTX 5080 (17 GB VRAM)",
        "explanation": (
            "Fine-tunes the model using SFTTrainer (Supervised Fine-Tuning). "
            "The RTX 5080's 17 GB VRAM handles the 4-bit base model + LoRA adapters "
            "with gradient checkpointing. Watch the Loss curve drop — lower is better. "
            "Training completes in ~20–60 minutes depending on dataset size."
        ),
    },
    {
        "id": "export_gguf",
        "label": "GGUF Export",
        "icon": "package",
        "description": "Export adapter → spc-adapter-lora.gguf",
        "explanation": (
            "Exports the LoRA adapter (not the full model) to GGUF format. "
            "The resulting spc-adapter-lora.gguf file (~50–80 MB) is committable "
            "to git and loadable on the Jetson Orin Nano alongside the base model "
            "using llama-server."
        ),
    },
    {
        "id": "complete",
        "label": "Ready for Jetson",
        "icon": "check-circle",
        "description": "Adapter ready — commit and deploy",
        "explanation": (
            "The SPC specialist adapter is ready. Commit it to git and pull on "
            "the Jetson Orin Nano 8GB. The spc_agent will load it via llama-server "
            "as a LoRA adapter on top of the base Llama-3.2-3B model."
        ),
    },
]

STEP_IDS = [s["id"] for s in PIPELINE_STEPS]


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


def _atomic_write(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    tmp.write_text(json.dumps(data, indent=2, default=str), encoding="utf-8")
    tmp.replace(path)


def write_step(
    pipeline_file: Path,
    current_id: str,
    status: str,           # "running" | "done" | "error"
    detail: str = "",
    error: str = "",
) -> None:
    """
    Update pipeline.json marking `current_id` with `status`.
    Steps before it → done. Steps after it → pending.
    """
    # Load existing to preserve started_at timestamps
    existing: dict = {}
    if pipeline_file.exists():
        try:
            existing = json.loads(pipeline_file.read_text(encoding="utf-8"))
        except Exception:
            pass

    existing_steps: dict[str, dict] = {
        s["id"]: s for s in existing.get("steps", [])
    }

    steps = []
    found = False
    for defn in PIPELINE_STEPS:
        sid = defn["id"]
        prev = existing_steps.get(sid, {})

        if sid == current_id:
            found = True
            s = {
                **defn,
                "status": status,
                "detail": detail,
                "error": error,
                "started_at": prev.get("started_at") or _now(),
                "completed_at": _now() if status in ("done", "error") else None,
            }
        elif not found:
            # Steps before current → done
            s = {
                **defn,
                "status": "done",
                "detail": prev.get("detail", ""),
                "error": "",
                "started_at": prev.get("started_at", ""),
                "completed_at": prev.get("completed_at", ""),
            }
        else:
            # Steps after current → pending
            s = {
                **defn,
                "status": "pending",
                "detail": "",
                "error": "",
                "started_at": None,
                "completed_at": None,
            }
        steps.append(s)

    data = {
        "started_at": existing.get("started_at") or _now(),
        "updated_at": _now(),
        "current_step": current_id,
        "current_status": status,
        "steps": steps,
    }
    _atomic_write(pipeline_file, data)
