#!/bin/bash
# Full 78-problem agentic run — Claude Sonnet reflector + Qwen RL v2 generator
# Chosen based on reflector comparison: Sonnet 7/10=70% vs Haiku 2/10=20% vs Qwen 0/10=0%
#SBATCH --job-name=agentic-sonnet-full
#SBATCH --partition=medium
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=08:00:00
#SBATCH --exclude=slinky-1
#SBATCH --output=/home/noahsabb/logs/agentic-sonnet-full-%j.out

set -e
source /home/noahsabb/.bashrc 2>/dev/null || true
mkdir -p /home/noahsabb/logs

export HF_HOME=/home/noahsabb/.cache/huggingface
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True

srun \
  --gres=gpu:1 \
  --cpus-per-task=16 \
  --mem=128G \
  --container-image='nvcr.io#nvidia/pytorch:24.12-py3' \
  --container-mounts=/home/noahsabb:/home/noahsabb,/home/_shared:/home/_shared \
  bash -c '
    set -e
    source /home/noahsabb/.bashrc 2>/dev/null || true
    export PATH=/usr/local/bin:/usr/bin:$PATH
    export HF_HOME=/home/noahsabb/.cache/huggingface
    export TOKENIZERS_PARALLELISM=false
    export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    export MASTER_ADDR=localhost
    export MASTER_PORT=29500
    export LOCAL_RANK=0
    export RANK=0
    export WORLD_SIZE=1

    echo "=== GPU sanity check ==="
    python3 -c "import torch; print(f\"CUDA devices: {torch.cuda.device_count()}\", flush=True)"

    echo "=== Installing packages ==="
    pip install -q --no-deps --break-system-packages "trl==0.13.0"
    pip install -q --break-system-packages \
      datasets "transformers==4.46.0" "accelerate==0.34.0" "peft==0.13.0" \
      huggingface-hub tokenizers multiprocess xxhash
    pip install -q --break-system-packages bitsandbytes
    pip install -q --break-system-packages tyro rich
    pip install -q --break-system-packages anthropic

    echo "=== Installing iverilog ==="
    apt-get update -qq && apt-get install -y -qq iverilog 2>/dev/null || \
      echo "WARNING: iverilog install failed — compile checks skipped"
    iverilog -V 2>&1 | head -1 || echo "iverilog not available"

    echo "=== Starting full 78-problem run: Sonnet reflector + Qwen generator ==="
    python3 /home/noahsabb/spec2rtl/scripts/run_agentic_sonnet.py \
      --adapter       /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2 \
      --data          /home/noahsabb/data/cid003_nonagentic.jsonl \
      --initial-rtl   /home/noahsabb/results/cid003_eval_rl_v2/rtl \
      --cocotb-errors /home/noahsabb/data/cocotb_errors_rl_v2.json \
      --out           /home/noahsabb/results/cid003_eval_agentic_sonnet_full \
      --log           /home/noahsabb/logs/agentic_sonnet_full.jsonl \
      --max-compile-iter 3 \
      --max-cocotb-iter  2 \
      --temperature 0.3 \
      --max-new-tokens 2048

    echo "=== Full run complete: $(date -u) ==="
  '
