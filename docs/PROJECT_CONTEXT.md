# Spec2RTL — Project Context for Claude Code

This document is the authoritative reference for understanding this project. Read it fully before making any suggestions or writing any code.

---

## What This Project Is

A custom agentic RTL (Register-Transfer Level) code generation system, built for CS153 at Stanford. It is modeled after NVIDIA's ACE-RTL paper (arXiv:2602.10218, March 2026) and evaluated on the CVDP benchmark (arXiv:2506.14074).

The core idea: instead of asking an LLM to generate Verilog in a single shot, an agentic loop generates code, runs it through a simulator, and iteratively self-corrects based on real simulation feedback until the design passes.

---

## Research Papers

### Paper 1: CVDP Benchmark (arXiv:2506.14074)
Authors: NVIDIA (Pinckney, Deng, Ho, Tsai, Liu, Zhou, Khailany, Ren)

- 783 human-authored Verilog problems across 13 categories
- State-of-the-art models achieve no more than 34% pass@1 — this is a hard benchmark
- We evaluate on **cid003 only**: RTL Natural Language Spec-to-Code, 78 problems
- Evaluation metric: pass@1 with n=5 samples
- Tools used: Icarus Verilog simulation, Yosys synthesis, Verilator linting
- All evaluation runs inside Docker containers via cocotb test harnesses

### Paper 2: ACE-RTL (arXiv:2602.10218)
Authors: NVIDIA (Deng, Yu, Liu, Pinckney, Khailany, Ren)

This is the architecture we implement. Three components:

**Generator** — An RTL-specialized LLM that generates Verilog from spec. In the paper, this is Qwen2.5-Coder-32B-Instruct fine-tuned on 1.7M RTL samples (spec-to-RTL, editing, and debugging tasks). Fine-tuned with full SFT on 256 A100s for ~10K GPU-hours.

**Reflector** — A frontier LLM (Claude Sonnet in the paper) that reads simulation error logs, analyzes expected-vs-actual signal behavior, and produces structured fix guidance for the Generator.

**Coordinator** — A frontier LLM (Claude Sonnet in the paper) that maintains a self-evolving context across iterations. Tracks debugging history, identified errors, suggested fixes, and outcomes. Decides whether to CONTINUE iterating or RESTART from scratch when stuck.

**Key results from the paper:**
- Claude Sonnet standalone: 51.28% APR on cid003
- ACE-RTL Generator standalone: 52.56% APR on cid003
- ACE-RTL full system: **96.15% APR on cid003** ← this is our target
- Parallel scaling (5 processes): 2.77× speedup with only 1.12× token increase

---

## Our Implementation

### How We Differ From the Paper

The paper used 256 A100s for training. We have 1 H100 × 60 hours. So:

1. We use **QLoRA** instead of full SFT (memory-efficient fine-tuning)
2. We train on **CraftRTL** (high-quality synthetic Verilog dataset from HuggingFace) instead of their 1.7M custom corpus
3. We fine-tune only on **spec-to-RTL** task (not editing/debugging) — a deliberate scope decision, since our Reflector/Coordinator handle the debugging reasoning
4. Our Generator is currently **Claude Sonnet 4.6** (placeholder until fine-tuned Qwen is ready)
5. Our Reflector and Coordinator use **Claude Haiku** instead of Claude Sonnet (cost savings)

### Baseline Results (Established)

| Model | cid003 Pass@1 | Easy | Medium | Problems |
|-------|--------------|------|--------|----------|
| claude-sonnet-4-6 (single-shot) | **55.13%** | 75.61% | 32.43% | 78 |
| rtlcoder-7B (single-shot) | 2.56% | 4.88% | 0.00% | 78 |

**Goal:** Beat 55.13% Pass@1 using fine-tuned Qwen as Generator + agentic loop.

---

## Agentic Loop v1 — Current Architecture

### File: `agents/agentic_loop_v1.py`

