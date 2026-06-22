"""
Training Monitor — MetricsCallback
===================================
HuggingFace Trainer callback that writes live training metrics to
/output/metrics.json every ~5 seconds.

The file is picked up by metrics_server.py (running on the Windows host)
and served to the browser dashboard at http://localhost:8765.

Metrics JSON schema:
{
  "status":          "idle" | "extracting" | "training" | "complete" | "error"
  "phase":           "extract" | "train"
  "epoch":           float   — current epoch (fractional during epoch)
  "total_epochs":    int
  "step":            int     — global step
  "total_steps":     int
  "progress_pct":    float   — 0-100
  "loss":            float | null
  "learning_rate":   float | null
  "grad_norm":       float | null
  "samples_per_sec": float | null
  "elapsed_seconds": int
  "eta_seconds":     int | null
  "gpu": {
    "vram_used_gb":  float
    "vram_total_gb": float
    "vram_pct":      float
    "temperature_c": float | null
    "utilization_pct": float | null
  }
  "history": [
    {"step": int, "loss": float, "lr": float, "ts": str}, ...
  ]
  "dataset_pairs":   int | null   — total Q&A pairs in dataset
  "updated_at":      str          — ISO timestamp
}
"""

import json
import os
import time
from datetime import datetime
from pathlib import Path
from typing import Optional

from transformers import TrainerCallback, TrainerState, TrainerControl, TrainingArguments

from pipeline_writer import write_step as _pipeline_step

METRICS_INTERVAL_SECONDS = 5
PIPELINE_FILE = Path("/output/pipeline.json")


class MetricsCallback(TrainerCallback):
    """
    Writes output/metrics.json every METRICS_INTERVAL_SECONDS during training.
    Atomic write (tmp → rename) so the reader never sees partial JSON.
    """

    def __init__(self, output_dir: str, dataset_pairs: int = 0):
        self._file = Path(output_dir) / "metrics.json"
        self._dataset_pairs = dataset_pairs
        self._start_time: float = 0.0
        self._last_write: float = 0.0
        self._history: list[dict] = []

        # Write initial idle state immediately so the dashboard shows something
        self._write({
            "status": "idle",
            "phase": "train",
            "epoch": 0,
            "total_epochs": 0,
            "step": 0,
            "total_steps": 0,
            "progress_pct": 0.0,
            "loss": None,
            "learning_rate": None,
            "grad_norm": None,
            "samples_per_sec": None,
            "elapsed_seconds": 0,
            "eta_seconds": None,
            "gpu": self._gpu_stats(),
            "history": [],
            "dataset_pairs": dataset_pairs,
            "updated_at": _now(),
        })

    # ── Lifecycle hooks ────────────────────────────────────────────────────────

    def on_train_begin(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ):
        self._start_time = time.time()
        _pipeline_step(PIPELINE_FILE, "training", "running",
                       f"Epoch 0/{int(args.num_train_epochs)} · Step 0/{state.max_steps}")
        self._write({
            "status": "training",
            "phase": "train",
            "epoch": 0,
            "total_epochs": args.num_train_epochs,
            "step": 0,
            "total_steps": state.max_steps,
            "progress_pct": 0.0,
            "loss": None,
            "learning_rate": args.learning_rate,
            "grad_norm": None,
            "samples_per_sec": None,
            "elapsed_seconds": 0,
            "eta_seconds": None,
            "gpu": self._gpu_stats(),
            "history": [],
            "dataset_pairs": self._dataset_pairs,
            "updated_at": _now(),
        })

    def on_log(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        logs: Optional[dict] = None,
        **kwargs,
    ):
        now = time.time()
        # Throttle to one write per interval
        if now - self._last_write < METRICS_INTERVAL_SECONDS:
            return
        self._last_write = now

        logs = logs or {}
        step = state.global_step
        total = state.max_steps or 1
        elapsed = now - self._start_time
        progress = (step / total) * 100 if total > 0 else 0
        eta = int((elapsed / step) * (total - step)) if step > 0 else None

        loss = logs.get("loss") or logs.get("train_loss")
        lr = logs.get("learning_rate")
        grad_norm = logs.get("grad_norm")
        sps = logs.get("train_samples_per_second")

        # Append to loss history (keep last 200 points for the chart)
        if loss is not None:
            self._history.append({
                "step": step,
                "epoch": round(float(state.epoch or 0), 3),
                "loss": round(float(loss), 4),
                "lr": round(float(lr), 8) if lr else None,
                "ts": _now(),
            })
            if len(self._history) > 200:
                self._history = self._history[-200:]

        self._write({
            "status": "training",
            "phase": "train",
            "epoch": round(float(state.epoch or 0), 2),
            "total_epochs": int(args.num_train_epochs),
            "step": step,
            "total_steps": total,
            "progress_pct": round(progress, 1),
            "loss": round(float(loss), 4) if loss is not None else None,
            "learning_rate": round(float(lr), 8) if lr is not None else None,
            "grad_norm": round(float(grad_norm), 4) if grad_norm is not None else None,
            "samples_per_sec": round(float(sps), 2) if sps is not None else None,
            "elapsed_seconds": int(elapsed),
            "eta_seconds": eta,
            "gpu": self._gpu_stats(),
            "history": self._history[-100:],
            "dataset_pairs": self._dataset_pairs,
            "updated_at": _now(),
        })

    def on_train_end(
        self,
        args: TrainingArguments,
        state: TrainerState,
        control: TrainerControl,
        **kwargs,
    ):
        elapsed = time.time() - self._start_time
        _pipeline_step(PIPELINE_FILE, "export_gguf", "running", "Exporting LoRA adapter to GGUF...")
        self._write({
            "status": "complete",
            "phase": "train",
            "epoch": int(args.num_train_epochs),
            "total_epochs": int(args.num_train_epochs),
            "step": state.global_step,
            "total_steps": state.max_steps,
            "progress_pct": 100.0,
            "loss": self._history[-1]["loss"] if self._history else None,
            "learning_rate": None,
            "grad_norm": None,
            "samples_per_sec": None,
            "elapsed_seconds": int(elapsed),
            "eta_seconds": 0,
            "gpu": self._gpu_stats(),
            "history": self._history,
            "dataset_pairs": self._dataset_pairs,
            "updated_at": _now(),
        })

    # ── Helpers ────────────────────────────────────────────────────────────────

    def _write(self, data: dict) -> None:
        """Atomic write: write to .tmp then rename so readers never see partial JSON."""
        self._file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._file.with_suffix(".tmp")
        try:
            with open(tmp, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2, default=str)
            tmp.replace(self._file)
        except Exception as e:
            print(f"[MetricsCallback] Write failed: {e}")

    @staticmethod
    def _gpu_stats() -> dict:
        try:
            import torch
            if not torch.cuda.is_available():
                return {}
            props = torch.cuda.get_device_properties(0)
            vram_used = torch.cuda.memory_allocated(0) / 1024 ** 3
            vram_total = props.total_memory / 1024 ** 3
            stats: dict = {
                "vram_used_gb": round(vram_used, 2),
                "vram_total_gb": round(vram_total, 2),
                "vram_pct": round(vram_used / vram_total * 100, 1) if vram_total else 0,
                "temperature_c": None,
                "utilization_pct": None,
            }
            # Try pynvml for temperature + utilization
            try:
                import pynvml
                pynvml.nvmlInit()
                handle = pynvml.nvmlDeviceGetHandleByIndex(0)
                stats["temperature_c"] = pynvml.nvmlDeviceGetTemperature(
                    handle, pynvml.NVML_TEMPERATURE_GPU
                )
                util = pynvml.nvmlDeviceGetUtilizationRates(handle)
                stats["utilization_pct"] = util.gpu
            except Exception:
                pass
            return stats
        except Exception:
            return {}


