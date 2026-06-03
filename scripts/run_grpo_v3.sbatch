#!/bin/bash
#SBATCH --partition=medium
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=16
#SBATCH --time=24:00:00
#SBATCH --output=/home/noahsabb/logs/rl-grpo-v3-%j.out
#SBATCH --job-name=rl-grpo-v3
#SBATCH --mem=128G
#SBATCH --exclude=slinky-1

# RL GRPO v3 — starts from RL v2 adapter, hybrid cocotb reward.
# Phase 1: Training (3 epochs × 78 problems = 234 steps, G=4, max_new_tokens=512)
# Phase 2: Eval on cid003 (same iverilog-scoring script as job 384)
#
# Timing estimate (based on v2 actual ~83s/step):
#   G=4×512tok vs v2 G=2×256tok → ~4× more generation tokens
#   Pessimistic: 83s × 4 = ~332s/step × 234 = ~21.6h training
#   Optimistic:  83s × 2 = ~166s/step × 234 = ~10.8h training  (most probs short)
#   Eval: ~2h | Setup: ~15min | Budget: 24h
#
# Before submitting:
#   1. Run dry run and confirm step times:
#      sbatch spec2rtl/scripts/run_grpo_v3_dryrun.sbatch
#   2. If step times consistently > 600s, reduce --max-new-tokens to 384 or 256.
#   3. Copy scripts to cluster:
#      kubectl cp scripts/train_grpo_v3.py <pod>:/home/noahsabb/spec2rtl/scripts/ -c login
#      kubectl cp scripts/run_grpo_v3.sbatch <pod>:/home/noahsabb/spec2rtl/scripts/ -c login
#      kubectl cp scripts/run_grpo_v3_dryrun.sbatch <pod>:/home/noahsabb/spec2rtl/scripts/ -c login

set -e
mkdir -p /home/noahsabb/logs \
         /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v3 \
         /home/noahsabb/results/cid003_eval_rl_v3

export HF_HOME=/home/noahsabb/.cache/huggingface
export TOKENIZERS_PARALLELISM=false
export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
export CLOUDFLARE_R2_ENDPOINT=https://a5000aacae3e74e21534569c0bf2909b.r2.cloudflarestorage.com
[ -f /home/noahsabb/.r2_creds ] && source /home/noahsabb/.r2_creds

echo "=== Job: rl-grpo-v3  JOB_ID=${SLURM_JOB_ID}  NODE=${SLURM_NODELIST} ==="
echo "=== Phase 1: GRPO training (3 epochs, 78 problems, G=4, max_new_tokens=512, lr=3e-6) ==="

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
      echo "WARNING: iverilog install failed — rewards will all be 0.0"
    iverilog -V 2>&1 | head -1 || echo "iverilog not available"

    echo "=== Starting RL v3 training ==="
    export HF_HOME=/home/noahsabb/.cache/huggingface
    export TOKENIZERS_PARALLELISM=false
    export PYTORCH_CUDA_ALLOC_CONF=expandable_segments:True
    export MASTER_ADDR=localhost
    export MASTER_PORT=29500
    export LOCAL_RANK=0
    export RANK=0
    export WORLD_SIZE=1
    [ -f /home/noahsabb/.r2_creds ] && source /home/noahsabb/.r2_creds
    export CLOUDFLARE_R2_ENDPOINT=https://a5000aacae3e74e21534569c0bf2909b.r2.cloudflarestorage.com

    python3 /home/noahsabb/spec2rtl/scripts/train_grpo_v3.py \
        --sft-adapter      /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-35e941c1 \
        --adapter          /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2 \
        --out              /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v3 \
        --bench-dir        /home/noahsabb/spec2rtl/cvdp_benchmark \
        --epochs           3 \
        --lr               3e-6 \
        --max-new-tokens   512 \
        --num-generations  4

    echo "=== Training complete ==="
    ls -lh /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v3/ || true

    echo ""
    echo "=== Phase 2: Eval on cid003 (same script as job 384) ==="

    python3 /home/noahsabb/spec2rtl/scripts/run_cid003_eval.py \
        --adapter /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v3 \
        --out     /home/noahsabb/results/cid003_eval_rl_v3

    echo "=== Job complete ==="
    echo ""
    echo "Results:"
    cat /home/noahsabb/results/cid003_eval_rl_v3/summary.txt 2>/dev/null || true
  '