**Components:**
- **Generator** — `claude-sonnet-4-6` via `claude_factory.py`. Swappable. When fine-tuned Qwen is ready, swap here.
- **Reflector** — `claude-haiku-4-5-20251001`. Reads CVDP harness simulation errors, produces structured fix guidance.
- **Coordinator** — `claude-haiku-4-5-20251001`. Maintains self-evolving context, decides CONTINUE or RESTART.
- **Testbench Generator** — `claude-sonnet-4-6`. Generates once per problem before loop starts.

**Verification stack (in order):**
1. Verilator lint (`verilator --lint-only -Wall -Wno-DECLFILENAME`) — fast structural check
2. Icarus Verilog simulation (`iverilog` + `vvp`) — compile and run
3. CVDP harness — Docker cocotb tests (final judge, **also used as loop feedback**)

**IMPORTANT:** The loop uses CVDP harness output as the simulation feedback signal — NOT a generic Claude-generated testbench. This was the critical fix. Earlier version used Claude's testbench which was too weak (Claude would pass its own testbench on iteration 1, loop never iterated, CVDP harness then caught failures the testbench missed).

**Current settings:**
```python
num_processes = 1   # parallel processes
max_iterations = 3  # iterations per process
```

**Key functions:**
- `run_simulation(verilog, testbench)` — iverilog compile + vvp run
- `run_verilator_lint(verilog)` — fast structural check
- `generate_testbench(client, spec, verilog)` — Sonnet generates once before loop
- `reflect(client, spec, verilog, sim_result)` — Haiku analyzes errors
- `coordinate(client, context, reflection, verilog, iteration)` — Haiku manages context
- `extract_verilog(response)` — handles CVDP factory tuple return format
- `run_single_process(generator, client, spec, max_iterations)` — single agentic loop
- `run_parallel(generator, client, spec, num_processes, max_iterations)` — parallel processes

### File: `agents/agentic_claude_factory.py`
Wraps `run_parallel()` inside CVDP's `prompt()` interface. Returns CVDP-compatible format: `({"direct_text": verilog}, True)`.

---

## Repository Structure

```
spec2RTL/
├── agents/
│   ├── claude_factory.py           # Single-shot Claude generator (baseline)
│   ├── agentic_claude_factory.py   # Agentic wrapper factory (plugs into CVDP)
│   ├── agentic_loop_v1.py          # Core agentic loop
│   ├── gemini_factory.py
│   └── ollama_factory.py
├── cvdp_benchmark/                 # Git submodule — NVlabs/cvdp_benchmark
│   ├── work_claude_sonnet46_1sample/    # Baseline results (55.13% Pass@1)
│   ├── work_rtlcoder_1sample/           # RTLCoder results (2.56% Pass@1)
│   └── work_claude_agentic_v1/          # Agentic loop results (in progress)
├── data/
│   └── cid003_nonagentic.jsonl     # 78-problem CVDP cid003 dataset
├── docs/
│   └── PROJECT_CONTEXT.md          # This file
├── models/                         # Model configs
├── notebooks/                      # Exploration notebooks
├── results/                        # Saved report.txt files
├── CLAUDE.md                       # Cluster context for Claude Code
├── RUNBOOK.md                      # How to run evaluations
└── .env                            # API keys (never commit)
```

---

## Benchmark Commands

```bash
# Baseline single-shot Claude
caffeinate -i python run_benchmark.py \
  -f ../data/cid003_nonagentic.jsonl \
  -l -m claude-sonnet-4-6 \
  -c ../agents/claude_factory.py \
  -p work_claude_sonnet46_1sample \
  -t 4

# Agentic loop
caffeinate -i python run_benchmark.py \
  -f ../data/cid003_nonagentic.jsonl \
  -l -m claude-sonnet-4-6 \
  -c ../agents/agentic_claude_factory.py \
  -p work_claude_agentic_v1 \
  -t 4

# Single problem test
caffeinate -i python run_benchmark.py \
  -f ../data/cid003_nonagentic.jsonl \
  -l -m claude-sonnet-4-6 \
  -c ../agents/agentic_claude_factory.py \
  -p work_claude_agentic_v1 \
  -t 1 \
  -i cvdp_copilot_gcd_0001
```

