# Spec2RTL — Process Log

This document is the authoritative running record of everything done in this project, maintained so that the full arc of decisions, experiments, results, and failures can be reconstructed for a paper. Every significant action is logged with date, rationale, and outcome.

---

## Project Overview

**Goal:** Replicate and adapt NVIDIA's ACE-RTL system (arXiv:2602.10218) at academic scale on the CVDP benchmark (arXiv:2506.14074), specifically the cid003 category (RTL Natural Language Spec-to-Code, 78 problems). Beat a single-shot Claude baseline using a fine-tuned Qwen Generator + agentic loop.

**Course:** CS153, Stanford University

**Compute budget:**
- 1× H100 80GB × 60 GPU-hours (QLoRA fine-tuning)
- $20 OpenRouter credits (Claude as Reflector/Coordinator during eval)
- $250 DigitalOcean credits (serving fine-tuned model)
- Cloudflare R2 bucket `spec2rtl-checkpoints` (LoRA checkpoint storage)

---

## Research Context

### CVDP Benchmark (arXiv:2506.14074)
- 783 human-authored Verilog problems across 13 categories
- State-of-the-art single-shot models achieve no more than 34% pass@1
- We evaluate on **cid003 only**: RTL Natural Language Spec-to-Code, 78 problems
- Metric: pass@1 with n=5 samples (Agentic Pass Rate = APR)
- Tools: Icarus Verilog simulation, Yosys synthesis, Verilator linting
- All evaluation runs inside Docker containers via cocotb test harnesses

### ACE-RTL (arXiv:2602.10218) — Our Target Architecture
Published March 2026 by NVIDIA (Deng, Yu, Liu, Pinckney, Khailany, Ren).

**Architecture:** Three components in an iterative loop:
1. **Generator** — RTL-specialized LLM (Qwen2.5-Coder-32B-Instruct fine-tuned on 1.7M samples). Trained on spec-to-RTL, editing, and debugging tasks — deliberately not just spec-to-RTL, because the agentic loop feeds the Generator editing/debugging-style prompts on iterations 2+.
2. **Reflector** — Frontier LLM (Claude Sonnet in paper). Reads simulation error logs, parses expected-vs-actual signal behavior, produces structured fix guidance.
3. **Coordinator** — Frontier LLM (Claude Sonnet in paper). Maintains self-evolving context across iterations (identified errors, suggested fixes, outcomes). Decides CONTINUE or RESTART when same failure persists.

**Key results on cid003 (spec-to-RTL):**
- Claude Sonnet standalone: 51.28% APR
- ACE-RTL Generator standalone: 49.74% Pass@1
- ACE-RTL full system: **96.15% APR** ← our target
- Parallel scaling (5 processes): 2.77× speedup, only 1.12× more tokens

**Training data pipeline:**
- Started from ~5M RTL scripts from public repos
- Filtered to 157K high-quality seeds (30–2,000 lines, deduped, syntax-validated)
- Expanded to 1.7M samples via LLM synthesis (GPT-OSS-120B + DeepSeek-R1) across three task types
- Quality gates: iverilog syntax validation + Jaccard decontamination (>0.8 threshold) + LLM-as-Judge scoring ≥3/5
- Data mix: spec-to-RTL, editing (spec + partial → complete), debugging (spec + buggy → fixed)
- Training: full SFT, 32 nodes × 8 A100s, 3 epochs, ~10K GPU-hours

**Ablation findings (from paper):**
- Coordinator with restart: largest single contributor to APR gain
- Coordinator without restart: still meaningful gain from history aggregation
- Generator specialization: adds ~15% over Claude-based ACE variant on code modification

### CraftRTL Dataset (arXiv:2409.12993)
By NVIDIA's Scale Lab. **110K total samples:**
- 80.1K SDG (Self-Instruct, OSS-Instruct, Docu-Instruct, non-textual representations)
- 28.5K correct-by-construction (K-maps/truth tables, FSMs, waveforms) — algorithmically generated, guaranteed correct
- 1.4K targeted code repair (debugging examples)

Quality filtering: syntax validation (Pyverilog), self-verification, benchmark decontamination, self-consistency checks for error reports.

StarCoder2-15B fine-tuned on CraftRTL: 81.9% pass@1 VerilogEval-Machine, 68.0% VerilogEval-Human.

**Note:** CraftRTL did NOT train RTLCoder. Common misconception. CraftRTL trained StarCoder2-15B with strong results.

