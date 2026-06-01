#!/bin/bash
#SBATCH --partition=medium
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
#SBATCH --output=/home/noahsabb/logs/cid003-eval-%j.out
#SBATCH --job-name=cid003-eval

# ── Prereqs ───────────────────────────────────────────────────────────────────
# Before submitting:
#   kubectl cp data/cid003_nonagentic.jsonl <pod>:/home/noahsabb/data/cid003_nonagentic.jsonl -c login
#   kubectl cp scripts/run_cid003_eval.py   <pod>:/home/noahsabb/spec2rtl/scripts/run_cid003_eval.py -c login
#   kubectl cp scripts/run_cid003_eval.sbatch <pod>:/home/noahsabb/spec2rtl/scripts/run_cid003_eval.sbatch -c login
#   sbatch spec2rtl/scripts/run_cid003_eval.sbatch

set -e
mkdir -p /home/noahsabb/logs /home/noahsabb/results

# ── Env vars ──────────────────────────────────────────────────────────────────
export HF_HOME=/home/noahsabb/.cache/huggingface
export TOKENIZERS_PARALLELISM=false

ADAPTER_LOCAL=/home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-35e941c1
DATA_PATH=/home/noahsabb/data/cid003_nonagentic.jsonl

echo "=== Using local adapter: ${ADAPTER_LOCAL} ==="
ls "${ADAPTER_LOCAL}/adapter_model.safetensors" && echo "Adapter confirmed present" || { echo "ERROR: adapter missing"; exit 1; }

# ── Run inference + scoring inside container ───────────────────────────────────
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
    # Core ML packages (proven order from job 293)
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
      echo "WARNING: apt-get install iverilog failed — compile check will be skipped"

    iverilog -V 2>&1 | head -1 || echo "iverilog not available"

    echo "=== Starting inference ==="
    export HF_HOME=/home/noahsabb/.cache/huggingface
    export TOKENIZERS_PARALLELISM=false
    export MASTER_ADDR=localhost
    export MASTER_PORT=29500
    export LOCAL_RANK=0
    export RANK=0
    export WORLD_SIZE=1

    python3 /home/noahsabb/spec2rtl/scripts/run_cid003_eval.py \
        --data    /home/noahsabb/data/cid003_nonagentic.jsonl \
        --adapter /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-35e941c1 \
        --out     /home/noahsabb/results/cid003_eval

    echo "=== Job complete ==="
    echo "Results at: /home/noahsabb/results/cid003_eval/"
    echo ""
    echo "To run full CVDP harness scoring (requires Docker on Mac):"
    echo "  kubectl cp slurm/<pod>:/home/noahsabb/results/cid003_eval/ . -c login"
    echo "  # Then run CVDP benchmark with --runs-file pointing to the saved outputs"
  '
