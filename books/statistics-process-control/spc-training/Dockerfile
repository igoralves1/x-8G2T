# ── SPC Training Container ────────────────────────────────────────────────────
# Supports NVIDIA RTX 5080 (Blackwell architecture, CUDA 12.8+)
# Build once, run training and extraction inside.

FROM nvidia/cuda:12.8.1-devel-ubuntu22.04

LABEL description="SPC LLM Fine-Tuning Environment — Unsloth + Llama-3.2-3B"

ENV DEBIAN_FRONTEND=noninteractive
ENV PYTHONUNBUFFERED=1
ENV PYTHONDONTWRITEBYTECODE=1

# System dependencies
RUN apt-get update && apt-get install -y \
    python3.11 \
    python3.11-pip \
    python3.11-venv \
    python3-dev \
    git \
    wget \
    curl \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Make python3.11 the default
RUN update-alternatives --install /usr/bin/python3 python3 /usr/bin/python3.11 1 && \
    update-alternatives --install /usr/bin/pip3 pip3 /usr/bin/pip3.11 1 && \
    ln -sf /usr/bin/python3 /usr/bin/python && \
    ln -sf /usr/bin/pip3 /usr/bin/pip

# Upgrade pip
RUN pip install --upgrade pip setuptools wheel

# PyTorch with CUDA 12.8 support (required for RTX 5080 Blackwell)
RUN pip install torch==2.6.0 torchvision torchaudio \
    --index-url https://download.pytorch.org/whl/cu128

# Core training stack
# Unsloth: fastest LoRA fine-tuning library, handles GGUF export natively
RUN pip install "unsloth[cu128-torch260] @ git+https://github.com/unslothai/unsloth.git"

# Supporting libraries
RUN pip install \
    trl==0.15.2 \
    peft==0.14.0 \
    accelerate==1.3.0 \
    bitsandbytes==0.45.3 \
    transformers==4.48.3 \
    datasets==3.2.0 \
    huggingface_hub \
    sentencepiece \
    protobuf \
    pyyaml \
    pypdf \
    rich \
    tqdm

# Working directory inside the container
WORKDIR /workspace

# Copy training scripts
COPY scripts/ /workspace/scripts/
COPY config/ /workspace/config/

# The following are mounted as Docker volumes at runtime:
#   /books  → books/statistics-process-control/  (read-only, source PDFs)
#   /output → books/statistics-process-control/spc-training/output/ (read-write)

CMD ["python", "scripts/2_train.py"]
