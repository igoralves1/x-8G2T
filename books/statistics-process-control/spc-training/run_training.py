#!/usr/bin/env python3
"""
SPC Fine-Tuning Pipeline — Single Entry Point
==============================================

HOW TO USE
----------
From Windows (outside Docker) — run once:
    python run_training.py

    The script will:
      1. Verify Docker Desktop is running
      2. Build the Docker image (conda + CUDA 12.8 + Unsloth + all libs)
      3. Run the extract step (reads PDFs → generates JSONL dataset)
      4. Run the train step  (LoRA fine-tune Llama-3.2-3B on RTX 5080)
      5. Print the location of the output file

From inside the container (auto-detected via IN_DOCKER env var):
    python run_training.py

    No environment setup needed — conda env "spc-train" is already active.
    Runs both pipeline scripts directly.

OUTPUT
------
The fine-tuned LoRA adapter is saved here (on the Windows filesystem):
    books/statistics-process-control/spc-training/output/adapter/spc-model-q4km.gguf

This file IS committed to git (see output/.gitignore — the *.gguf exception).
Pull it on the Jetson and load it alongside the base Llama model.

HARDWARE
--------
  Windows PC  : AMD Ryzen 9 9900X | RTX 5080 (17 GB VRAM) | 32 GB RAM
  GPU CUDA    : 12.8 — Blackwell sm_120 — sufficient for 3B LoRA training
  Docker image: nvidia/cuda:12.8.1-devel-ubuntu22.04 + Miniconda spc-train env
"""

import os
import sys
import subprocess
import socket
import time
from pathlib import Path

# Pipeline writer (host-side path)
sys.path.insert(0, str(Path(__file__).parent / "scripts"))
from pipeline_writer import write_step as _write_step


# ── Context detection ──────────────────────────────────────────────────────────

def is_inside_docker() -> bool:
    """True when this script is running inside the Docker container."""
    return (
        Path("/.dockerenv").exists()
        or os.environ.get("IN_DOCKER") == "1"
        or os.environ.get("CONDA_DEFAULT_ENV") == "spc-train"
    )


# ── Helpers ────────────────────────────────────────────────────────────────────

def header(title: str) -> None:
    width = 62
    print("\n" + "=" * width)
    print(f"  {title}")
    print("=" * width)


_LOG_FILE: Path | None = None


def _set_log(path: Path) -> None:
    global _LOG_FILE
    _LOG_FILE = path
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("", encoding="utf-8")  # reset on each run


def _log_line(line: str) -> None:
    print(line, end="", flush=True)
    if _LOG_FILE:
        with open(_LOG_FILE, "a", encoding="utf-8") as f:
            f.write(line)


def run(label: str, cmd: list, **kwargs) -> None:
    """Run a subprocess step, streaming every output line to stdout + log file."""
    header(label)
    print(f"  cmd: {' '.join(str(c) for c in cmd)}\n")
    kwargs.pop("capture_output", None)
    proc = subprocess.Popen(
        cmd,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        encoding="utf-8",
        errors="replace",
        **kwargs,
    )
    for line in proc.stdout:
        _log_line(line)
    proc.wait()
    if proc.returncode != 0:
        print(f"\n[ERROR] Step failed (exit {proc.returncode})")
        sys.exit(proc.returncode)


# ── Path inside the container ──────────────────────────────────────────────────

CONTAINER_SCRIPTS = Path("/workspace/scripts")
CONTAINER_OUTPUT  = Path("/output")
CONTAINER_CONFIG  = Path("/workspace/config")


# ── Inside-container pipeline ──────────────────────────────────────────────────

def run_inside_container() -> None:
    """
    Called when already inside the Docker container.
    No conda env creation needed — spc-train env is pre-activated by the image.
    """
    header("SPC Training Pipeline — Running INSIDE Container")
    print(f"  Python  : {sys.executable}")
    print(f"  Conda   : {os.environ.get('CONDA_DEFAULT_ENV', 'n/a')}")

    import torch  # noqa: F401 — validate CUDA available
    print(f"  PyTorch : {torch.__version__}")
    if not torch.cuda.is_available():
        print("\n[ERROR] No CUDA GPU detected inside the container.")
        print("  Check that the container was started with --gpus all (or the")
        print("  deploy.resources GPU reservation in docker-compose.train.yml).")
        sys.exit(1)

    gpu = torch.cuda.get_device_name(0)
    vram = torch.cuda.get_device_properties(0).total_memory / 1024**3
    print(f"  GPU     : {gpu}  ({vram:.1f} GB VRAM)")

    CONTAINER_OUTPUT.mkdir(parents=True, exist_ok=True)

    # Step 1 — extract dataset from PDFs
    run(
        "STEP 1 / 2 — Extracting training dataset from PDF books",
        [sys.executable, str(CONTAINER_SCRIPTS / "1_extract_dataset.py")],
    )

    # Step 2 — fine-tune
    run(
        "STEP 2 / 2 — Fine-tuning Llama-3.2-3B with LoRA on RTX 5080",
        [sys.executable, str(CONTAINER_SCRIPTS / "2_train.py")],
    )

    _report_container_output()


