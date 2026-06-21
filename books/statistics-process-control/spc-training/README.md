# SPC Model Training — Windows RTX 5080

This folder contains everything needed to fine-tune a Llama-3.2-3B language model
to become an expert SPC / Six Sigma analyst. You run training on the Windows PC
(RTX 5080), commit the result to git, and pull it on the Jetson.

---

## What happens end-to-end

```
Windows PC (RTX 5080)              Git                   Jetson Orin Nano
──────────────────────────         ────                  ────────────────
1. git pull this repo         →
2. cd spc-training/
3. docker compose build
4. docker compose run extract →  generates spc-qa-pairs.jsonl (60+ Q&A)
5. docker compose run train   →  trains model, saves adapter (~80MB GGUF)
6. git add output/adapter/
   git commit && git push      →  adapter in git  →   git pull
                                                       bash scripts/3_deploy_jetson.sh
                                                       llama-server loads base + adapter
                                                       SPC agent is now expert-trained
```

---

## Prerequisites on the Windows PC

| Requirement | How to get it |
|-------------|--------------|
| Docker Desktop | docker.com/products/docker-desktop — enable WSL2 backend |
| NVIDIA Container Toolkit | Settings → Docker Engine → add `"runtimes": {"nvidia": ...}` — follow docs.nvidia.com/datacenter/cloud-native/container-toolkit |
| 20 GB free disk | For the base model download cache (~6GB) + output |
| Internet connection | First run downloads Llama-3.2-3B from HuggingFace (~6GB) |

---

## Folder structure

```
spc-training/
├── Dockerfile                   ← Container definition (CUDA 12.8, Unsloth)
├── docker-compose.train.yml     ← Orchestrates extract + train services
├── README.md                    ← This file
│
├── config/
│   └── training_config.yaml    ← Hyperparameters (epochs, LoRA rank, LR, etc.)
│
├── scripts/
│   ├── 1_extract_dataset.py    ← Reads PDFs → generates spc-qa-pairs.jsonl
│   ├── 2_train.py              ← LoRA fine-tuning + GGUF adapter export
│   └── 3_deploy_jetson.sh      ← Run on Jetson after git pull
│
└── output/
    ├── .gitignore               ← Keeps adapter (~80MB), ignores checkpoints (GBs)
    ├── spc-qa-pairs.jsonl       ← Generated training dataset (auto-generated)
    └── adapter/
        └── spc-adapter-lora.gguf   ← THE TRAINED MODEL (commit this to git)
```

---

## Step-by-step: Training on Windows

### Step 0 — Get the repository on Windows

Open PowerShell or Git Bash on the Windows PC:

```powershell
# Navigate to wherever you want the repo
cd C:\Users\YourName\Documents

# Clone (first time only)
git clone https://github.com/igoralves1/x-8G2T.git

# OR if you already have it, just update
cd x-8G2T
git pull
```

### Step 1 — Build the Docker container

```powershell
cd books\statistics-process-control\spc-training

docker compose -f docker-compose.train.yml build
```

This takes 5–15 minutes the first time. It:
- Downloads the CUDA 12.8 base image (~4GB)
- Installs PyTorch for RTX 5080 (Blackwell architecture)
- Installs Unsloth (the training library)
- Copies the training scripts into the container

You only need to build once unless the `Dockerfile` changes.

### Step 2 — Extract the training dataset from the PDF books

```powershell
docker compose -f docker-compose.train.yml run --rm extract
```

This reads the SPC PDF books in `books/statistics-process-control/` and generates
`output/spc-qa-pairs.jsonl`. The dataset always includes 60 hand-crafted, expert
Q&A pairs plus additional pairs extracted from the PDF text.

**Output:** `output/spc-qa-pairs.jsonl`

> **Note:** The PDF books are scanned images, so text extraction may be limited.
> The 60 seed pairs in `scripts/1_extract_dataset.py` ensure training works even
> if the PDFs yield no machine-readable text.

### Step 3 — Run the training

```powershell
docker compose -f docker-compose.train.yml run --rm train
```

This is the main training step. What happens:

