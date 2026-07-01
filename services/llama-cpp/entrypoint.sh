#!/usr/bin/env bash
# =============================================================================
# Launches llama-server in one of three modes (SERVER_MODE: llm | vlm | embed).
# Every mode serves an OpenAI-compatible API on :8080 so the agent
# orchestrator can talk to all of them the same way.
# =============================================================================
set -euo pipefail

MODE="${SERVER_MODE:-llm}"
MODEL_DIR="${MODEL_DIR:-/models}"
MODEL_PATH="${MODEL_DIR}/${MODEL_FILE:?MODEL_FILE env var is required}"
NGL="${NGL:-999}"
CTX_SIZE="${CTX_SIZE:-8192}"
PARALLEL="${PARALLEL:-2}"
HOST="0.0.0.0"
PORT="8080"

if [[ ! -f "$MODEL_PATH" ]]; then
  echo "FATAL: model file not found: $MODEL_PATH"
  echo "Run ./scripts/download-models.sh to populate the shared 'models' volume."
  exit 1
fi

COMMON=( --host "$HOST" --port "$PORT" -m "$MODEL_PATH"
         --ctx-size "$CTX_SIZE" --parallel "$PARALLEL" )

# NGL=auto  -> let llama.cpp fit as many layers as the (unified) memory allows,
#              offloading the rest to CPU. Robust on the memory-constrained Orin
#              Nano where forcing all layers onto the GPU/NvMap pool can OOM.
# NGL=<int> -> force that many layers onto the GPU (999 = all).
if [[ "$NGL" != "auto" ]]; then
  COMMON+=( --n-gpu-layers "$NGL" )
fi

case "$MODE" in
  llm)
    echo ">> Starting LLM server: $MODEL_PATH"
    # Newer llama.cpp requires an explicit value: --flash-attn on|off|auto
    exec llama-server "${COMMON[@]}" --flash-attn on
    ;;
  vlm)
    MMPROJ_PATH="${MODEL_DIR}/${MMPROJ_FILE:?MMPROJ_FILE env var is required for vlm mode}"
    echo ">> Starting VLM server: $MODEL_PATH (mmproj=$MMPROJ_PATH)"
    exec llama-server "${COMMON[@]}" --mmproj "$MMPROJ_PATH"
    ;;
  embed)
    echo ">> Starting Embeddings server: $MODEL_PATH"
    exec llama-server "${COMMON[@]}" --embedding --pooling mean
    ;;
  *)
    echo "FATAL: unknown SERVER_MODE='$MODE' (expected llm|vlm|embed)"
    exit 1
    ;;
esac