def _report_container_output() -> None:
    adapter = CONTAINER_OUTPUT / "adapter_gguf" / "spc-model-q4km.gguf"
    header("PIPELINE COMPLETE")
    if adapter.exists():
        size_mb = adapter.stat().st_size / 1024 ** 2
        print(f"  Adapter  : {adapter}")
        print(f"  Size     : {size_mb:.1f} MB")
        print(f"  Status   : ready to commit and deploy to Jetson")
        print()
        print("  Next — on the Windows host (outside this container):")
        print("    cd C:\\Users\\alexa\\Documents\\vhost\\x-8G2T")
        print("    git add books/statistics-process-control/spc-training/output/adapter/")
        print("    git commit -m \"feat(spc): SPC LoRA adapter — Llama-3.2-3B v1\"")
        print("    git push origin main")
        print()
        print("  Then on the Jetson:")
        print("    git pull")
        print("    bash books/statistics-process-control/spc-training/scripts/3_deploy_jetson.sh")
    else:
        print(f"  [WARNING] Expected file not found: {adapter}")
        print(f"  Check the training logs above for errors.")
        print(f"  Output directory contents:")
        for p in sorted(CONTAINER_OUTPUT.rglob("*")):
            if p.is_file():
                print(f"    {p}  ({p.stat().st_size / 1024:.0f} KB)")


# ── Windows-host orchestration ─────────────────────────────────────────────────

def _pipeline(script_dir: Path, step_id: str, status: str, detail: str = "") -> None:
    pipeline_file = script_dir / "output" / "pipeline.json"
    try:
        _write_step(pipeline_file, step_id, status, detail)
    except Exception as e:
        print(f"  [pipeline] write failed: {e}")


def run_from_windows_host() -> None:
    """
    Called when running on the Windows PC.
    Orchestrates Docker: build image → run container → report output path.
    """
    script_dir   = Path(__file__).parent.resolve()
    compose_file = script_dir / "docker-compose.train.yml"
    output_dir   = script_dir / "output"

    _set_log(script_dir / "output" / "build_log.txt")

    header("SPC Fine-Tuning — Windows Host Orchestrator")
    print(f"  Script dir   : {script_dir}")
    print(f"  Compose file : {compose_file}")
    print(f"  Output dir   : {output_dir}")
    print(f"  Target GPU   : RTX 5080  (17 GB VRAM, CUDA 12.8)")

    # ── Pre-flight: Docker running? ────────────────────────────────────────────
    header("PRE-FLIGHT — Checking Docker")
    _pipeline(script_dir, "preflight", "running", "Checking Docker + GPU...")
    try:
        result = subprocess.run(
            ["docker", "info"],
            capture_output=True, text=True
        )
        if result.returncode != 0:
            raise RuntimeError("docker info failed")
        print("  Docker Desktop: running")
    except (FileNotFoundError, RuntimeError):
        _pipeline(script_dir, "preflight", "error", "Docker not running")
        print("\n[ERROR] Docker is not running or not in PATH.")
        print("  Start Docker Desktop, then re-run this script.")
        sys.exit(1)

    # Check NVIDIA Docker runtime
    gpu_detail = "GPU passthrough: unknown"
    try:
        r = subprocess.run(
            ["docker", "run", "--rm", "--gpus", "all",
             "nvidia/cuda:12.8.1-base-ubuntu22.04",
             "nvidia-smi", "--query-gpu=name,memory.total", "--format=csv,noheader"],
            capture_output=True, text=True, check=True
        )
        gpu_detail = r.stdout.strip() or "GPU passthrough works"
        print(f"  NVIDIA runtime: available ({gpu_detail})")
    except subprocess.CalledProcessError:
        gpu_detail = "GPU passthrough check failed — continuing"
        print("  [WARNING] NVIDIA Docker runtime check failed.")
        print("  Make sure 'NVIDIA Container Toolkit' is installed in Docker Desktop.")
        print("  Training will still attempt to proceed.")
    _pipeline(script_dir, "preflight", "done", gpu_detail)

    if not compose_file.exists():
        print(f"\n[ERROR] Not found: {compose_file}")
        sys.exit(1)

    compose = ["docker", "compose", "-f", str(compose_file)]
    cwd = str(script_dir)

    # ── Step 1: Start metrics server on host ───────────────────────────────────
    _pipeline(script_dir, "metrics_server", "running", "Starting on port 8765...")
    metrics_proc = _start_metrics_server(script_dir)
    _pipeline(script_dir, "metrics_server", "done", "http://localhost:8765")

    # ── Step 2: Build image ────────────────────────────────────────────────────
    # Uses layer cache on re-runs — only rebuilds changed layers
    _pipeline(script_dir, "docker_build", "running", "Building image (first run: 10-20 min)...")
    run(
        "STEP 1 / 3 — Building Docker image  (first run: ~10-20 min)",
        compose + ["build"],
        cwd=cwd
    )
    _pipeline(script_dir, "docker_build", "done", "Image ready — starting container")

    # ── Step 3: Extract + Train (single container run) ─────────────────────────
    _pipeline(script_dir, "extract", "running", "Starting container...")
    try:
        run(
            "STEP 3 / 3 — Extract dataset + Fine-tune model inside container",
            compose + ["run", "--rm", "all"],
            cwd=cwd,
        )
        _pipeline(script_dir, "complete", "done", "spc-model-q4km.gguf ready")
    finally:
        if metrics_proc and metrics_proc.poll() is None:
            metrics_proc.terminate()
            print("\n  Metrics server stopped.")

    # ── Report Windows-side output path ───────────────────────────────────────
    _report_host_output(output_dir, script_dir)