### RTLCoder (arXiv:2312.08617)
- 27K samples, only syntax-checked with Pyverilog (no functional verification)
- No editing/debugging task coverage — only spec-to-RTL
- 7B parameter model
- Achieves 61.2% VerilogEval-Machine but **2.56% on CVDP cid003**
- Failure on CVDP explained by: (1) too small, (2) training data only syntax-validated, (3) VerilogEval-Machine/Human are much easier than CVDP

---

## Experiments and Results

### Baseline 1: claude-sonnet-4-6 Single-Shot
**Date:** Early project (before agentic loop)
**Method:** `agents/claude_factory.py` — single API call per problem, no iteration
**Command:**
```bash
caffeinate -i python run_benchmark.py \
  -f ../data/cid003_nonagentic.jsonl \
  -l -m claude-sonnet-4-6 \
  -c ../agents/claude_factory.py \
  -p work_claude_sonnet46_1sample \
  -t 4
```
**Results:**
| Metric | Score |
|--------|-------|
| Pass@1 | **55.13%** |
| Easy problems | 75.61% |
| Medium problems | 32.43% |
| Total problems | 78 |

**Significance:** This is our primary baseline. Notably, 55.13% already beats the ACE-RTL paper's reported Claude Sonnet standalone of 51.28% — likely because we're using claude-sonnet-4-6 vs the paper's Claude4-Sonnet (different model versions). Establishes the floor we need to beat with the agentic system.

---

### Baseline 2: RTLCoder-7B Single-Shot
**Date:** Early project
**Method:** `agents/ollama_factory.py` — Ollama-served RTLCoder-v1.1-GGUF Q4_K_M
**Results:**
| Metric | Score |
|--------|-------|
| Pass@1 | **2.56%** |
| Easy problems | 4.88% |
| Medium problems | 0.00% |
| Total problems | 78 |

**Analysis:** Catastrophic failure. Root causes: (1) 7B GGUF quantized model too small for complex RTL, (2) training data only syntax-checked with Pyverilog — functionally incorrect samples in training, (3) only trained on spec-to-RTL task, (4) VerilogEval benchmarks it was tuned for are far easier than CVDP. This result is NOT evidence against CraftRTL (RTLCoder does not use CraftRTL).

---

### Agentic Loop v1 — Architecture
**Date:** After baselines
**File:** `agents/agentic_loop_v1.py`
**Key design decisions and their rationale:**

**Decision: Use CVDP harness output (not Claude-generated testbench) as the iteration feedback signal.**
- *Why:* Early version used Claude to generate a testbench. Claude would pass its own testbench on iteration 1, loop never iterated, CVDP harness then caught failures the Claude testbench missed. The loop was essentially non-functional.
- *Fix:* Run the actual Docker/cocotb CVDP harness after each iteration. Real ground-truth feedback.

**Decision: Reflector uses claude-haiku-4-5, not Sonnet.**
- *Why:* Cost reduction. Haiku is ~20× cheaper than Sonnet. Reflector's job (parse error logs, produce structured guidance) doesn't require frontier reasoning.

**Decision: Coordinator uses claude-haiku-4-5, not Sonnet.**
- *Why:* Same cost argument. Simple context aggregation + CONTINUE/RESTART doesn't need Sonnet-level capability.

**Decision: Generator is claude-sonnet-4-6 (placeholder).**
- *Why:* Fine-tuned Qwen not yet trained. Sonnet stands in until the QLoRA checkpoint is ready.

**Verification stack (in order):**
1. Verilator lint (`verilator --lint-only -Wall -Wno-DECLFILENAME`) — fast structural check
2. Icarus Verilog simulation (`iverilog` + `vvp`) — compile and run
3. CVDP harness — Docker cocotb tests (final judge and loop feedback signal)

**Settings at launch:** `num_processes=1`, `max_iterations=5`

---

### Agentic Loop v1 — RESTART Mechanism Added
**Date:** 2026-05-30
**File:** `agents/agentic_loop_v1.py`
**Change:** Added CONTINUE/RESTART decision logic to the Coordinator.