1. Downloads `Llama-3.2-3B-Instruct` from HuggingFace (~6GB, first time only)
2. Applies LoRA adapters (only 0.5% of the model's weights are trained)
3. Fine-tunes for 3 epochs on the SPC dataset
4. Exports the adapter in GGUF format

**Expected time:** 10–30 minutes on RTX 5080

**Output:** `output/adapter/spc-adapter-lora.gguf` (~50-80 MB)

**Training progress looks like:**
```
GPU detected: NVIDIA GeForce RTX 5080 (16.0 GB)
Trainable parameters: 10,485,760 (0.35% of 3,212,749,824 total)
Starting training...
  Epoch 1/3 — loss: 1.243
  Epoch 2/3 — loss: 0.892
  Epoch 3/3 — loss: 0.741
Training complete! Time: 18.3 minutes
GGUF adapter saved: /output/adapter/spc-adapter-lora.gguf
File size: 67.4 MB
```

### Step 4 — (Optional) Run extract + train in one command

```powershell
docker compose -f docker-compose.train.yml run --rm all
```

### Step 5 — Commit the adapter to git

```powershell
# From the spc-training/ folder
git add output/adapter/
git add output/spc-qa-pairs.jsonl
git commit -m "feat(spc): trained SPC LoRA adapter v1 — Llama-3.2-3B, 60+ pairs"
git push origin main
```

> The `.gitignore` in `output/` ensures only the adapter (~80MB) is committed,
> not the checkpoints (GBs) or the HuggingFace cache.

---

## Step-by-step: Deploying on the Jetson

On the Jetson:

```bash
cd /home/jts/Documents/x-8G2T
git pull
bash books/statistics-process-control/spc-training/scripts/3_deploy_jetson.sh
```

The script:
1. Copies `output/adapter/spc-adapter-lora.gguf` to the models directory
2. Checks if the llama-server container is running
3. Restarts it (or prints the startup command if it needs the `--lora` flag added)

### Using the adapter with llama.cpp

The Jetson llama-server must be started with two model files:

```bash
docker run -d \
  --name llm-server \
  --gpus all \
  -v /home/jts/Documents/x-8G2T/models:/models \
  -p 8080:8080 \
  ghcr.io/ggerganov/llama.cpp:server \
  -m /models/Llama-3.2-3B-Instruct-Q4_K_M.gguf \
  --lora /models/spc-adapter-lora.gguf \
  --host 0.0.0.0 \
  --port 8080 \
  -n 2048 \
  --n-gpu-layers 999
```

The key flags:
- `-m` → the base model (already on the Jetson, ~2.2GB GGUF)
- `--lora` → the trained adapter (pulled from git, ~80MB GGUF)

The adapter modifies the base model's behavior at inference time WITHOUT merging
the two files. No extra VRAM is needed — the adapter is tiny compared to the base model.

---

## Re-training (iterating)

To improve the model over time:

1. Add more Q&A pairs to the `SEED_PAIRS` list in `scripts/1_extract_dataset.py`
2. Or add more text files (`.txt`, `.md`) to `books/statistics-process-control/`
3. Re-run extract + train on Windows
4. Commit the new adapter and pull on Jetson

Each new training run produces a new `spc-adapter-lora.gguf` that replaces the old one.

---

## Troubleshooting

**"No CUDA GPU detected"**
→ Docker Desktop is not using the GPU. Check: Settings → Resources → GPU is enabled.
→ Verify NVIDIA Container Toolkit is installed: `docker run --rm --gpus all nvidia/cuda:12.8.1-base-ubuntu22.04 nvidia-smi`

**"Dataset not found"**
→ Run the extract step first: `docker compose -f docker-compose.train.yml run --rm extract`

**"GGUF export failed"**
→ Check that `output/adapter/` is writable: `ls -la output/`
→ The safetensors adapter is still saved — you can convert it manually with `llama.cpp`'s `convert_lora_to_gguf.py`

**"Only 60 pairs in dataset"**
→ The PDFs are likely scanned images (not machine-readable text). This is normal.
→ The 60 seed pairs cover the core SPC curriculum. Training will still work.
→ Consider adding markdown or text versions of SPC reference material to the books folder.

**Adapter file is >100MB (GitHub won't accept it)**
→ Edit `config/training_config.yaml`: reduce `lora.r` from 16 to 8
→ This reduces adapter size to ~25MB with minimal quality loss
→ Or use Git LFS: `git lfs track "*.gguf"` then commit normally

---

## What the trained model knows

After training, the SPC agent can:

- Select the correct chart type (I-MR, Xbar-R, Xbar-S, p, np, c, u, CUSUM, EWMA)
  given process conditions without being prompted
- Apply all 8 Nelson Rules to identify out-of-control patterns
- Calculate and interpret Cp, Cpk, Pp, Ppk, DPMO, and Sigma Level
- Recognise Oakland and Zontec pattern types: Shift, Trend, Freak, Mixture,
  Stratification, Cycles, Bunching, Instability
- Explain the difference between common cause and special cause variation
- Provide step-by-step corrective action guidance when a signal is detected
- Understand the IoT context: sensor drift, autocorrelation, subgroup formation
  for high-frequency data streams

The SPC MCP server (`spc-mcp`) handles all deterministic math.
The fine-tuned model provides interpretation, pattern recognition, and guidance.
Together they form the complete SPC / Six Sigma analyst agent.
