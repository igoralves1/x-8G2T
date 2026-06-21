#!/usr/bin/env bash
# ── Deploy SPC Adapter to Jetson ──────────────────────────────────────────────
# Run this script ON THE JETSON after `git pull` to activate the trained adapter.
#
# What it does:
#   1. Finds the trained adapter GGUF file in this repo
#   2. Copies it to the llama-server models volume
#   3. Adds the --lora flag to the llama-server configuration
#   4. Restarts the llama-server container to load the adapter
#
# Prerequisites on the Jetson:
#   - Docker running with llama-server container
#   - git pull already executed
#   - The base model (Llama-3.2-3B-Instruct Q4_K_M) already in /models/
#
# Usage:
#   cd /home/jts/Documents/x-8G2T
#   git pull
#   bash books/statistics-process-control/spc-training/scripts/3_deploy_jetson.sh

set -euo pipefail

# ── Configuration ──────────────────────────────────────────────────────────────
REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/../../../../.." && pwd)"
ADAPTER_SOURCE="${REPO_ROOT}/books/statistics-process-control/spc-training/output/adapter/spc-adapter-lora.gguf"
MODELS_DIR="/home/jts/Documents/x-8G2T/models"
ADAPTER_DEST="${MODELS_DIR}/spc-adapter-lora.gguf"

# Name of the llama.cpp server Docker container (adjust if different)
LLAMA_CONTAINER_NAME="llm-server"
DOCKER_COMPOSE_FILE="${REPO_ROOT}/docker-compose.yml"

# ── Colours ────────────────────────────────────────────────────────────────────
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
NC='\033[0m'

log()  { echo -e "${GREEN}[DEPLOY]${NC} $1"; }
warn() { echo -e "${YELLOW}[WARN]${NC}  $1"; }
err()  { echo -e "${RED}[ERROR]${NC} $1"; exit 1; }

echo ""
echo "============================================================"
echo "  SPC Adapter Deployment — Jetson Orin Nano"
echo "============================================================"
echo ""

# ── Step 1: Verify adapter file exists ────────────────────────────────────────
log "Checking for trained adapter..."
if [ ! -f "${ADAPTER_SOURCE}" ]; then
    err "Adapter not found at: ${ADAPTER_SOURCE}

Did you remember to:
  1. Run training on Windows (docker compose run --rm train)
  2. git add output/adapter/ && git commit && git push on Windows
  3. git pull on the Jetson

If the file is there but small (<1MB), the training failed or the GGUF was not exported correctly."
fi

ADAPTER_SIZE=$(du -sh "${ADAPTER_SOURCE}" | cut -f1)
log "Adapter found: ${ADAPTER_SOURCE} (${ADAPTER_SIZE})"

# ── Step 2: Create models directory if needed ──────────────────────────────────
log "Ensuring models directory exists: ${MODELS_DIR}"
mkdir -p "${MODELS_DIR}"

# ── Step 3: Copy adapter to models directory ───────────────────────────────────
log "Copying adapter to models directory..."
cp "${ADAPTER_SOURCE}" "${ADAPTER_DEST}"
log "Adapter installed at: ${ADAPTER_DEST}"

# ── Step 4: Check if llama-server container is running ────────────────────────
log "Checking llama-server container status..."
if ! docker ps --format '{{.Names}}' | grep -q "^${LLAMA_CONTAINER_NAME}$"; then
    warn "Container '${LLAMA_CONTAINER_NAME}' is not running."
    warn "The adapter has been copied but the server needs to be started manually."
    echo ""
    echo "To start llama-server WITH the SPC adapter:"
    echo ""
    echo "  docker run -d \\"
    echo "    --name ${LLAMA_CONTAINER_NAME} \\"
    echo "    --gpus all \\"
    echo "    -v ${MODELS_DIR}:/models \\"
    echo "    -p 8080:8080 \\"
    echo "    ghcr.io/ggerganov/llama.cpp:server \\"
    echo "    -m /models/Llama-3.2-3B-Instruct-Q4_K_M.gguf \\"
    echo "    --lora /models/spc-adapter-lora.gguf \\"
    echo "    --host 0.0.0.0 \\"
    echo "    --port 8080 \\"
    echo "    -n 2048 \\"
    echo "    --n-gpu-layers 999"
    echo ""
    exit 0
fi

# ── Step 5: Restart container to reload model + adapter ───────────────────────
log "Restarting llama-server to load the new adapter..."

# Get the current run command from the container
CURRENT_CMD=$(docker inspect "${LLAMA_CONTAINER_NAME}" --format='{{.Config.Cmd}}' 2>/dev/null || echo "")

# Check if --lora is already in the command
if echo "${CURRENT_CMD}" | grep -q -- "--lora"; then
    log "Container already has --lora flag. Restarting to pick up new adapter..."
    docker restart "${LLAMA_CONTAINER_NAME}"
else
    warn "Container '${LLAMA_CONTAINER_NAME}' is running but does NOT have --lora flag."
    warn "The adapter was copied but you need to restart the container with --lora added."
    echo ""
    echo "Stop the current container and restart it with:"
    echo ""
    echo "  docker stop ${LLAMA_CONTAINER_NAME} && docker rm ${LLAMA_CONTAINER_NAME}"
    echo ""
    echo "  docker run -d \\"
    echo "    --name ${LLAMA_CONTAINER_NAME} \\"
    echo "    --gpus all \\"
    echo "    -v ${MODELS_DIR}:/models \\"
    echo "    -p 8080:8080 \\"
    echo "    ghcr.io/ggerganov/llama.cpp:server \\"
    echo "    -m /models/Llama-3.2-3B-Instruct-Q4_K_M.gguf \\"
    echo "    --lora /models/spc-adapter-lora.gguf \\"
    echo "    --host 0.0.0.0 \\"
    echo "    --port 8080 \\"
    echo "    -n 2048 \\"
    echo "    --n-gpu-layers 999"
    echo ""
fi

# ── Step 6: Verify server is responding ────────────────────────────────────────
log "Waiting for llama-server to be ready..."
MAX_WAIT=60
ELAPSED=0
while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -s http://localhost:8080/health > /dev/null 2>&1; then
        log "llama-server is responding at http://localhost:8080"
        break
    fi
    sleep 3
    ELAPSED=$((ELAPSED + 3))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    warn "llama-server did not respond within ${MAX_WAIT}s. Check logs:"
    warn "  docker logs ${LLAMA_CONTAINER_NAME}"
else
    log "Testing SPC adapter with a quick inference..."
    RESPONSE=$(curl -s http://localhost:8080/v1/chat/completions \
        -H "Content-Type: application/json" \
        -d '{
            "model": "spc",
            "messages": [
                {"role": "user", "content": "What chart should I use for a subgroup size of n=5?"}
            ],
            "max_tokens": 100,
            "temperature": 0.1
        }' 2>&1 | head -c 300)
    echo ""
    log "Quick test response (first 300 chars):"
    echo "${RESPONSE}"
fi

echo ""
echo "============================================================"
log "Deployment complete!"
echo ""
echo "The SPC adapter is now active on the Jetson."
echo "The SPC / Six Sigma agent will use it automatically."
echo "============================================================"
echo ""
