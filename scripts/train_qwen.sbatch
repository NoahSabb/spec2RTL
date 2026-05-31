#!/bin/bash
#SBATCH --partition=medium
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
#SBATCH --output=/home/noahsabb/logs/train_qwen-%j.out
#SBATCH --job-name=qwen-spec2rtl
#SBATCH --mem=0

# ── Prereqs ───────────────────────────────────────────────────────────────────
# Before submitting:
#   1. Copy data and scripts to cluster:
#        kubectl cp data/final_finetune_full.jsonl  <pod>:/home/noahsabb/data/final_finetune.jsonl -c login
#        kubectl cp scripts/train_qwen.py      <pod>:/home/noahsabb/spec2rtl/scripts/train_qwen.py -c login
#        kubectl cp scripts/train_qwen.sbatch  <pod>:/home/noahsabb/spec2rtl/scripts/train_qwen.sbatch -c login
#   2. Set R2 credentials in your home dir's ~/.r2_creds (sourced below):
#        export AWS_ACCESS_KEY_ID=<r2-access-key>
#        export AWS_SECRET_ACCESS_KEY=<r2-secret-key>
#   3. Submit: sbatch scripts/train_qwen.sbatch

set -e
mkdir -p /home/noahsabb/logs

# ── Env vars ─────────────────────────────────────────────────────────────────
export HF_HOME=/home/noahsabb/.cache/huggingface  # personal writable cache for downloads
# HF_HUB_CACHE intentionally unset — defaults to $HF_HOME/hub (writable).
# find_model_path() in train_qwen.py checks /home/_shared/models/hub manually first.
export TOKENIZERS_PARALLELISM=false
export CLOUDFLARE_R2_BUCKET=spec2rtl-checkpoints
export CLOUDFLARE_R2_ENDPOINT=https://a5000aacae3e74e21534569c0bf2909b.r2.cloudflarestorage.com

# Source R2 credentials if file exists (keep these out of the sbatch file itself)
[ -f /home/noahsabb/.r2_creds ] && source /home/noahsabb/.r2_creds

# ── Container ────────────────────────────────────────────────────────────────
srun \
  --gres=gpu:1 \
  --cpus-per-task=16 \
  --container-image='nvcr.io#nvidia/pytorch:24.12-py3' \
  --container-mounts=/home/noahsabb:/home/noahsabb,/home/_shared:/home/_shared \
  bash -c '
    set -e

    echo "=== GPU sanity check ==="
    python3 -c "import torch; print(f\"CUDA devices: {torch.cuda.device_count()}\", flush=True)"

    echo "=== Installing packages ==="
    # The NGC 24.12-py3 container already ships matched versions of:
    # torch, transformers, bitsandbytes, peft, accelerate, datasets, safetensors, etc.
    # Upgrading ANY of these breaks the nightly-torch ABI. Use --no-deps everywhere.
    # --break-system-packages required by PEP 668 in newer container builds.
    #
    # trl (SFTTrainer) is the one package not in the container.
    # tyro + rich are trl's small non-container runtime deps.
    pip install -q --no-deps --break-system-packages "trl==0.13.0"
    pip install -q --break-system-packages tyro rich awscli

    echo "=== Starting training ==="
    python3 -m torch.distributed.run \
      --standalone \
      --nproc-per-node=1 \
      /home/noahsabb/spec2rtl/scripts/train_qwen.py \
        --data   /home/noahsabb/data/final_finetune.jsonl \
        --out    /home/noahsabb/checkpoints/spec2rtl \
        --epochs 5 \
        --batch-size 2 \
        --grad-accum 8 \
        --lr 1e-4

    echo "=== Job complete ==="
  '