**What changed:**
- `coordinate()` now accepts `sim_result` and records explicit outcome (`"FAILED"`) + error summary per iteration in context
- Coordinator prompt now asks for `## DECISION` (CONTINUE or RESTART), `## GUIDANCE`, and `## FORBIDDEN`
- **RESTART logic:** If decision is RESTART and `restart_count < max_restarts` (3), distill insights from failed context into a `restart_prompt = spec + lessons + forbidden`, call Generator fresh, clear context, continue
- **CONTINUE logic:** Unchanged — feed evolving context + forbidden list to Generator
- `run_single_process` now uses a `while` loop (instead of `for`) to handle restarts cleanly without consuming an iteration slot; tracks `restart_count`
- Return value now includes `restarts` field for logging

**Rationale from ACE-RTL paper:** The paper's case studies showed RESTART was the critical piece for breaking stuck loops. The clock jitter example required 2 restarts — each time the Coordinator distilled "validity flag needed before detection" from the failed runs and the Generator used a fundamentally different approach. Without RESTART, the loop just rephrases the same wrong fix.

**RESTART trigger condition:** "Same primary failure persists 2+ consecutive iterations without meaningful improvement OR error pattern shows a fundamentally wrong architectural approach that cannot be patched incrementally."

**Max restarts:** 3 per process (prevents infinite loops on truly unsolvable problems).

---

## Fine-Tuning Plan (In Progress)

### Motivation
Replace the Generator (currently claude-sonnet-4-6) with a fine-tuned Qwen2.5-Coder-32B-Instruct. Expected gains:
- Generator is specialized on RTL semantics (hardware-specific patterns, module interfaces, timing behavior)
- Generator is trained on editing/debugging tasks — mirrors the agentic loop's iteration 2+ input format
- ACE-RTL paper: Generator standalone scores ~49.74% Pass@1; full system 96.15% APR — specialization is necessary but not sufficient without the loop

### Data Strategy (Decided 2026-05-30)

**Base:** CraftRTL (110K samples, NVlabs, arXiv:2409.12993)
- Best publicly available RTL dataset
- Correct-by-construction FSM/K-map/waveform samples = guaranteed correct outputs
- Strong quality filtering (syntax + self-verification + decontamination)

**Gap in CraftRTL:** Only 1.4K debugging/repair samples. Agentic loop needs editing + debugging task coverage for iterations 2+. Need to generate more.

**Augmentation plan:**
- Take CraftRTL correct solutions → inject common bug patterns → create `(spec + buggy_code → fixed_code)` debugging pairs
- Bug patterns: wrong FSM transitions, off-by-one counters, timing/handshake violations, incorrect always-block sensitivity lists
- Create editing pairs: `(spec + partial_code → complete_code)`
- All outputs verified with `iverilog -g2012` (not Pyverilog — must actually compile)

