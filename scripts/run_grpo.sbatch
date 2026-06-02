#!/bin/bash
#SBATCH --partition=medium
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
#SBATCH --output=/home/noahsabb/logs/rl-grpo-v1-%j.out
#SBATCH --job-name=rl-grpo-v1
#SBATCH --mem=0

# ── Prereqs ───────────────────────────────────────────────────────────────────
# Before submitting:
#   kubectl cp scripts/train_grpo.py  <pod>:/home/noahsabb/spec2rtl/scripts/train_grpo.py -c login
#   kubectl cp scripts/run_grpo.sbatch <pod>:/home/noahsabb/spec2rtl/scripts/run_grpo.sbatch -c login
#   sbatch spec2rtl/scripts/run_grpo.sbatch
#
# Expected wall time: ~7-9 h training + ~1.5 h eval = ~9-11 h total (24 h limit)

set -e
mkdir -p /home/noahsabb/logs \
         /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v1 \
         /home/noahsabb/results/cid003_eval_rl_v1

export HF_HOME=/home/noahsabb/.cache/huggingface
export TOKENIZERS_PARALLELISM=false
export CLOUDFLARE_R2_ENDPOINT=https://a5000aacae3e74e21534569c0bf2909b.r2.cloudflarestorage.com
[ -f /home/noahsabb/.r2_creds ] && source /home/noahsabb/.r2_creds

echo "=== Job: rl-grpo-v1  JOB_ID=${SLURM_JOB_ID}  NODE=${SLURM_NODELIST} ==="
echo "=== Phase 1: GRPO training (3 epochs, 78 problems, 4 completions/step) ==="

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

    echo "=== Installing iverilog for reward function ==="
    apt-get update -qq && apt-get install -y -qq iverilog 2>/dev/null || \
      echo "WARNING: iverilog install failed — rewards will all be 0.0"
    iverilog -V 2>&1 | head -1 || echo "iverilog not available"

    echo "=== Starting GRPO training ==="
    export HF_HOME=/home/noahsabb/.cache/huggingface
    export TOKENIZERS_PARALLELISM=false
    export MASTER_ADDR=localhost
    export MASTER_PORT=29500
    export LOCAL_RANK=0
    export RANK=0
    export WORLD_SIZE=1
    [ -f /home/noahsabb/.r2_creds ] && source /home/noahsabb/.r2_creds
    export CLOUDFLARE_R2_ENDPOINT=https://a5000aacae3e74e21534569c0bf2909b.r2.cloudflarestorage.com

    python3 /home/noahsabb/spec2rtl/scripts/train_grpo.py \
        --adapter /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-35e941c1 \
        --out     /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v1 \
        --epochs  3 \
        --lr      5e-6 \
        --max-new-tokens 2048 \
        --num-generations 4

    echo "=== Training complete ==="
    echo "Adapter saved to: /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v1/"
    ls -lh /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v1/ || true

    echo ""
    echo "=== Phase 2: Eval on cid003 (same script as job 384) ==="

    python3 /home/noahsabb/spec2rtl/scripts/run_cid003_eval.py \
        --adapter /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v1 \
        --out     /home/noahsabb/results/cid003_eval_rl_v1

    echo "=== Job complete ==="
    echo ""
    echo "Results:"
    cat /home/noahsabb/results/cid003_eval_rl_v1/summary.txt 2>/dev/null || true
  '