# ── Standalone writer for the extraction phase ────────────────────────────────

class ExtractionProgressWriter:
    """
    Used by 1_extract_dataset.py to emit progress during PDF extraction.
    Not a Trainer callback — called manually by the extraction script.
    """

    def __init__(self, output_dir: str, total_pdfs: int = 0):
        self._file = Path(output_dir) / "metrics.json"
        self._start = time.time()
        self._total = total_pdfs
        _pipeline_step(PIPELINE_FILE, "extract", "running", f"Parsing {total_pdfs} PDF(s)...")
        self.write(0, 0, "Starting PDF extraction...")

    def write(self, pdfs_done: int, pairs_so_far: int, message: str = "") -> None:
        progress = (pdfs_done / self._total * 100) if self._total > 0 else 0
        self._atomic_write({
            "status": "extracting",
            "phase": "extract",
            "epoch": 0,
            "total_epochs": 0,
            "step": pdfs_done,
            "total_steps": self._total,
            "progress_pct": round(progress, 1),
            "loss": None,
            "learning_rate": None,
            "grad_norm": None,
            "samples_per_sec": None,
            "elapsed_seconds": int(time.time() - self._start),
            "eta_seconds": None,
            "gpu": {},
            "history": [],
            "dataset_pairs": pairs_so_far,
            "message": message,
            "updated_at": _now(),
        })

    def _atomic_write(self, data: dict) -> None:
        self._file.parent.mkdir(parents=True, exist_ok=True)
        tmp = self._file.with_suffix(".tmp")
        with open(tmp, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, default=str)
        tmp.replace(self._file)


def _now() -> str:
    return datetime.now().isoformat()
