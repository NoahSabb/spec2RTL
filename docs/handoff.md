# spec2RTL — New Chat Handoff

## What This Project Is

Fine-tuning **Qwen2.5-Coder-32B-Instruct** with QLoRA on (spec, Verilog RTL) training pairs,
so it can be used later as a cheaper generator inside an agentic loop that writes and self-corrects
Verilog from natural language hardware specs.

Benchmark: CVDP cid003 (78 problems). Baseline (single-shot Sonnet 4.6): 55.13%.

---

## Security Constraint

The `.env` file at project root contains API keys — **never reveal or echo their values**.
You may reference variable names only:
- `ANTHROPIC_API_KEY`
- `OPENROUTER_API_KEY`
- `DIGITALOCEAN_API_KEY`
- `CLOUDFLARE_R2_BUCKET` = `spec2rtl-checkpoints`
- `CLOUDFLARE_R2_ENDPOINT` = `https://a5000aacae3e74e21534569c0bf2909b.r2.cloudflarestorage.com`

---

## Cluster Environment

- **Cluster**: 32× H100 SLURM cluster (Stanford/Omniva), accessed via `kubectl exec`
- **Username**: `noahsabb`
- **Home dir on cluster**: `/home/noahsabb`
- **Login pod selector**: `kubectl get pod -n slurm -l stanford/user=noahsabb`
- **Pod name pattern**: `slurm-login-noahsabb-<hash>`
- **Shared model cache**: `/home/_shared/models/hub` (read-only, check here before downloading)
- **No SSH** — all file movement via `kubectl cp`
- **Single-node only**: all partitions MaxNodes=1, use `torchrun --standalone --nproc-per-node=N`
- **Container runtime**: pyxis + enroot; always pass `--cpus-per-task=32` on container jobs

### Useful SLURM commands
```bash
kubectl get pod -n slurm -l stanford/user=noahsabb   # find your pod name
kubectl exec -it -n slurm <pod> -c login -- runuser -u noahsabb -- bash -l
sbatch scripts/train_qwen.sbatch
squeue -u noahsabb
sacct -u noahsabb -S today
```

---

## Project Layout

```
spec2RTL/
├── .env                          # API keys (never reveal values)
├── data/
│   ├── prepare_finetune_data.py  # main data pipeline
│   ├── fetch_seed_data.py        # downloads 312 VerilogEval seed pairs
│   ├── seed_finetune.jsonl       # 312 human-authored (spec, RTL) pairs ✓
│   ├── final_finetune.jsonl      # OUTPUT — written when pipeline finishes
│   ├── pipeline_run.log          # live log of current pipeline run
│   └── cache/
│       ├── validated_modules_limit30000.json   # 2563 iverilog-validated Verilog modules ✓
│       ├── spec_pairs_2563.json                # partial → being completed by running process
│       └── scored_pairs_21.json               # old small test run, ignore
├── scripts/
│   ├── train_qwen.py             # QLoRA fine-tuning script
│   ├── train_qwen.sbatch         # sbatch job submission script
│   └── setup_harnesses.py        # pre-copies CVDP harnesses for agentic runs
├── agents/
│   ├── agentic_loop_v1.py        # agentic loop: generator → harness → reflector → coordinator
│   └── agentic_claude_factory.py # factory that wraps the loop as a CVDP-compatible model
└── cvdp_benchmark/               # CVDP benchmark harness (git submodule/separate repo)
    ├── venv/                     # Python venv with benchmark deps (activate this to run bench)
    └── work_*/                   # benchmark run outputs
```

---

## Current Status (as of 2026-05-31 ~00:15 PDT)

### Data Pipeline — MAY STILL BE RUNNING
```bash
# Check if process is running:
ps aux | grep prepare_finetune_data | grep -v grep

# Watch progress:
tail -f data/pipeline_run.log

# Check if output exists yet:
ls -lh data/final_finetune.jsonl
```

**What it does**: generates natural language specs for 2,563 Verilog modules using Claude
Sonnet 4.6 (OSS-Instruct technique), starting from 406 already cached. Then runs Haiku
LLM-as-Judge to filter quality, generates 3 task types, merges with 312 seed pairs, and
writes `data/final_finetune.jsonl`.

**Expected output**: ~5,000–6,000 training examples total

---

## Next Steps After Pipeline Finishes

### 1. Verify the output
```bash
wc -l data/final_finetune.jsonl
python3 -c "
import json
with open('data/final_finetune.jsonl') as f:
    samples = [json.loads(l) for l in f]
print(f'Total samples: {len(samples)}')
from collections import Counter
print(Counter(s.get('task_type') for s in samples))
"
```

### 2. Find your cluster pod
```bash
kubectl get pod -n slurm -l stanford/user=noahsabb
# Copy the pod name, e.g. slurm-login-noahsabb-abc123
```

