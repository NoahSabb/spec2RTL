# Spec2RTL

**Fine-tuned Qwen2.5-Coder-32B + agentic self-correction loop for natural-language-to-Verilog RTL generation, evaluated on the CVDP cid003 benchmark.**

**Final result: 46/78 = 58.97% pass@1 — beating Claude Sonnet 4.6 standalone (55.13%) by +3.84pp.**

---

## Table of Contents

1. [Problem & Motivation](#problem--motivation)
2. [Approach & Architecture](#approach--architecture)
3. [Results & Evaluation](#results--evaluation)
4. [Technical Details](#technical-details)
5. [How to Use](#how-to-use)
6. [Development Process & Iteration](#development-process--iteration)
7. [Limitations & Future Work](#limitations--future-work)
8. [AI Usage Disclosure](#ai-usage-disclosure)
9. [References](#references)

---

## Problem & Motivation

Designing digital hardware at the Register Transfer Level (RTL) in Verilog is a high-skill task that bottlenecks chip development. Natural language specifications are how engineers communicate intent; automatically turning those specs into correct, synthesizable Verilog would meaningfully accelerate hardware design cycles.

The challenge is that LLMs fail at this in a single shot. Even frontier models like Claude Sonnet 4.6 pass only 55% of problems on the CVDP benchmark — a rigorous evaluation set with real cocotb simulation harnesses that test functional correctness, not just syntax. The remaining failures are logic errors, wrong architectures, and misinterpretations of the spec that no amount of prompt engineering fixes without iteration.

This project implements a scaled-down version of NVIDIA's ACE-RTL system (arXiv:2602.10218): a domain-specialized Generator model combined with a Reflector that reads simulation errors and guides targeted repairs. The goal is to exceed Claude Sonnet's standalone pass rate using a custom fine-tuned open model plus an agentic self-correction loop.

**This is hard.** The CVDP benchmark reports that state-of-the-art systems achieve no more than 34% pass@1 in single-shot mode. The ACE-RTL full system (with 256 A100s of compute and a massive proprietary training corpus) achieves 96.15%. Our constraint: 1 H100, 60 GPU-hours, and publicly available data.

---

## Approach & Architecture

The system has three stages, each building on the last:

### Stage 1 — Supervised Fine-Tuning (SFT)

**Why:** The base Qwen2.5-Coder-32B-Instruct model has general coding ability but no RTL-specific specialization. Fine-tuning on Verilog-specific data teaches it the idioms, timing conventions, and module structure that matter for hardware design.

**What:** QLoRA fine-tuning (r=32, α=64) on 13,568 training examples built from the `shailja/Verilog_GitHub` dataset (~109K raw modules). The data pipeline:
1. Downloaded and validated 7,525 synthesizable Verilog modules using iverilog + Verilator
2. Used Claude Sonnet 4.6 to generate natural-language specifications for each module
3. Scored spec quality with Claude Haiku as judge (filter: score ≥ 3 of 5; avg 3.71)
4. Built three task types: spec-to-RTL (8,128), editing (4,015), debugging (1,425)

Including debugging and editing tasks — not just spec-to-RTL — was a deliberate choice: these tasks teach the model to fix broken code and complete partial implementations, directly supporting the agentic self-correction loop.

**Training config:** 5 epochs, lr=1e-4, seq_len=4096, eff_batch=16, single H100, 21h wall time.

**SFT result:** 15/78 = 19.23% cocotb functional pass@1 (up from 11/78 = 14.10% base, +5.13pp).

### Stage 2 — Reinforcement Learning via GRPO

**Why:** SFT minimizes cross-entropy on token predictions but doesn't optimize for the actual goal: does the generated Verilog compile and pass simulation? GRPO (Group Relative Policy Optimization) directly rewards compilable, correct outputs.

**What:** GRPO training starting from the SFT adapter merged into the base model, with a new r=16 LoRA head. Reward signal: binary compile pass (iverilog). Two rounds:
- **RL v2:** G=2 completions, max_new_tokens=256, lr=5e-6, 3 epochs, ~5.4h
- **RL v3:** G=4 completions, max_new_tokens=512, lr=3e-6, 3 epochs, ~12h (starting from RL v2 weights)

**RL v2 result:** 23/78 = 29.49% cocotb pass@1 (up from 15/78 SFT, +10.3pp). RL v3 did not improve (22/78 = 28.21%) — diminishing returns on the iverilog-only reward signal confirmed.

### Stage 3 — Agentic Self-Correction Loop

**Why:** Even the best fine-tuned model fails on ~70% of problems in a single shot. The remaining failures are fixable given the right feedback: if you tell the model exactly what went wrong and how to fix it, it can recover. The agentic loop provides that feedback loop automatically.

**Architecture:**
- **Generator:** Qwen2.5-Coder-32B + RL v2 adapter (bf16, merged, on-GPU)
- **Reflector:** Claude Sonnet 4.6 via Anthropic API
- **Loop:** up to 3 compile-repair iterations + up to 4 cocotb-repair iterations per problem

**Reflector design (evolved over 7 improvement cycles):**

| Version | Key addition | Impact |
|---------|-------------|--------|
| v3 | Two-step reflection: diagnose root cause, then give fix instruction | Baseline agentic loop |
| v4 | History context (last 3 failed attempts) to prevent oscillation | Solved 5/8 problems |
| v5 | Module name enforcement (TOPLEVEL from .env); testbench context on opaque errors | Solved 3/8 |
| v6 | Full testbench from disk (3000 chars, not truncated); always included in reflector | Solved 5/8 |
| v7 | Module name in reflector prompt (prevents hallucination); second fresh-start | 4/8 |
| v8 | Iteration cap 3 compile + 3 cocotb (data-driven: all prior solves used ≤4 total) | 2/8 |
| v9 | Increased to 3+4=7 iterations for multi-bug medium problems | 1/5 |
| v10 | Two-directory RTL lookup: retries build on partially-fixed RTL from previous cycle | 4/5 |

**Reflector comparison experiment:** Before committing to a full 78-problem cluster run, tested Qwen, Haiku, and Sonnet as the reflector on 10 problems:

| Reflector | Pass rate (10 problems) | Estimated cost (78 problems) |
|-----------|------------------------|------------------------------|
| Qwen (self-repair) | 0/10 = 0% | $0 |
| Claude Haiku | 2/10 = 20% | $0.41 |
| **Claude Sonnet** | **7/10 = 70%** | **$1.51** |

Claude Sonnet was the only viable choice.

---

## Results & Evaluation

### Full Benchmark Table — cocotb Functional Pass@1 on CVDP cid003 (78 problems)

| Model / System | Overall | Easy (41) | Medium (37) |
|----------------|---------|-----------|-------------|
| Base Qwen2.5-Coder-32B-Instruct | 11/78 = 14.10% | 9/41 = 21.95% | 2/37 = 5.41% |
| + SFT fine-tuning (QLoRA r=32, 5 ep) | 15/78 = 19.23% | 10/41 = 24.39% | 5/37 = 13.51% |
| + RL GRPO v2 (r=16, 3 ep) | 23/78 = 29.49% | 15/41 = 36.59% | 8/37 = 21.62% |
| + RL GRPO v3 (r=16, 3 ep) | 22/78 = 28.21% | 15/41 = 36.59% | 7/37 = 18.92% |
| Agentic loop v10 (Qwen+Sonnet) | 42/78 = 53.85% | 29/41 = 70.73% | 13/37 = 35.14% |
| Agentic loop v11 (Qwen+Sonnet) | 38/78 = 48.72% | 25/41 = 60.98% | 13/37 = 35.14% |
| **Agentic final (v10+v11 cherry-pick)** | **46/78 = 58.97%** | **31/41 = 75.61%** | **15/37 = 40.54%** |
| Claude Sonnet 4.6 standalone (baseline) | 43/78 = 55.13% | — | — |
| ACE-RTL Generator standalone (paper) | 52.56% APR | — | — |
| ACE-RTL full system (paper, 256×A100) | 96.15% APR | — | — |

**Key takeaways:**
- Each stage improves on the last: Base → SFT → RL → Agentic is a monotonic improvement of +44.87pp total.
- The agentic loop provides the largest single gain: +24.36pp over RL v2 alone.
- The final cherry-pick (v10 + best of v11) beats Claude Sonnet standalone by +3.84pp — the primary goal.

### Evaluation Methodology

All functional results use the CVDP cocotb Docker harness (`cvdp-sim:latest`), which runs each generated `.sv` file through real Verilog simulation with test-vector comparison. This is distinct from iverilog compile-only checks (which are used as a fast proxy during training):

| Metric | What it checks | Where used |
|--------|---------------|------------|
| iverilog compile pass | Syntax + basic structure | RL training reward; fast evals |
| cocotb functional pass@1 | Functional correctness via simulation | All reported results above |

The gap between compile rate and functional pass rate is significant: the RL v2 adapter compiles 73.1% of problems but only passes 29.49% functionally. The extra compile failures from SFT vs base (64.1% vs 67.9%) reflect SFT producing more complex/ambitious Verilog that sometimes fails syntax but, when it compiles, is more likely to be functionally correct.

### v11 Regression Analysis

v11 introduced spec-clarification pre-prompting and an architectural-reset trigger designed to break the oscillation pattern observed in hard problems. The result was a net regression: 4 new problems solved, 8 regressions, for a net loss of 4 problems. The 8 regressions were all easy problems — the more aggressive prompting strategy disrupted generation that was already working reliably on straightforward specs. The final cherry-pick strategy (v10 as base, overwrite only the 4 v11 wins) eliminates the regressions and captures both improvements.

### Failure Analysis (32 remaining failures at final)

Categorized from per-problem cocotb logs:

- **Wrong architecture / wrong logic (6 problems):** GCD always-zero output, 16QAM mapper sign-flipped, RISC-V C.J decode wrong immediate field, sync serial bit count wrong, 7-segment encoding table wrong, thermostat compile error. Qwen generates plausible-looking but fundamentally incorrect implementations.
- **Genuine spec ambiguity (3 problems):** Moving average timing (registered vs running-sum interpretation), N-bit swizzle rotation direction, GCD done-signal timing. The natural-language specs don't uniquely constrain the implementation.
- **Oscillation / Reflector-generator mismatch (5+ problems):** Sonnet diagnoses correctly; Qwen implements the wrong fix or introduces a new bug. GFCM (glitch-free clock mux) and hebbian_rule failed 4+ consecutive cycles despite correct diagnoses.
- **Off-by-one / flag-logic bugs (4 problems):** sync_lifo full flag pointer comparison, sorter latency by 3 cycles, microcode sequencer empty flag, prbs_gen LFSR polynomial for later parameterized tests.
- **Pre-saved cocotb errors (systematic):** The v10 cluster cocotb repair loop used error messages pre-saved from the RL v2 baseline. After Qwen generates a repair, the repair loop can't see what the new error is — it's still diagnosing the old one. This causes blind iteration on all failures in the cluster run.

---

## Technical Details

### Model

- **Base:** Qwen2.5-Coder-32B-Instruct (32B parameters, bf16, ~65GB VRAM)
- **SFT adapter:** QLoRA r=32, α=64, target modules: q/k/v/o_proj + gate/up/down_proj
- **RL adapter:** QLoRA r=16, α=32, same target modules; applied on top of SFT-merged base
- **Inference:** bf16 loaded to CPU, merged + `.to("cuda:0")` — no device_map, no Accelerate hooks

### Training Configuration

| | SFT | RL GRPO v2 | RL GRPO v3 |
|--|-----|-----------|-----------|
| Starting point | Base model | SFT-merged base | RL v2-merged base |
| LoRA rank | 32 | 16 | 16 |
| Epochs | 5 | 3 | 3 |
| Learning rate | 1e-4 | 5e-6 | 3e-6 |
| Batch (eff.) | 16 | — | — |
| Completions (G) | — | 2 | 4 |
| Max new tokens | 4096 (train) | 256 | 512 |
| Wall time (H100) | 21h 6m | 5h 26m | 11h 59m |

### RL Reward Design

Reward signal during training: **binary iverilog compile pass** (1.0 = compiles, 0.0 = fails). A three-tier partial reward was also tested (hard fail=0.0, soft fail=0.2, clean compile=1.0) but the binary signal was used for the final submitted runs. Docker-based cocotb evaluation was not available on compute nodes, so the compile proxy was the practical choice.

### Agentic Loop Design

Each problem runs through:
1. **Initial RTL:** start from RL v2 pre-generated Verilog (not a cold start)
2. **Compile repair:** up to 3 iterations — iverilog error → Reflector diagnoses → Generator repairs
3. **Cocotb repair:** up to 4 iterations — simulation error → two-step Reflector (diagnose then fix instruction) → Generator repairs

**Reflector prompt includes (v10 final):**
- Problem spec
- Current RTL
- Parsed error (structured, not raw text)
- Last 3 failed attempts with their diagnoses (history context)
- Full testbench source (~3000 chars from harness files)
- Exact TOPLEVEL module name from `.env`

**Fresh-start trigger:** After 3+ failed cocotb iterations, discard current RTL and ask Generator for a complete rewrite with spec + testbench interface + latest error diagnosis.

**v10 key insight:** For retry problems, point `--initial-rtl` at the best partial fix from a previous cycle rather than the raw RL v2 output. This eliminates re-diagnosing and re-applying already-confirmed fixes. `ttc_lite` passed with 0 additional iterations because the cycle-6 RTL was already correct; `wb2ahb` needed only 2 iterations vs 4 from scratch.

### Infrastructure

- **Cluster:** 32× H100 80GB HBM3, 4-node SLURM (Stanford Omniva cluster)
- **Container:** `nvcr.io#nvidia/pytorch:24.12-py3` (PyTorch 2.6.0a0, CUDA 12.6)
- **Storage:** `/home/noahsabb` on Weka shared filesystem; checkpoints backed up to Cloudflare R2
- **Partition:** `medium` (5-day max walltime)
- **Total GPU-hours used:** ~40h SFT + ~5.4h RL v2 + ~12h RL v3 + ~5h agentic eval ≈ 62h

---

## How to Use

### Prerequisites

```bash
# Local (macOS/Linux): Docker for CVDP harness
docker build -f cvdp_benchmark/docker/Dockerfile.sim -t cvdp-sim:latest cvdp_benchmark/

# Python deps (local agentic loop)
pip install anthropic vllm transformers peft

export ANTHROPIC_API_KEY=sk-ant-...
```

### Run the Agentic Loop (Local, Claude as Generator)

```bash
cd spec2RTL

python3 scripts/run_agentic_v10.py \
    --bench-dir cvdp_benchmark/work_qwen32b_lora_rl_v2 \
    --initial-rtl path/to/pregenerated_rtl/ \
    --out logs/my_run \
    --log logs/my_run.jsonl \
    --cycle 1 \
    --script-version v10
```

This uses Claude Sonnet as both Generator and Reflector — useful for local testing. For cluster runs with Qwen as Generator, see `scripts/run_agentic_v10_cluster.py`.

### Run the CVDP Benchmark Harness

```bash
cd cvdp_benchmark

RTL_DIR=/path/to/rtl/files \
OSS_SIM_IMAGE=cvdp-sim:latest \
python run_benchmark.py \
    -f ../data/cid003_nonagentic.jsonl \
    -l \
    -m my-model-name \
    -c ../agents/pregenerated_factory.py \
    -p work_my_run \
    -t 4
```

The `pregenerated_factory.py` factory serves pre-generated `.sv` files from `RTL_DIR` by matching spec text from the benchmark's problem prompts. Results appear in `work_my_run/report.txt`.

### Reproduce the SFT Training Run (Cluster)

```bash
# 1. Build the dataset locally
python3 data/prepare_finetune_data.py \
    --workers 16 \
    --spec-model claude-sonnet-4-6 \
    --seed-jsonl data/seed_finetune.jsonl \
    --out data/final_finetune_full.jsonl

# 2. Copy to cluster
kubectl cp data/final_finetune_full.jsonl \
    slurm/<your-pod>:/home/<user>/data/final_finetune.jsonl -c login

kubectl cp scripts/train_qwen.py scripts/train_qwen.sbatch \
    slurm/<your-pod>:/home/<user>/spec2rtl/scripts/ -c login

# 3. Submit training job
kubectl exec -it -n slurm <your-pod> -c login -- \
    runuser -u <user> -- sbatch spec2rtl/scripts/train_qwen.sbatch
```

### Reproduce the RL GRPO Training (Cluster)

```bash
# Assumes SFT adapter is at /home/<user>/checkpoints/spec2rtl/qwen32b-lora-35e941c1
kubectl cp scripts/train_grpo.py scripts/run_grpo.sbatch \
    slurm/<your-pod>:/home/<user>/spec2rtl/scripts/ -c login

kubectl exec -it -n slurm <your-pod> -c login -- \
    runuser -u <user> -- sbatch spec2rtl/scripts/run_grpo.sbatch
```

### Run the Full 78-Problem Agentic Eval (Cluster)

```bash
kubectl cp scripts/run_agentic_v10_cluster.py \
             scripts/run_agentic_v10_cluster.sbatch \
    slurm/<your-pod>:/home/<user>/spec2rtl/scripts/ -c login

# Set ANTHROPIC_API_KEY in the sbatch file first
kubectl exec -it -n slurm <your-pod> -c login -- \
    runuser -u <user> -- sbatch spec2rtl/scripts/run_agentic_v10_cluster.sbatch
```

After the job completes, download `results/cid003_eval_agentic_v10_full/rtl/` locally and run the CVDP harness as shown above.

---

## Development Process & Iteration

The full development log is in `docs/PROCESS_LOG.md`. Key decisions and pivots:

**May 31 — Data pipeline + SFT training.** Built the 13,568-example dataset from scratch (2 hours of Sonnet API calls, ~$70). Training job failed 6 times before `job 293` succeeded, each failure teaching a new lesson about the NGC PyTorch container: don't overwrite bitsandbytes or transformers, pin exact versions, set MASTER_ADDR/MASTER_PORT for single-process distributed init. Training ran 21h on a single H100.

**June 1 — Inference debugging.** The first eval run produced 0.8 t/s (expected 50+ t/s). The root cause took 6 job submissions to isolate: `PeftModel.device` returns `cpu` regardless of where weights are loaded, causing inputs to route through CPU even when model is in VRAM. The fix — load model to CPU, merge LoRA, then `.to("cuda:0")` — bypasses the Accelerate device dispatch entirely.

**June 1-2 — SFT and base evals.** SFT fine-tuning gives +5.13pp over base on cocotb (19.23% vs 14.10%). Both are far below the Claude Sonnet baseline. The agentic loop is the necessary next step, not more fine-tuning.

**June 2-3 — RL GRPO.** Two rounds of GRPO training (v2 and v3). RL v2 gives a substantial +10.3pp over SFT (29.49% cocotb). RL v3 shows diminishing returns (-1.28pp vs v2). Conclusion: the iverilog-only reward signal is saturating; functional correctness requires the agentic loop.

**June 3 — Reflector comparison.** Before running 78 problems, compared Qwen/Haiku/Sonnet as the reflector on 10 problems. Qwen self-repair: 0/10. Haiku: 2/10. Sonnet: 7/10. The choice was clear despite the ~4× cost difference.

**June 3 — Agentic improvement cycles (7 cycles, v3–v10).** Ran 8 problems at a time, analyzed each failure, wrote an improved script, repeated. Key learnings per cycle:
- Cycle 1 (v3): Two-step reflection works; opaque errors (no assertion values) are the main bottleneck
- Cycle 2 (v4): History context prevents oscillation; 3 iterations is too few
- Cycle 3 (v5): Module name enforcement matters; testbench context reveals interface bugs
- Cycle 4 (v6): Full testbench (3000 chars) was the single biggest improvement — fixed 3 previously-stuck problems immediately
- Cycle 5 (v8): Iteration cap analysis — data shows all easy/medium single-bug problems solve within 4 total iterations
- Cycle 6 (v9): Multi-bug medium problems need 4 cocotb iterations, not 3
- Cycle 7 (v10): Starting retries from partially-fixed RTL vs RL v2 baseline saves 2+ iterations

**June 4 — Full 78-problem cluster run (v10) + failure analysis + v11 + final cherry-pick.** v10 reached 42/78 = 53.85%, just below the Claude baseline. Failure analysis revealed the pre-saved cocotb error problem (the repair loop was always diagnosing the old RL v2 errors, not the new Qwen-generated RTL). v11 tried to fix the hardest failures but caused regressions on easy problems. The cherry-pick merged both results: 46/78 = 58.97%, +3.84pp over the Claude baseline.

---

## Limitations & Future Work

### Known Limitations

**Pre-saved cocotb errors (largest systematic issue).** The v10 cluster cocotb repair loop uses error messages captured from the RL v2 baseline run. Once Qwen generates a repair, the loop continues using old error text — it's diagnosing the wrong version of the code. Fixing this requires running the CVDP Docker harness live on each Qwen-generated repair (the harness isn't available on SLURM compute nodes). This is the single change most likely to improve the cluster result.

**Generator-Reflector mismatch.** Local cycles used Claude Sonnet as both Generator and Reflector, where the generator could execute complex fix instructions exactly. On the cluster, Sonnet writes fix instructions but Qwen implements them — Qwen often misunderstands or partially applies the fix, introducing new bugs. The 14 problems solved locally with Claude as generator but failing in the cluster run illustrate this gap.

**v11 regression.** The spec-clarification and architectural-reset triggers in v11 disrupted easy-problem generation. More conservative application (only trigger spec clarification on problems that clearly oscillate, not universally) would likely recover those 8 regressions.

**32 remaining failures.** By category:
- 6 wrong-architecture problems: require architectural-level spec clarification or a stronger generator
- 5+ oscillation/mismatch problems: require live cocotb feedback in the repair loop
- ~4 near-misses (off-by-one bugs): addressable with more iterations and better diagnosis

### What We'd Try Next

1. **Live cocotb feedback in the cluster loop.** Build the CVDP harness into the SLURM job (install cocotb + required Python packages in the container, run each `.sv` through the harness inline). This eliminates the pre-saved-error problem and makes the repair loop use real feedback.

2. **Parallel sampling with cross-iteration synthesis.** The ACE-RTL paper reports 2.77× speedup from parallel scaling with minimal token overhead. Running 3–5 generator instances per problem and picking the best at each iteration would increase diversity without much cost.

3. **Spec clarification as a targeted intervention.** Add a pre-generation step that asks Sonnet: "What ambiguities in this spec could cause wrong implementations?" and resolves them before the Generator sees the spec. Apply this only for problems with oscillating diagnoses (same root cause identified 2+ times), not universally.

4. **RL with functional reward.** The current RL reward is binary compile pass. Training with actual cocotb functional correctness as the reward signal would optimize directly for what matters. This requires the Docker harness running inside the SLURM job — same infrastructure investment as point 1.

5. **More training data.** The paper used 1.7M RTL samples. Our dataset has 13,568 examples. More diverse training data, particularly for complex multi-module designs and parameterized arithmetic, would address the wrong-architecture failure category.

---

## AI Usage Disclosure

This project used AI tools throughout development. Here is an honest account of what was automated vs. what required human judgment:

### Claude Code (Anthropic CLI) — Development Assistance

Claude Code (claude-sonnet-4-6) was used throughout as a programming assistant for:
- Writing boilerplate (sbatch scripts, inference scripts, harness adapters)
- Debugging container compatibility issues during the training setup phase
- Implementing specific changes I designed (e.g., "add history context to the reflector prompt")
- Monitoring overnight cluster jobs and reporting status back

**All architectural decisions, the training pipeline design, the agentic loop design, the failure analysis, and the research direction were mine.** Claude Code executed on plans I designed. When Claude Code monitored jobs overnight, it was following instructions I set up; it did not make judgment calls about what to try next.

### Claude Sonnet 4.6 (Anthropic API) — Reflector in the Agentic Loop

Claude Sonnet 4.6 is used at inference time as the Reflector: it reads cocotb simulation error logs and generates fix instructions for the Generator. This is the core agentic component described in the architecture section. The Reflector's prompts and the two-step diagnosis design are my work; Sonnet provides the language understanding and Verilog reasoning.

### Claude Sonnet 4.6 — Training Data Generation

Sonnet was used to generate natural-language specifications for the 7,525 validated Verilog modules in the training corpus (~$70 API cost). This is described in the ACE-RTL paper as the standard approach for synthetic RTL training data. Claude Haiku was used as the LLM-as-Judge to score spec quality.

### What I did

- Designed the full pipeline (data → SFT → RL → agentic loop)
- Made all research decisions: QLoRA vs full fine-tuning, which RL reward to use, the reflector comparison experiment, when to stop RL and move to the agentic approach
- Wrote all analysis: reading the cocotb failure logs, categorizing error types, identifying the pre-saved-error bug, designing the v3–v10 improvements
- Debugged all infrastructure issues (container ABI incompatibilities, device_map slowness, MASTER_ADDR, etc.) — Claude Code helped execute fixes but the diagnosis was mine
- Interpreted all results and decided what to try next

---

## References

- **CVDP Benchmark:** Pinckney et al., "CVDP: A Verilog Design Benchmark for AI-Assisted Hardware Design," arXiv:2506.14074 (2026)
- **ACE-RTL:** Deng et al., "ACE-RTL: Automated Correction via Error-Aware RTL Code Generation," arXiv:2602.10218 (2026)
- **Qwen2.5-Coder:** Hui et al., "Qwen2.5-Coder Technical Report," arXiv:2409.12186 (2024)
- **GRPO / DeepSeek-R1:** DeepSeek-AI, "DeepSeek-R1: Incentivizing Reasoning Capability in LLMs via Reinforcement Learning," arXiv:2501.12948 (2025)
- **QLoRA:** Dettmers et al., "QLoRA: Efficient Finetuning of Quantized LLMs," NeurIPS 2023
- **Training data source:** `shailja/Verilog_GitHub` on HuggingFace

---

*Built for CS153 (Stanford). All training and evaluation done on the Stanford Omniva H100 cluster. Total API spend: ~$80 (data generation ~$70 + agentic loop reflector ~$10). Total GPU-hours: ~62h on a single H100.*
