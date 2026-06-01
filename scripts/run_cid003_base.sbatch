#!/bin/bash
#SBATCH --partition=medium
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --time=08:00:00
#SBATCH --output=/home/noahsabb/logs/cid003-base-%j.out
#SBATCH --job-name=cid003-base

set -e
mkdir -p /home/noahsabb/logs /home/noahsabb/results

export HF_HOME=/home/noahsabb/.cache/huggingface
export TOKENIZERS_PARALLELISM=false

echo "=== Base model eval (no LoRA adapter) ==="
echo "Results: /home/noahsabb/results/cid003_eval_base/"

srun \
  --gres=gpu:1 \
  --cpus-per-task=16 \
  --container-image='nvcr.io#nvidia/pytorch:24.12-py3' \
  --container-mounts=/home/noahsabb:/home/noahsabb,/home/_shared:/home/_shared \
  bash -c '
    set -e
    export PATH=/usr/local/bin:/usr/bin:$PATH

    echo "=== GPU sanity check ==="
    python3 -c "import torch; print(f\"CUDA devices: {torch.cuda.device_count()}\", flush=True)"

    echo "=== Installing packages ==="
    pip install -q --no-deps --break-system-packages "trl==0.13.0"
    pip install -q --break-system-packages \
      datasets \
      "transformers==4.46.0" \
      "accelerate==0.34.0" \
      "peft==0.13.0" \
      huggingface-hub tokenizers multiprocess xxhash
    pip install -q --break-system-packages bitsandbytes
    pip install -q --break-system-packages tyro rich

    echo "=== Installing iverilog for scoring ==="
    apt-get update -qq && apt-get install -y -qq iverilog 2>/dev/null || \
      echo "WARNING: iverilog install failed — compile check will be skipped"
    iverilog -V 2>&1 | head -1 || echo "iverilog not available"

    echo "=== Starting inference (base model, no adapter) ==="
    export HF_HOME=/home/noahsabb/.cache/huggingface
    export TOKENIZERS_PARALLELISM=false
    export MASTER_ADDR=localhost
    export MASTER_PORT=29500
    export LOCAL_RANK=0
    export RANK=0
    export WORLD_SIZE=1

    python3 /home/noahsabb/spec2rtl/scripts/run_cid003_eval.py \
        --data    /home/noahsabb/data/cid003_nonagentic.jsonl \
        --out     /home/noahsabb/results/cid003_eval_base

    echo "=== Job complete ==="
    echo "Results at: /home/noahsabb/results/cid003_eval_base/"
  '