---

## Compute Resources

### H100 80GB — CS153 Class Allocation
- Access: via `cs153` alias (see CLAUDE.md)
- Amount: 1 GPU × 60 hours
- Use: QLoRA fine-tuning Qwen2.5-Coder-32B-Instruct on CraftRTL dataset
- Everything downloads fresh onto H100 from HuggingFace — base weights (~65GB) + CraftRTL dataset
- Only the LoRA adapter (~100MB) gets saved to Cloudflare R2 before shutdown

### OpenRouter — $20 inference credits
- Dashboard: https://openrouter.ai
- Use: Claude Sonnet as Reflector and Coordinator during full CVDP benchmark eval (78 problems × 5 runs). Also for baseline Qwen2.5-Coder-32B testing before fine-tuning.
- Key: `OPENROUTER_API_KEY` in `.env`

### DigitalOcean — $250 credits
- Dashboard: https://cloud.digitalocean.com
- Use: Serverless Inference API for serving models. Fine-tuned Qwen serving TBD after training.
- Key: `DIGITALOCEAN_API_KEY` in `.env`

### Cloudflare — $100K credits
- Dashboard: https://dash.cloudflare.com
- Caps: Workers AI $50K · R2 $10K · Cache Reserve $10K
- R2 bucket: `spec2rtl-checkpoints` — stores LoRA checkpoint after H100 training
- Keys: `CLOUDFLARE_R2_ACCESS_KEY_ID`, `CLOUDFLARE_R2_SECRET_ACCESS_KEY`, `CLOUDFLARE_R2_TOKEN`, `CLOUDFLARE_R2_BUCKET`, `CLOUDFLARE_R2_ACCOUNT_ID`, `CLOUDFLARE_R2_ENDPOINT` in `.env`

---

## Priority Order of Operations

1. **H100** → QLoRA fine-tune Qwen2.5-Coder-32B-Instruct on CraftRTL
2. **Cloudflare R2** → Save LoRA checkpoint before shutting H100 down
3. **DigitalOcean** → Pull checkpoint, serve fine-tuned model for inference
4. **Swap Generator** → Replace `claude-sonnet-4-6` with fine-tuned Qwen in agentic loop
5. **OpenRouter** → Run full CVDP-cid003 benchmark (78 problems × 5 runs) with Claude as Reflector/Coordinator
6. **Cloudflare Workers AI** → Backup inference if DigitalOcean runs dry

---

## Environment Variables (`.env`)

```
ANTHROPIC_API_KEY=...
OPENROUTER_API_KEY=...
DIGITALOCEAN_API_KEY=...
CLOUDFLARE_R2_ACCESS_KEY_ID=...
CLOUDFLARE_R2_SECRET_ACCESS_KEY=...
CLOUDFLARE_R2_TOKEN=...
CLOUDFLARE_R2_BUCKET=spec2rtl-checkpoints
CLOUDFLARE_R2_ACCOUNT_ID=...
CLOUDFLARE_R2_ENDPOINT=https://a5000aacae3e74e21534569c0bf2909b.r2.cloudflarestorage.com
```

---

## Cluster Rules (from Anthony Mensah, CS153 TA)

1. Don't touch infra, other pods, Slurm config, or RBAC. Ping Anthony if broken.
2. Always read AI-generated commands before running — CLAUDE.md has cluster context.
3. Replace all placeholder values before running anything.
4. Stay at GPU tier — `--gres=gpu:1` only.
5. `scancel <jobid>` any stalled or idle jobs. Don't sit on GPUs you're not using.

---

## What's Next

The immediate next task is writing the fine-tuning script to run on the H100. It needs to:
1. Download Qwen2.5-Coder-32B-Instruct from HuggingFace
2. Download and filter CraftRTL dataset (syntax validation with iverilog)
3. QLoRA fine-tune on spec-to-RTL examples only
4. Save LoRA adapter to Cloudflare R2 before instance shutdown

After that, swap the Generator in `agentic_claude_factory.py` to point at the fine-tuned Qwen served via DigitalOcean, and run the full benchmark.
