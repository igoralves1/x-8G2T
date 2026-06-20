#!/usr/bin/env bash
# =============================================================================
# Download the GGUF models into the shared docker volume used by the three
# llama.cpp inference servers. Runs a tiny throw-away container that mounts the
# volume, so you do not need anything installed on the host besides Docker.
#
# Models (all open / ungated community GGUF builds):
#   LLM   : Llama-3.2-3B-Instruct  Q4_K_M
#   VLM   : SmolVLM2-2.2B-Instruct Q4_K_M  (+ f16 mmproj projector)
#   Embed : nomic-embed-text-v1.5  Q8_0    (768-dim)
#
# Override the volume name with VOLUME=... if your compose project differs.
# =============================================================================
set -euo pipefail

VOLUME="${VOLUME:-x-8g2t_models}"
HF="https://huggingface.co"

# Ensure the volume exists (compose also creates it, this is just for safety).
docker volume create "$VOLUME" >/dev/null

declare -A FILES=(
  ["Llama-3.2-3B-Instruct-Q4_K_M.gguf"]="$HF/bartowski/Llama-3.2-3B-Instruct-GGUF/resolve/main/Llama-3.2-3B-Instruct-Q4_K_M.gguf"
  ["SmolVLM2-2.2B-Instruct-Q4_K_M.gguf"]="$HF/ggml-org/SmolVLM2-2.2B-Instruct-GGUF/resolve/main/SmolVLM2-2.2B-Instruct-Q4_K_M.gguf"
  ["mmproj-SmolVLM2-2.2B-Instruct-f16.gguf"]="$HF/ggml-org/SmolVLM2-2.2B-Instruct-GGUF/resolve/main/mmproj-SmolVLM2-2.2B-Instruct-f16.gguf"
  ["nomic-embed-text-v1.5.Q8_0.gguf"]="$HF/nomic-ai/nomic-embed-text-v1.5-GGUF/resolve/main/nomic-embed-text-v1.5.Q8_0.gguf"
)

AUTH=()
if [[ -n "${HF_TOKEN:-}" ]]; then
  AUTH=(-H "Authorization: Bearer ${HF_TOKEN}")
fi

for name in "${!FILES[@]}"; do
  url="${FILES[$name]}"
  echo ">> Fetching ${name}"
  docker run --rm -v "${VOLUME}:/models" curlimages/curl:8.9.1 \
    -L --fail --retry 3 -C - "${AUTH[@]}" -o "/models/${name}" "${url}"
done

echo ""
echo "All models downloaded into volume '${VOLUME}'. Listing:"
docker run --rm -v "${VOLUME}:/models" alpine ls -lh /models