**Target data mix:**
- ~60-70% spec-to-RTL (from CraftRTL SDG + CC)
- ~15-20% editing
- ~15-20% debugging
- **Total: 50-100K samples** (QLoRA on 32B, 60 GPU-hours — more data won't help beyond this)

**Quality gate:** Every output sample must pass `iverilog -g2012`. Discard anything that doesn't compile. This is the single most important filter — RTLCoder's failure is partly explained by training on syntactically-checked-only data.

### QLoRA Training Plan
- Base model: `Qwen2.5-Coder-32B-Instruct` (HuggingFace)
- Method: QLoRA (4-bit quantized base + LoRA adapters) — fits in 80GB H100
- Dataset: final_finetune.jsonl (50-100K samples, task_type field)
- Adapter size: ~100MB saved to Cloudflare R2 `spec2rtl-checkpoints`
- Inference: DigitalOcean Serverless Inference API after training

---

---

## Data Pipeline — Completed 2026-05-30

### Why CraftRTL (as originally planned) required a change
CraftRTL (arXiv:2409.12993) has no pre-built downloadable dataset. The NVlabs GitHub repo provides the generation pipeline, which requires NVIDIA NIM API access to run. Given our budget and timeline, we pivoted to a functionally equivalent approach using publicly available data.

### Chosen approach: OSS-Instruct from shailja/Verilog_GitHub
- **Source:** `shailja/Verilog_GitHub` — 109K raw Verilog modules from GitHub, publicly available on HuggingFace
- **Why equivalent to CraftRTL's approach:** CraftRTL's OSS-Instruct component does exactly this — takes open-source Verilog modules and uses LLM prompting to generate specifications from them. We replicate this using Claude Haiku.
- **Why better than RTLCoder's data:** iverilog validation (not just Pyverilog syntax checking), plus functional-level LLM-as-judge spec quality check is implicit in the generation prompt.

### File: `data/prepare_finetune_data.py`

Full pipeline in one script, with checkpointing (intermediate results saved to `data/cache/`):

**Stage 1 — iverilog validation:**
- Download `shailja/Verilog_GitHub`
- Pre-filter: 50–3000 chars, must contain `module` keyword
- Run `iverilog -g2012 -o /dev/null` on every module in parallel
- Expected pass rate: ~40-60% (GitHub code has many partial/broken files)
- Output: `data/cache/validated_modules.json`

**Stage 2 — Spec generation (OSS-Instruct):**
- Claude Haiku reads each valid Verilog module and writes the natural language spec that would precede it
- Prompt instructs: describe behavior/interfaces/timing, no implementation details
- 8 parallel workers, retry logic, checkpointed to `data/cache/spec_pairs.json`
- Estimated cost: ~$20-25 in Claude Haiku API calls for 50K modules

**Stage 3 — Debugging pairs (programmatic bug injection):**
Six bug patterns, applied by collecting ALL applicable injectors then picking uniformly at random (ensures diversity):
| Bug pattern | Trigger condition |
|---|---|
| `posedge_negedge` | Module has `posedge` clock edge |
| `off_by_one` | Expression contains `<` or `>` operator |
| `wrong_operator` | `assign` statement with `&` or `\|` |
| `missing_reset` | Multi-line `if (rst)` block |
| `wrong_state_transition` | Simple `next_state = STATE;` assignments |
| `always_sensitivity` | `always @(...)` with 2+ signals |
Format: `user = spec + buggy_code`, `assistant = fixed_code`

**Stage 4 — Editing pairs (section masking):**
Three masking strategies, first applicable one used:
- `_mask_always_body`: Replace always block body with `// TODO`
- `_mask_assign_statements`: Blank out half of continuous assign RHS
- `_mask_module_body`: Keep port declarations only, mask all logic
Format: `user = spec + partial_code`, `assistant = complete_code`

**Stage 5 — Mix and final quality gate:**
- Target: 65% spec-to-RTL / 17.5% debugging / 17.5% editing
- Max 100K total samples
- **Final iverilog pass on every assistant output** — discard any sample whose output Verilog doesn't compile
- Output: `data/final_finetune.jsonl` with `task_type` field

**Verification:** All pipeline logic smoke-tested locally (iverilog 13.0):
- iverilog_check: PASS (accepts valid, rejects malformed)
- Bug injection diversity: ~33% each for complex modules across 50 trials
- All pair builders produce correct format
- Quality filter: 100% pass rate on test samples (correct Verilog passes)

**To run the pipeline** (on cluster login pod, CPU-only, ~2-4 hours):
```bash
cd ~/spec2RTL
ANTHROPIC_API_KEY=... python data/prepare_finetune_data.py --workers 16 --out data/final_finetune.jsonl
# Resume after interruption:
python data/prepare_finetune_data.py --skip-download --workers 16 --out data/final_finetune.jsonl
```

---

## Next Steps

1. ~~RESTART mechanism~~ ✓ (2026-05-30)
2. ~~Data pipeline script written and verified~~ ✓ (2026-05-30)
3. Run `prepare_finetune_data.py` on cluster to generate `final_finetune.jsonl`
4. Write QLoRA fine-tuning script for H100
5. Run fine-tuning job on H100, save adapter to R2
6. Serve fine-tuned Qwen via DigitalOcean
7. Swap Generator in `agentic_claude_factory.py`
8. Run full CVDP cid003 benchmark (78 problems × 5 runs)
9. Compare results vs 55.13% baseline

---

## Open Questions / Risks

- **CraftRTL availability:** CraftRTL pipeline is on NVlabs GitHub but dataset may not be directly downloadable — may need to run the generation pipeline itself.
- **Debugging data quality:** Injecting bugs programmatically risks creating trivially easy or unrealistic bugs. Need to verify that generated debugging examples have meaningful variation.
- **H100 time budget:** 60 GPU-hours. QLoRA on 32B at ~1K samples/hour = ~50-100K samples is feasible in ~1-3 hours. Most time will go to model download + checkpoint saves.
- **iverilog vs Verilator:** iverilog is more permissive than Verilator. Passing iverilog doesn't guarantee synthesizable RTL. May want to add a Verilator lint pass as a second filter.
- **Agentic loop benchmark cost:** 78 problems × 5 runs × up to 30 iterations × Haiku for Reflector/Coordinator = ~$10-15 on OpenRouter at current Haiku pricing.
