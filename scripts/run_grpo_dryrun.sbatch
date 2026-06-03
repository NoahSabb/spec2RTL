#!/bin/bash
#SBATCH --partition=medium
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --time=01:30:00
#SBATCH --output=/home/noahsabb/logs/grpo-dryrun-%j.out
#SBATCH --job-name=grpo-dryrun

# Dry run: 5 problems, 2 GRPO steps.
# Verifies: iverilog reward function, model fits in VRAM, TRL API compatibility.
# Takes ~5-15 min after model load.

set -e
mkdir -p /home/noahsabb/logs

export HF_HOME=/home/noahsabb/.cache/huggingface
export TOKENIZERS_PARALLELISM=false

echo "=== GRPO dry run: 5 problems, 2 steps ==="

srun \
  --gres=gpu:1 \
  --cpus-per-task=16 \
  --container-image='nvcr.io#nvidia/pytorch:24.12-py3' \
  --container-mounts=/home/noahsabb:/home/noahsabb,/home/_shared:/home/_shared \
  bash -c '
    set -e
    export PATH=/usr/local/bin:/usr/bin:$PATH

    echo "=== GPU sanity check ==="
    python3 -c "import torch; print(f\"CUDA devices: {torch.cuda.device_count()}\")"

    echo "=== Installing packages ==="
    pip install -q --no-deps --break-system-packages "trl==0.13.0"
    pip install -q --break-system-packages \
      datasets \
      "transformers==4.46.0" \
      "accelerate==0.34.0" \
      "peft==0.13.0" \
      huggingface-hub tokenizers multiprocess xxhash
    pip install -q --break-system-packages bitsandbytes
    pip install -q --break-system-packages tyro rich awscli

    echo "=== Installing iverilog ==="
    apt-get update -qq && apt-get install -y -qq iverilog 2>/dev/null || \
      echo "WARNING: iverilog install failed"
    iverilog -V 2>&1 | head -1 || echo "iverilog not available"

    echo "=== Starting GRPO dry run ==="
    export HF_HOME=/home/noahsabb/.cache/huggingface
    export TOKENIZERS_PARALLELISM=false
    export MASTER_ADDR=localhost
    export MASTER_PORT=29500
    export LOCAL_RANK=0
    export RANK=0
    export WORLD_SIZE=1

    python3 /home/noahsabb/spec2rtl/scripts/train_grpo.py \
        --adapter          /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-35e941c1 \
        --out              /tmp/grpo_dry_run \
        --dry-run \
        --max-problems     5 \
        --max-steps        2 \
        --max-new-tokens   256 \
        --num-generations  2 \
        --no-r2-upload

    echo "=== DRY RUN COMPLETE ==="
  '
