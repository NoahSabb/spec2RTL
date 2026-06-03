#!/bin/bash
# Experiment A: Qwen as both generator and reflector (baseline)
# 10 test problems, pre-generated RL v2 RTL as starting point
#SBATCH --job-name=agentic-exp-a
#SBATCH --partition=medium
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --exclude=slinky-1
#SBATCH --output=/home/noahsabb/logs/agentic-exp-a-%j.out

set -e
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

    echo "=== Installing iverilog ==="
    apt-get update -qq && apt-get install -y -qq iverilog 2>/dev/null || \
      echo "WARNING: iverilog install failed — compile checks skipped"
    iverilog -V 2>&1 | head -1 || echo "iverilog not available"

    echo "=== Starting Experiment A: Qwen reflector (10 problems) ==="
    python3 /home/noahsabb/spec2rtl/scripts/run_agentic_v2.py \
      --adapter       /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2 \
      --data          /home/noahsabb/data/cid003_test10.jsonl \
      --initial-rtl   /home/noahsabb/results/cid003_eval_rl_v2/rtl \
      --cocotb-errors /home/noahsabb/data/cocotb_errors_rl_v2.json \
      --out           /home/noahsabb/results/cid003_eval_agentic_exp_a \
      --log           /home/noahsabb/logs/agentic_exp_a.jsonl \
      --max-compile-iter 3 \
      --max-cocotb-iter  2 \
      --temperature 0.3 \
      --max-new-tokens 2048

    echo "=== Exp A complete: $(date -u) ==="
  '
