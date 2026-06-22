# ── SPC Training Container ────────────────────────────────────────────────────
# NVIDIA RTX 5080 — Blackwell sm_120 — CUDA 12.8
# Uses Miniconda for environment management (best for GPU/CUDA workloads)
# Python 3.11 in isolated conda env "spc-train"

FROM nvidia/cuda:12.8.1-devel-ubuntu22.04

LABEL description="SPC LLM Fine-Tuning — Conda + Unsloth + Llama-3.2-3B — RTX 5080"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1
# Tells run_training.py it is inside the container (skip Docker orchestration)
ENV IN_DOCKER=1

# ── System dependencies ────────────────────────────────────────────────────────
RUN apt-get update && apt-get install -y \
    wget \
    curl \
    git \
    git-lfs \
    build-essential \
    ca-certificates \
    libglib2.0-0 \
    libsm6 \
    libxrender1 \
    libxext6 \
    && rm -rf /var/lib/apt/lists/*

# ── Install Miniforge (conda-forge default — no Anaconda TOS required) ────────
ENV CONDA_DIR=/opt/conda
RUN wget -q https://github.com/conda-forge/miniforge/releases/latest/download/Miniforge3-Linux-x86_64.sh \
        -O /tmp/miniforge.sh && \
    bash /tmp/miniforge.sh -b -p $CONDA_DIR && \
    rm /tmp/miniforge.sh && \
    $CONDA_DIR/bin/conda init bash && \
    $CONDA_DIR/bin/conda clean -afy

ENV PATH="$CONDA_DIR/bin:$PATH"

# ── Create conda environment: spc-train / Python 3.11 ────────────────────────
RUN conda create -n spc-train python=3.11 -y && \
    conda clean -afy

# Activate env for all subsequent RUN/CMD layers by prepending its bin to PATH
ENV CONDA_DEFAULT_ENV=spc-train
ENV PATH="$CONDA_DIR/envs/spc-train/bin:$CONDA_DIR/bin:$PATH"

# ── PyTorch with CUDA 12.8 (Blackwell RTX 5080 requires CUDA 12.8+) ──────────
# torchaudio/torchvision not needed for LLM training — omit to avoid ABI issues
RUN pip install --upgrade pip setuptools wheel && \
    pip install \
        torch==2.7.0 \
        --index-url https://download.pytorch.org/whl/cu128

# ── Unsloth — fastest LoRA fine-tuning library ────────────────────────────────
# unsloth_zoo is a required dependency of the git version of unsloth
RUN pip install unsloth_zoo && \
    pip install "unsloth @ git+https://github.com/unslothai/unsloth.git"

# ── HuggingFace training stack ────────────────────────────────────────────────
RUN pip install \
    transformers \
    datasets \
    peft \
    trl \
    accelerate \
    bitsandbytes \
    huggingface_hub \
    sentencepiece \
    protobuf

# ── PDF processing ────────────────────────────────────────────────────────────
RUN pip install \
    pypdf \
    pdfminer.six \
    pymupdf

# ── Utilities + GPU monitoring ─────────────────────────────────────────────────
RUN pip install \
    numpy \
    scipy \
    scikit-learn \
    pandas \
    pyyaml \
    rich \
    tqdm \
    nvidia-ml-py

# ── Working directory + copy scripts ─────────────────────────────────────────
WORKDIR /workspace

COPY scripts/    /workspace/scripts/
COPY config/     /workspace/config/
COPY run_training.py /workspace/run_training.py

# Volumes expected at runtime (set in docker-compose.train.yml):
#   /books  → ../  (statistics-process-control/ folder, read-only — contains PDFs)
#   /output → ./output/  (read-write — dataset, adapter, checkpoints)

CMD ["python", "/workspace/run_training.py"]
