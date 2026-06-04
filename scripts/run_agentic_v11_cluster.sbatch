#!/bin/bash
#SBATCH --job-name=agentic-v11-full
#SBATCH --partition=medium
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=24:00:00
#SBATCH --exclude=slinky-1
#SBATCH --output=/home/noahsabb/logs/agentic-v11-full-%j.out

set -e
mkdir -p /home/noahsabb/logs /home/noahsabb/results

if [ -f ~/.bashrc ]; then
    source ~/.bashrc 2>/dev/null || true
fi

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
    export PATH=/usr/local/bin:/usr/bin:$PATH
    export HF_HOME=/home/noahsabb/.cache/huggingface
    export TOKENIZERS_PARALLELISM=false
    export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    export MASTER_ADDR=localhost
    export MASTER_PORT=29500
    export LOCAL_RANK=0
    export RANK=0
    export WORLD_SIZE=1
    export ANTHROPIC_API_KEY='"$ANTHROPIC_API_KEY"'

    echo "=== GPU sanity check: $(date -u) ==="
    python3 -c "import torch; print(f\"CUDA devices: {torch.cuda.device_count()}\")"

    echo "=== Installing packages ==="
    pip install -q --no-deps --break-system-packages "trl==0.13.0"
    pip install -q --break-system-packages \
      datasets "transformers==4.46.0" "accelerate==0.34.0" "peft==0.13.0" \
      huggingface-hub tokenizers multiprocess xxhash
    pip install -q --break-system-packages bitsandbytes
    pip install -q --break-system-packages anthropic tyro rich

    echo "=== Installing iverilog ==="
    apt-get update -qq && apt-get install -y -qq iverilog 2>/dev/null || \
      echo "WARNING: iverilog install failed — compile checks skipped"
    iverilog -V 2>&1 | head -1 || echo "iverilog not available"

    echo "=== Starting agentic loop v11 (full 78 problems): $(date -u) ==="
    python3 /home/noahsabb/spec2rtl/scripts/run_agentic_v11_cluster.py \
      --adapter       /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2 \
      --data          /home/noahsabb/data/cid003_nonagentic.jsonl \
      --initial-rtl   /home/noahsabb/results/cid003_eval_agentic_v10_full/rtl \
      --cocotb-errors /home/noahsabb/data/cocotb_errors_rl_v2.json \
      --out           /home/noahsabb/results/cid003_eval_agentic_v11_full \
      --log           /home/noahsabb/logs/agentic_v11_full.jsonl \
      --max-compile-iter 3 \
      --max-cocotb-iter  4 \
      --temperature 0.3 \
      --max-new-tokens 2048

    echo "=== Job complete: $(date -u) ==="
  '