def _report_host_output(output_dir: Path, script_dir: Path) -> None:
    adapter = output_dir / "adapter_gguf" / "spc-model-q4km.gguf"
    repo_root = script_dir.parent.parent.parent  # x-8G2T/

    header("DONE — Fine-tuned SPC adapter ready")
    if adapter.exists():
        size_mb = adapter.stat().st_size / 1024 ** 2
        print(f"  Windows path : {adapter}")
        print(f"  File size    : {size_mb:.1f} MB")
        print(f"  Git-tracked  : YES (see output/.gitignore)")
        print()
        print("  Commit and push:")
        print(f"    cd \"{repo_root}\"")
        print(f"    git add books/statistics-process-control/spc-training/output/adapter/")
        print(f"    git commit -m \"feat(spc): SPC LoRA adapter — Llama-3.2-3B v1\"")
        print(f"    git push origin main")
        print()
        print("  On the Jetson:")
        print(f"    git pull")
        print(f"    bash books/statistics-process-control/spc-training/scripts/3_deploy_jetson.sh")
    else:
        print(f"  [WARNING] Output file not found: {adapter}")
        print(f"  Contents of output dir:")
        if output_dir.exists():
            for p in sorted(output_dir.rglob("*")):
                if p.is_file():
                    rel = p.relative_to(output_dir)
                    print(f"    output/{rel}  ({p.stat().st_size / 1024:.0f} KB)")
        else:
            print(f"    (directory does not exist)")


# ── Metrics server helper ──────────────────────────────────────────────────────

def _start_metrics_server(script_dir: Path):
    """
    Start metrics_server.py as a background process on the Windows host.
    Returns the Popen handle (so the caller can terminate it later).
    Skips gracefully if fastapi/uvicorn are not installed.
    """
    server_script = script_dir / "metrics_server.py"
    if not server_script.exists():
        print("  [metrics] metrics_server.py not found — skipping dashboard server.")
        return None

    # Check if port 8765 is already in use
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        in_use = s.connect_ex(("localhost", 8765)) == 0

    if in_use:
        print("  [metrics] Port 8765 already in use — metrics server already running.")
        print("  [metrics] Dashboard: http://localhost:8765")
        return None

    # Check fastapi is available on the host
    try:
        import importlib
        importlib.import_module("fastapi")
        importlib.import_module("uvicorn")
    except ImportError:
        print("  [metrics] fastapi/uvicorn not installed on host.")
        print("  [metrics] Install with: pip install -r requirements-host.txt")
        print("  [metrics] Then re-run — or start manually: python metrics_server.py")
        return None

    proc = subprocess.Popen(
        [sys.executable, str(server_script)],
        cwd=str(script_dir),
    )

    # Give it a moment to bind the port
    for _ in range(10):
        time.sleep(0.5)
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            if s.connect_ex(("localhost", 8765)) == 0:
                break

    print(f"\n  Metrics dashboard: http://localhost:8765")
    print(f"  API endpoint     : http://localhost:8765/api/metrics")
    print(f"  SSE stream       : http://localhost:8765/api/stream\n")
    return proc


# ── Entry point ────────────────────────────────────────────────────────────────

if __name__ == "__main__":
    if is_inside_docker():
        run_inside_container()
    else:
        run_from_windows_host()
