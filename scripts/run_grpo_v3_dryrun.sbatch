#!/bin/bash
#SBATCH --partition=medium
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --time=02:00:00
#SBATCH --output=/home/noahsabb/logs/grpo-v3-dryrun-%j.out
#SBATCH --job-name=grpo-v3-dryrun
#SBATCH --mem=128G
#SBATCH --exclude=slinky-1

# Dry run: 5 problems, 2 GRPO steps.
# Verifies: model loads, two-adapter merge, iverilog reward, Docker availability.
# Automatically reports whether Docker is available for cocotb rewards.
# Takes ~20-30 min after model load (G=4, max_new_tokens=512).

set -e
mkdir -p /home/noahsabb/logs

export HF_HOME=/home/noahsabb/.cache/huggingface
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

echo "=== RL v3 dry run: 5 problems, 2 steps ==="
echo "=== JOB_ID=${SLURM_JOB_ID}  NODE=${SLURM_NODELIST} ==="

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

    echo "=== Installing packages (proven pattern from job 293) ==="
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

    echo "=== Docker availability check ==="
    if docker info >/dev/null 2>&1; then
      echo "Docker daemon: AVAILABLE"
      docker image ls cvdp-sim:latest 2>/dev/null && \
        echo "cvdp-sim:latest: FOUND" || \
        echo "cvdp-sim:latest: NOT FOUND — will fall back to iverilog-only reward"
    else
      echo "Docker daemon: NOT AVAILABLE — will use iverilog-only reward (expected on cluster)"
    fi

    echo "=== Starting RL v3 dry run ==="
    export HF_HOME=/home/noahsabb/.cache/huggingface
    export TOKENIZERS_PARALLELISM=false
    export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    export MASTER_ADDR=localhost
    export MASTER_PORT=29500
    export LOCAL_RANK=0
    export RANK=0
    export WORLD_SIZE=1

    python3 /home/noahsabb/spec2rtl/scripts/train_grpo_v3.py \
        --sft-adapter      /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-35e941c1 \
        --adapter          /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2 \
        --out              /tmp/grpo_v3_dry_run \
        --dry-run \
        --max-problems     5 \
        --max-steps        2 \
        --max-new-tokens   512 \
        --num-generations  4 \
        --no-r2-upload

    echo "=== DRY RUN COMPLETE ==="
    echo "If step times < 600s and no OOM: submit full job with sbatch run_grpo_v3.sbatch"
  '