### 3. Create required dirs on cluster
```bash
kubectl exec -it -n slurm <pod> -c login -- runuser -u noahsabb -- bash -c \
  "mkdir -p /home/noahsabb/logs /home/noahsabb/data /home/noahsabb/spec2rtl/scripts"
```

### 4. Copy files to cluster
```bash
POD=<your-pod-name>
kubectl cp data/final_finetune.jsonl   slurm/$POD:/home/noahsabb/data/final_finetune.jsonl -c login
kubectl cp scripts/train_qwen.py       slurm/$POD:/home/noahsabb/spec2rtl/scripts/train_qwen.py -c login
kubectl cp scripts/train_qwen.sbatch   slurm/$POD:/home/noahsabb/spec2rtl/scripts/train_qwen.sbatch -c login
```

### 5. Set up R2 credentials on cluster
The values are in your local `.env` as `CLOUDFLARE_R2_ACCESS_KEY_ID` and `CLOUDFLARE_R2_SECRET_ACCESS_KEY`.
```bash
kubectl exec -it -n slurm $POD -c login -- runuser -u noahsabb -- bash -c "
cat > ~/.r2_creds << 'EOF'
export AWS_ACCESS_KEY_ID=<your-r2-access-key-id>
export AWS_SECRET_ACCESS_KEY=<your-r2-secret-access-key>
EOF
chmod 600 ~/.r2_creds
"
```

### 6. Submit training job
```bash
kubectl exec -it -n slurm $POD -c login -- runuser -u noahsabb -- bash -c \
  "cd /home/noahsabb && sbatch spec2rtl/scripts/train_qwen.sbatch"

# Monitor:
kubectl exec -it -n slurm $POD -c login -- runuser -u noahsabb -- bash -c "squeue -u noahsabb"
```

### 7. Watch training logs
```bash
kubectl exec -it -n slurm $POD -c login -- runuser -u noahsabb -- bash -c \
  "tail -f /home/noahsabb/logs/train_qwen-<jobid>.out"
```

---

## Training Job Details

| Setting | Value |
|---|---|
| Base model | `Qwen/Qwen2.5-Coder-32B-Instruct` |
| Method | QLoRA (4-bit NF4 + LoRA) |
| LoRA r / α | 16 / 32 |
| LoRA targets | q,k,v,o,gate,up,down projections (all 7) |
| Max seq len | 2048 |
| Effective batch | 64 (2 per GPU × 4 GPUs × 8 grad accum) |
| Epochs | 3 |
| LR | 2e-4, cosine schedule |
| Loss | Completion-only (RTL output only, not the spec prompt) |
| Partition | `medium` (5-day max walltime) |
| GPUs | 4× H100 80GB |
| Container | `nvcr.io#nvidia/pytorch:24.12-py3` |
| Checkpoints | Every 400 steps, best-of-2 kept |
| R2 upload | Auto-uploads final adapter to `s3://spec2rtl-checkpoints/adapters/<run_id>/` |

---

## Data Pipeline Details

### What's free vs what costs money

**Free:**
- Downloading 108K raw Verilog files from HuggingFace (`shailja/Verilog_GitHub`)
- iverilog/Verilator compilation checks (local)
- 312 VerilogEval seed pairs from GitHub (git clone)

**Costs money (Sonnet API — OSS-Instruct):**
- Generating natural language SPECS from raw Verilog
- Each Verilog module → 1 Sonnet call → produces the spec that describes it
- Without specs there is no (input, output) pair for the model to learn from
- Cost: ~$23 total for 2,563 calls (~$5 already spent)

### Re-running the pipeline from scratch
```bash
# From project root:
env $(grep -v '^#' .env | xargs) python3 data/prepare_finetune_data.py \
  --limit 30000 \
  --workers 16 \
  --spec-model claude-sonnet-4-6 \
  --seed-jsonl data/seed_finetune.jsonl \
  --skip-download \
  --out data/final_finetune.jsonl
```

`--skip-download` reuses the 2,563 already-validated modules from cache.
The pipeline has **resume support**: if `spec_pairs_2563.json` exists with partial results,
it only calls the API for the missing entries.

---

## Agentic Loop (deferred — not the current focus)

`agents/agentic_loop_v1.py` wraps a generator model in a test-and-fix loop:
generate RTL → run real CVDP Docker harness → Haiku reflector analyzes failures →
Haiku coordinator decides CONTINUE or RESTART → regenerate.

**Plan**: use the fine-tuned Qwen as the generator (cheap) instead of Sonnet (expensive).
**Do not focus on this until the Qwen fine-tune is complete.**

---

## Environment Notes

- Benchmark venv: `cvdp_benchmark/venv/` — activate when running benchmark commands
- Data pipeline uses system Python; packages `anthropic`, `datasets`, `tqdm` are installed
- Load `.env` for API keys: `env $(grep -v '^#' .env | xargs) python3 ...`
- `src/config_manager.py` lives at `cvdp_benchmark/src/config_manager.py`
