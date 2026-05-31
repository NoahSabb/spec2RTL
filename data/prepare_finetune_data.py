#!/usr/bin/env python3
"""
Fine-tuning data preparation pipeline for spec2RTL.

Quality gates (in order):
  1. Size filter: 50-3000 chars, must contain 'module'
  2. iverilog -g2012 compilation check (syntax + basic semantics)
  3. Verilator --lint-only (stricter: width mismatches, implicit wires, undriven outputs)
  4. Jaccard decontamination against CVDP benchmark (discard if similarity > 0.8)
  5. Spec generation via Claude Haiku (OSS-Instruct style)
  6. LLM-as-Judge scoring (Claude Haiku, 1-5 scale, discard < 3) — mirrors ACE-RTL paper
  7. Task-specific pair generation (spec-to-RTL, debugging, editing)
  8. Final iverilog pass on ALL output Verilog — last line of defense

Strategy:
  - Source: shailja/Verilog_GitHub (~109K raw Verilog modules from GitHub)
  - Mix: ~65% spec-to-RTL / 17.5% debugging / 17.5% editing
  - Target: 50-100K final samples

Output format (Qwen2.5 chat template):
  {
    "messages": [{"role": "user", "content": "..."}, {"role": "assistant", "content": "..."}],
    "task_type": "spec_to_rtl" | "debugging" | "editing",
    "quality_score": 3-5  (LLM-as-Judge score, spec-to-rtl only)
  }

Run:
  python prepare_finetune_data.py [--limit N] [--workers W] [--out PATH]

Checkpointing: intermediate results saved to data/cache/ so the pipeline
can be resumed after interruption.
"""

import argparse
import json
import os
import random
import re
import subprocess
import tempfile
import time
import logging
from concurrent.futures import ThreadPoolExecutor, as_completed
from pathlib import Path

import anthropic
from datasets import load_dataset
from tqdm import tqdm

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
log = logging.getLogger(__name__)

CACHE_DIR = Path(__file__).parent / "cache"
CACHE_DIR.mkdir(exist_ok=True)

# ---------------------------------------------------------------------------
# Step 1 — iverilog validation
# ---------------------------------------------------------------------------

def iverilog_check(verilog: str) -> bool:
    """Return True if verilog compiles cleanly under iverilog -g2012."""
    with tempfile.NamedTemporaryFile(suffix=".v", mode="w", delete=False) as f:
        f.write(verilog)
        path = f.name
    try:
        result = subprocess.run(
            ["iverilog", "-g2012", "-o", "/dev/null", path],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0
    except Exception:
        return False
    finally:
        os.unlink(path)


def is_synthesizable_rtl(verilog: str) -> bool:
    """
    Return False if the module looks like a testbench, simulation utility,
    or non-synthesizable file. We want real hardware designs only.

    Heuristics (any match = reject):
    - Contains simulation system tasks ($write, $display, $finish, $stop, $monitor)
    - Contains 'initial begin' blocks (testbench setup, not synthesizable)
    - Contains Verilator/Icarus copyright headers common in test files
    - Contains 'timescale' + no real module body (header-only files)
    - Contains fork/join (simulation-only construct)
    - Cycle counter pattern: integer cyc (classic testbench idiom)
    """
    # Simulation system tasks — not in real RTL
    sim_tasks = ['$write', '$display', '$finish', '$stop', '$monitor',
                 '$dumpfile', '$dumpvars', '$readmem', '$strobe']
    for task in sim_tasks:
        if task in verilog:
            return False

    # initial begin blocks are not synthesizable
    if re.search(r'\binitial\s+begin\b', verilog):
        return False

    # fork/join — simulation only
    if re.search(r'\bfork\b', verilog):
        return False

    # Classic testbench cycle counter idiom
    if re.search(r'\binteger\s+cyc\b', verilog):
        return False

    # Verilator/open-source test file headers
    if 'placed into the Public Domain' in verilog:
        return False
    if 'DESCRIPTION: Verilator' in verilog:
        return False

    return True


def filter_valid_modules(raw_modules: list[str], workers: int = 8) -> list[str]:
    """Return only modules that pass iverilog -g2012."""
    log.info(f"iverilog-validating {len(raw_modules)} modules with {workers} workers...")
    valid = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(iverilog_check, m): m for m in raw_modules}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="iverilog validate"):
            if fut.result():
                valid.append(futures[fut])
    log.info(f"  {len(valid)}/{len(raw_modules)} passed iverilog ({100*len(valid)//len(raw_modules)}%)")
    return valid


# ---------------------------------------------------------------------------
# Quality gate 2 — Verilator lint (stricter than iverilog)
# ---------------------------------------------------------------------------

def verilator_check(verilog: str) -> bool:
    """
    Return True if verilog passes Verilator --lint-only with no errors.
    Catches issues iverilog misses: width mismatches, implicit wires, undriven outputs.
    Warnings are allowed; only errors cause rejection.
    Returns True (skip) if Verilator is not installed.
    """
    with tempfile.NamedTemporaryFile(suffix=".v", mode="w", delete=False) as f:
        f.write(verilog)
        path = f.name
    try:
        result = subprocess.run(
            ["verilator", "--lint-only", "-Wall", "-Wno-DECLFILENAME",
             "-Wno-UNUSED", "-Wno-UNDRIVEN", "--bbox-unsup", path],
            capture_output=True, text=True, timeout=15
        )
        # Verilator exits non-zero on errors (not warnings)
        return result.returncode == 0
    except FileNotFoundError:
        return True  # Verilator not installed — skip this gate
    except Exception:
        return False
    finally:
        os.unlink(path)


def filter_verilator(modules: list[str], workers: int = 8) -> list[str]:
    """Filter modules through Verilator lint."""
    log.info(f"Verilator-linting {len(modules)} modules...")
    valid = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(verilator_check, m): m for m in modules}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="verilator lint"):
            if fut.result():
                valid.append(futures[fut])
    pct = 100 * len(valid) // len(modules) if modules else 0
    log.info(f"  {len(valid)}/{len(modules)} passed Verilator ({pct}%)")
    return valid


# ---------------------------------------------------------------------------
# Quality gate 3 — Jaccard benchmark decontamination
# ---------------------------------------------------------------------------

def _tokenize(text: str) -> set[str]:
    """Split verilog into a bag of tokens for Jaccard comparison."""
    return set(re.findall(r'\w+', text.lower()))


def jaccard(a: str, b: str) -> float:
    ta, tb = _tokenize(a), _tokenize(b)
    if not ta or not tb:
        return 0.0
    return len(ta & tb) / len(ta | tb)


def load_benchmark_specs(benchmark_jsonl: str) -> list[str]:
    """
    Load the natural language specs from the CVDP benchmark (input.prompt field).
    These are used to decontaminate training data — we don't want training specs
    that are too similar to the test prompts the model will be evaluated on.
    """
    refs = []
    if not os.path.exists(benchmark_jsonl):
        log.warning(f"Benchmark file not found: {benchmark_jsonl} — skipping decontamination")
        return refs
    with open(benchmark_jsonl) as f:
        for line in f:
            row = json.loads(line)
            # CVDP format: input.prompt holds the natural language spec
            prompt = row.get("input", {}).get("prompt", "")
            if prompt:
                refs.append(prompt)
    log.info(f"  Loaded {len(refs)} benchmark specs for decontamination")
    return refs


def decontaminate_specs(spec_pairs: list[tuple[str, str]],
                        benchmark_specs: list[str],
                        threshold: float = 0.8) -> list[tuple[str, str]]:
    """
    Remove any (verilog, spec) pair whose generated spec has Jaccard similarity
    >= threshold with any CVDP benchmark spec. Run AFTER spec generation so we
    compare spec text against spec text (most meaningful comparison).
    Mirrors ACE-RTL paper's decontamination step.
    """
    if not benchmark_specs:
        log.info("  No benchmark specs loaded — skipping decontamination")
        return spec_pairs

    log.info(f"Decontaminating {len(spec_pairs)} spec pairs against "
             f"{len(benchmark_specs)} CVDP test specs (threshold={threshold})...")
    clean = []
    contaminated = 0
    for verilog, spec in tqdm(spec_pairs, desc="decontaminate"):
        max_sim = max(jaccard(spec, ref) for ref in benchmark_specs)
        if max_sim < threshold:
            clean.append((verilog, spec))
        else:
            contaminated += 1
    log.info(f"  Removed {contaminated} contaminated pairs, {len(clean)} remain")
    return clean


# ---------------------------------------------------------------------------
# Quality gate 4 — LLM-as-Judge spec-code alignment scoring
# Directly mirrors ACE-RTL paper: score 1-5, discard < 3
# ---------------------------------------------------------------------------

JUDGE_SYSTEM = (
    "You are an expert RTL hardware engineer evaluating the quality of a "
    "specification-code pair for machine learning training data. "
    "Score the semantic alignment between the specification and the Verilog implementation."
)

JUDGE_USER_TMPL = """Rate the alignment between this specification and Verilog implementation on a scale of 1 to 5.

## Specification
{spec}

## Verilog Implementation
```verilog
{verilog}
```

Scoring rubric:
1 = Spec is wrong or completely unrelated to the implementation
2 = Spec partially describes the implementation but has significant inaccuracies
3 = Spec adequately describes the implementation; a competent engineer could re-implement it
4 = Spec accurately and completely describes the implementation including edge cases
5 = Spec is exceptionally precise — unambiguous, complete, and directly implementable

Respond with ONLY a single integer (1, 2, 3, 4, or 5). No explanation."""


JUDGE_MODEL = "claude-haiku-4-5-20251001"  # keep Haiku for judge (binary pass/fail, Haiku is fine)


def score_pair(client: anthropic.Anthropic, verilog: str, spec: str,
               retries: int = 3) -> int | None:
    """Return LLM-as-Judge score (1-5) or None on failure."""
    for attempt in range(retries):
        try:
            resp = client.messages.create(
                model=JUDGE_MODEL,
                max_tokens=8,
                system=JUDGE_SYSTEM,
                messages=[{"role": "user", "content": JUDGE_USER_TMPL.format(
                    spec=spec, verilog=verilog)}],
            )
            text = resp.content[0].text.strip()
            score = int(re.search(r'[1-5]', text).group())
            return score
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                log.warning(f"Judge scoring failed: {e}")
                return None


def score_pairs_batch(client: anthropic.Anthropic,
                      pairs: list[tuple[str, str]],
                      workers: int = 8,
                      min_score: int = 3) -> list[tuple[str, str, int]]:
    """
    Score all (verilog, spec) pairs. Return (verilog, spec, score) for pairs
    scoring >= min_score. Matches ACE-RTL paper's quality gate exactly.
    """
    log.info(f"LLM-as-Judge scoring {len(pairs)} pairs (min_score={min_score})...")
    scored = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(score_pair, client, v, s): (v, s) for v, s in pairs}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="judge scoring"):
            v, s = futures[fut]
            score = fut.result()
            if score is not None and score >= min_score:
                scored.append((v, s, score))

    if pairs:
        pass_rate = 100 * len(scored) // len(pairs)
        log.info(f"  {len(scored)}/{len(pairs)} pairs passed LLM-as-Judge ({pass_rate}%)")
        if scored:
            avg = sum(t[2] for t in scored) / len(scored)
            log.info(f"  Average score of kept pairs: {avg:.2f}/5")
    return scored


# ---------------------------------------------------------------------------
# Step 2 — spec generation via Claude Haiku (OSS-Instruct style)
# ---------------------------------------------------------------------------

SPEC_SYSTEM = (
    "You are a senior RTL hardware engineer writing design specifications. "
    "Given a Verilog module implementation, write the natural language specification "
    "that a hardware engineer would write BEFORE implementing it. "
    "The spec must be precise enough that a competent engineer could re-implement the module from scratch. "
    "Do NOT reference internal signal names or implementation details. "
    "Describe behavior, interfaces, timing, and functional requirements only."
)

SPEC_USER_TMPL = """Here is a Verilog module implementation:

```verilog
{verilog}
```

Write the design specification for this module. Include:
1. Module purpose and high-level behavior
2. Port descriptions (name, direction, width, meaning)
3. Functional behavior (what it computes, state machine if applicable)
4. Timing requirements (clocked/combinational, reset behavior)
5. Edge cases and corner conditions

Write ONLY the specification text, no code."""


SPEC_GEN_MODEL = "claude-haiku-4-5-20251001"  # overridden by --spec-model


def generate_spec(client: anthropic.Anthropic, verilog: str, retries: int = 3) -> str | None:
    for attempt in range(retries):
        try:
            resp = client.messages.create(
                model=SPEC_GEN_MODEL,
                max_tokens=1024,
                system=SPEC_SYSTEM,
                messages=[{"role": "user", "content": SPEC_USER_TMPL.format(verilog=verilog)}],
            )
            return resp.content[0].text.strip()
        except Exception as e:
            if attempt < retries - 1:
                time.sleep(2 ** attempt)
            else:
                log.warning(f"Spec generation failed after {retries} attempts: {e}")
                return None


def generate_specs_batch(client: anthropic.Anthropic, modules: list[str],
                          workers: int = 8) -> list[tuple[str, str]]:
    """Returns list of (verilog, spec) pairs for successful generations."""
    pairs = []
    with ThreadPoolExecutor(max_workers=workers) as ex:
        futures = {ex.submit(generate_spec, client, m): m for m in modules}
        for fut in tqdm(as_completed(futures), total=len(futures), desc="generate specs"):
            spec = fut.result()
            if spec:
                pairs.append((futures[fut], spec))
    log.info(f"  Generated {len(pairs)}/{len(modules)} specs successfully")
    return pairs


# ---------------------------------------------------------------------------
# Step 3 — bug injection for debugging pairs
# ---------------------------------------------------------------------------

# Each injector takes a verilog string, returns modified verilog or None if pattern not found.
# We apply one random injector per module.

def _inject_posedge_negedge(v: str) -> str | None:
    """Flip posedge clk to negedge clk (timing bug)."""
    if "posedge" not in v:
        return None
    return v.replace("posedge", "negedge", 1)


def _inject_off_by_one(v: str) -> str | None:
    """Change one > to >= or < to <= (off-by-one in counter/comparator)."""
    # Match standalone comparison operators in expressions, avoid port declarations
    pattern = r'(?<![<>!])([<>])(?![=<>])'
    matches = list(re.finditer(pattern, v))
    if not matches:
        return None
    m = random.choice(matches)
    op = m.group(1)
    replacement = ">=" if op == ">" else "<="
    return v[:m.start()] + replacement + v[m.end():]


def _inject_wrong_operator(v: str) -> str | None:
    """Swap & and | in one combinational assignment (logic bug)."""
    # Only in assign statements or always blocks, avoid module declarations
    pattern = r'(assign\s+\w+\s*=\s*[^;]+)([&|])([^;]+;)'
    m = re.search(pattern, v)
    if not m:
        return None
    op = m.group(2)
    new_op = "|" if op == "&" else "&"
    return v[:m.start(2)] + new_op + v[m.end(2):]


def _inject_missing_reset(v: str) -> str | None:
    """Remove one synchronous reset branch (state corruption bug)."""
    # Match: if (rst) ... else ... or if (!rst_n) ...
    pattern = r'(if\s*\([^)]*rst[^)]*\)\s*begin)(.*?)(end\s*else)',
    m = re.search(r'if\s*\([^)]*rst[^)]*\)\s*\n(\s+[^\n]+\n)+', v, re.IGNORECASE)
    if not m:
        return None
    # Remove the entire reset block
    return v[:m.start()] + v[m.end():]


def _inject_wrong_state_transition(v: str) -> str | None:
    """Swap two state assignments in a case statement (FSM bug)."""
    # Find state transitions like: next_state = STATE_X;
    pattern = r'(next_state\s*(?:<=|=)\s*)(\w+)(\s*;)'
    matches = list(re.finditer(pattern, v))
    if len(matches) < 2:
        return None
    # Swap two random transitions
    i, j = random.sample(range(len(matches)), 2)
    m1, m2 = matches[i], matches[j]
    val1, val2 = m1.group(2), m2.group(2)
    if val1 == val2:
        return None
    result = list(v)
    # Replace j first (higher index) then i to preserve offsets
    for src, dst in sorted([(m1, val2), (m2, val1)], key=lambda x: x[0].start(), reverse=True):
        result[src.start(2):src.end(2)] = dst
    return "".join(result)


def _inject_always_sensitivity(v: str) -> str | None:
    """Remove one signal from a combinational always @(...) sensitivity list."""
    m = re.search(r'always\s*@\s*\(([^)]+)\)', v)
    if not m:
        return None
    signals = [s.strip() for s in m.group(1).split(",")]
    if len(signals) < 2 or signals == ["*"]:
        return None
    signals.pop(random.randrange(len(signals)))
    new_sens = ", ".join(signals)
    return v[:m.start(1)] + new_sens + v[m.end(1):]


BUG_INJECTORS = [
    _inject_posedge_negedge,
    _inject_off_by_one,
    _inject_wrong_operator,
    _inject_missing_reset,
    _inject_wrong_state_transition,
    _inject_always_sensitivity,
]


def inject_bug(verilog: str) -> tuple[str, str] | None:
    """
    Collect ALL injectors that produce a valid modification, then pick one
    uniformly at random. This ensures diversity across bug types rather than
    always picking the first matching injector.
    Returns (buggy_verilog, bug_description) or None if no injector matched.
    """
    candidates = []
    for injector in BUG_INJECTORS:
        result = injector(verilog)
        if result and result != verilog:
            candidates.append((result, injector.__name__.replace("_inject_", "").replace("_", " ")))
    if not candidates:
        return None
    return random.choice(candidates)


def make_debugging_pairs(spec_pairs: list[tuple[str, str]]) -> list[dict]:
    """
    For each (verilog, spec) pair, inject a bug to create a debugging training example.
    Format: user sees spec + buggy_code, assistant outputs fixed_code.
    """
    pairs = []
    for verilog, spec in tqdm(spec_pairs, desc="inject bugs"):
        result = inject_bug(verilog)
        if result is None:
            continue
        buggy, bug_type = result
        user_content = (
            f"The following Verilog implementation has a bug. Fix it.\n\n"
            f"## Specification\n{spec}\n\n"
            f"## Buggy Implementation\n```verilog\n{buggy}\n```"
        )
        assistant_content = f"```verilog\n{verilog}\n```"
        pairs.append({
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ],
            "task_type": "debugging",
            "bug_type": bug_type,
        })
    log.info(f"  Generated {len(pairs)} debugging pairs")
    return pairs


# ---------------------------------------------------------------------------
# Step 4 — editing pairs (partial implementation → complete)
# ---------------------------------------------------------------------------

def _mask_always_body(verilog: str) -> str | None:
    """Replace the body of one always block with a TODO comment."""
    # Match always block with begin...end
    pattern = r'(always\s*@[^;]+begin\s*\n)(.*?)(^\s*end\b)',
    m = re.search(r'(always\s*@[^;]+begin\s*\n)(.*?)(^\s*end)', verilog, re.DOTALL | re.MULTILINE)
    if not m or len(m.group(2).strip()) < 20:
        return None
    indent = "    "
    masked = m.group(1) + f"{indent}// TODO: implement this always block\n" + m.group(3)
    return verilog[:m.start()] + masked + verilog[m.end():]


def _mask_assign_statements(verilog: str) -> str | None:
    """Remove assign statement RHS values (continuous assignment editing)."""
    assigns = list(re.finditer(r'(assign\s+\w+\s*=\s*)([^;]+)(;)', verilog))
    if len(assigns) < 2:
        return None
    # Mask half of them
    to_mask = random.sample(assigns, max(1, len(assigns) // 2))
    result = verilog
    for m in sorted(to_mask, key=lambda x: x.start(), reverse=True):
        result = result[:m.start(2)] + "/* TODO */" + result[m.end(2):]
    return result


def _mask_module_body(verilog: str) -> str | None:
    """Keep only port declarations, mask all internal logic with TODO."""
    # Find module...endmodule
    m = re.search(r'(module\s+\w+[^;]+;)(.*?)(endmodule)', verilog, re.DOTALL)
    if not m or len(m.group(2).strip()) < 50:
        return None
    masked = m.group(1) + "\n\n// TODO: implement module logic\n\n" + m.group(3)
    return verilog[:m.start()] + masked + verilog[m.end():]


EDIT_MASKERS = [_mask_always_body, _mask_assign_statements, _mask_module_body]


def make_editing_pairs(spec_pairs: list[tuple[str, str]]) -> list[dict]:
    """
    For each (verilog, spec) pair, mask part of the implementation to create
    an editing training example.
    Format: user sees spec + partial_code, assistant outputs complete_code.
    """
    pairs = []
    for verilog, spec in tqdm(spec_pairs, desc="make editing pairs"):
        maskers = EDIT_MASKERS[:]
        random.shuffle(maskers)
        partial = None
        for masker in maskers:
            partial = masker(verilog)
            if partial and partial != verilog:
                break
        if partial is None:
            continue
        user_content = (
            f"Complete the following partial Verilog implementation.\n\n"
            f"## Specification\n{spec}\n\n"
            f"## Partial Implementation\n```verilog\n{partial}\n```"
        )
        assistant_content = f"```verilog\n{verilog}\n```"
        pairs.append({
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ],
            "task_type": "editing",
        })
    log.info(f"  Generated {len(pairs)} editing pairs")
    return pairs


# ---------------------------------------------------------------------------
# Step 5 — spec-to-RTL pairs (base task)
# ---------------------------------------------------------------------------

def make_spec_to_rtl_pairs(scored_triples: list[tuple[str, str, int]]) -> list[dict]:
    """
    scored_triples: list of (verilog, spec, quality_score) from LLM-as-Judge.
    quality_score is stored in the output for traceability.
    """
    pairs = []
    for verilog, spec, score in scored_triples:
        user_content = (
            f"Generate synthesizable Verilog RTL for the following specification.\n\n"
            f"## Specification\n{spec}"
        )
        assistant_content = f"```verilog\n{verilog}\n```"
        pairs.append({
            "messages": [
                {"role": "user", "content": user_content},
                {"role": "assistant", "content": assistant_content},
            ],
            "task_type": "spec_to_rtl",
            "quality_score": score,
        })
    return pairs


# ---------------------------------------------------------------------------
# Step 6 — Final iverilog pass on all assistant outputs
# ---------------------------------------------------------------------------

def extract_verilog_from_response(text: str) -> str:
    m = re.search(r'```(?:verilog|systemverilog|sv)?\s*\n(.*?)```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def final_quality_filter(samples: list[dict]) -> list[dict]:
    """Keep only samples whose assistant output Verilog compiles with iverilog."""
    log.info(f"Final iverilog quality filter on {len(samples)} samples...")
    clean = []
    fail_count = 0
    for s in tqdm(samples, desc="final iverilog check"):
        assistant_text = s["messages"][1]["content"]
        verilog = extract_verilog_from_response(assistant_text)
        if iverilog_check(verilog):
            clean.append(s)
        else:
            fail_count += 1
    if samples:
        log.info(f"  Kept {len(clean)}/{len(samples)} ({100*len(clean)//len(samples)}%), dropped {fail_count}")
    else:
        log.info("  No samples to filter")
    return clean


# ---------------------------------------------------------------------------
# Main pipeline
# ---------------------------------------------------------------------------

def main():
    parser = argparse.ArgumentParser(description="Prepare RTL fine-tuning dataset")
    parser.add_argument("--limit", type=int, default=None,
                        help="Max raw modules to process (default: all)")
    parser.add_argument("--workers", type=int, default=8,
                        help="Parallel workers for iverilog and API calls")
    parser.add_argument("--out", type=str, default="data/final_finetune.jsonl",
                        help="Output JSONL path")
    parser.add_argument("--benchmark", type=str,
                        default="data/cid003_nonagentic.jsonl",
                        help="CVDP benchmark JSONL for decontamination")
    parser.add_argument("--decontam-threshold", type=float, default=0.8,
                        help="Jaccard similarity threshold for decontamination (default 0.8)")
    parser.add_argument("--min-judge-score", type=int, default=3,
                        help="Minimum LLM-as-Judge score to keep a pair (1-5, default 3)")
    parser.add_argument("--seed", type=int, default=42)
    parser.add_argument("--skip-download", action="store_true",
                        help="Skip HuggingFace download, use cached modules")
    parser.add_argument("--skip-verilator", action="store_true",
                        help="Skip Verilator lint gate (use if Verilator not installed)")
    parser.add_argument("--spec-model", type=str, default="claude-haiku-4-5-20251001",
                        help="Model for spec generation. Use claude-sonnet-4-6 for best quality.")
    parser.add_argument("--seed-jsonl", type=str, default=None,
                        help="Path to a high-quality seed JSONL (messages format) to prepend "
                             "before the generated data. These bypass all quality gates.")
    args = parser.parse_args()

    # Apply --spec-model globally before any API calls
    global SPEC_GEN_MODEL
    SPEC_GEN_MODEL = args.spec_model
    log.info(f"Spec generation model: {args.spec_model}")

    random.seed(args.seed)

    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        raise EnvironmentError("ANTHROPIC_API_KEY not set")
    client = anthropic.Anthropic(api_key=api_key)

    # ---- Stage 1a: Load raw modules ----
    # Cache key encodes the limit so a --limit 200 run never poisons a full run.
    cache_key = f"limit{args.limit}" if args.limit else "full"
    validated_cache = CACHE_DIR / f"validated_modules_{cache_key}.json"

    if validated_cache.exists() and args.skip_download:
        log.info("Loading validated modules from cache...")
        with open(validated_cache) as f:
            valid_modules = json.load(f)
        log.info(f"  Loaded {len(valid_modules)} cached valid modules")
    else:
        log.info("Downloading shailja/Verilog_GitHub from HuggingFace...")
        ds = load_dataset("shailja/Verilog_GitHub", split="train", trust_remote_code=True)
        raw = [row["text"] for row in ds if row.get("text", "").strip()]
        log.info(f"  Downloaded {len(raw)} raw modules")

        if args.limit:
            raw = random.sample(raw, min(args.limit, len(raw)))
            log.info(f"  Subsampled to {len(raw)} modules (--limit {args.limit})")

        # Size filter
        raw = [m for m in raw if 50 < len(m) < 3000 and "module" in m]
        log.info(f"  After size filter: {len(raw)} modules")

        # Synthesizability filter — reject testbenches and simulation files
        raw = [m for m in raw if is_synthesizable_rtl(m)]
        log.info(f"  After synthesizability filter: {len(raw)} modules")

        # Gate 1: iverilog
        valid_modules = filter_valid_modules(raw, workers=args.workers)

        # Gate 2: Verilator lint
        if not args.skip_verilator:
            valid_modules = filter_verilator(valid_modules, workers=args.workers)
        else:
            log.info("Verilator gate skipped (--skip-verilator)")

        with open(validated_cache, "w") as f:
            json.dump(valid_modules, f)
        log.info(f"  Saved {len(valid_modules)} validated modules to cache")

    # ---- Stage 1b: Generate specs ----
    # Content-addressed cache: merge ALL existing spec_pairs_*.json files so
    # previously generated specs are never re-paid-for across runs, regardless
    # of --limit. Matching is by Verilog text content, not module count.
    spec_cache = CACHE_DIR / f"spec_pairs_{len(valid_modules)}.json"

    existing_specs: dict[str, str] = {}
    for prior in sorted(CACHE_DIR.glob("spec_pairs_*.json")):
        with open(prior) as fh:
            for entry in json.load(fh):
                if len(entry) >= 2:
                    existing_specs.setdefault(entry[0], entry[1])
    log.info(f"Merged {len(existing_specs)} specs from existing caches")

    remaining = [m for m in valid_modules if m not in existing_specs]
    log.info(f"  {len(remaining)} modules still need spec generation")

    if remaining:
        new_pairs = generate_specs_batch(client, remaining, workers=args.workers)
        for v, s in new_pairs:
            existing_specs[v] = s

    spec_pairs = [(v, existing_specs[v]) for v in valid_modules if v in existing_specs]

    # Gate 3: Jaccard decontamination
    benchmark_specs = load_benchmark_specs(args.benchmark)
    spec_pairs = decontaminate_specs(spec_pairs, benchmark_specs,
                                     threshold=args.decontam_threshold)

    with open(spec_cache, "w") as f:
        json.dump(spec_pairs, f)
    log.info(f"Saved {len(spec_pairs)} decontaminated spec pairs to {spec_cache.name}")

    # ---- Stage 1c: LLM-as-Judge scoring (Gate 4) ----
    # Content-addressed: merge all scored_pairs_*.json so judge calls are never
    # repeated across runs. Only unscored spec pairs hit the API.
    scored_cache = CACHE_DIR / f"scored_pairs_{len(valid_modules)}.json"

    existing_scored: dict[str, tuple] = {}  # verilog -> (spec, score)
    for prior in sorted(CACHE_DIR.glob("scored_pairs_*.json")):
        with open(prior) as fh:
            for entry in json.load(fh):
                if len(entry) >= 3:
                    existing_scored.setdefault(entry[0], (entry[1], int(entry[2])))
    log.info(f"Merged {len(existing_scored)} scored pairs from existing caches")

    unscored = [(v, s) for v, s in spec_pairs if v not in existing_scored]
    log.info(f"  {len(unscored)} spec pairs still need judge scoring")

    if unscored:
        new_scored = score_pairs_batch(
            client, unscored, workers=args.workers,
            min_score=args.min_judge_score
        )
        for v, s, score in new_scored:
            existing_scored[v] = (s, score)

    scored_triples = [
        (v, existing_scored[v][0], existing_scored[v][1])
        for v, s in spec_pairs
        if v in existing_scored
    ]

    with open(scored_cache, "w") as f:
        json.dump(scored_triples, f)
    log.info(f"Saved {len(scored_triples)} scored pairs to {scored_cache.name}")

    # Convert back to plain (verilog, spec) for debugging/editing tasks
    # (they don't need per-pair scores since we're starting from already-scored correct code)
    spec_pairs_clean = [(v, s) for v, s, _ in scored_triples]

    # ---- Stage 2: Build all three task types ----
    log.info("Building task-specific training pairs...")

    random.shuffle(spec_pairs_clean)
    n = len(spec_pairs_clean)
    s2r_pairs = scored_triples  # keep scores for spec-to-RTL
    dbg_pairs_src = spec_pairs_clean[:int(n * 0.6)]
    edit_pairs_src = spec_pairs_clean[int(n * 0.4):]

    s2r_samples = make_spec_to_rtl_pairs(s2r_pairs)
    dbg_samples = make_debugging_pairs(dbg_pairs_src)
    edit_samples = make_editing_pairs(edit_pairs_src)

    log.info(f"  Raw counts — spec-to-RTL: {len(s2r_samples)}, "
             f"debugging: {len(dbg_samples)}, editing: {len(edit_samples)}")

    # ---- Stage 3: Mix to target ratio ----
    MAX_TOTAL = 100_000
    target_s2r = int(MAX_TOTAL * 0.65)
    target_dbg = int(MAX_TOTAL * 0.175)
    target_edit = int(MAX_TOTAL * 0.175)

    s2r_samples = random.sample(s2r_samples, min(len(s2r_samples), target_s2r))
    dbg_samples = random.sample(dbg_samples, min(len(dbg_samples), target_dbg))
    edit_samples = random.sample(edit_samples, min(len(edit_samples), target_edit))

    all_samples = s2r_samples + dbg_samples + edit_samples
    random.shuffle(all_samples)
    log.info(f"  After mixing: {len(s2r_samples)} s2r + {len(dbg_samples)} dbg "
             f"+ {len(edit_samples)} edit = {len(all_samples)} total")

    # ---- Stage 4: Final iverilog quality gate on all outputs ----
    clean_samples = final_quality_filter(all_samples)

    # ---- Stage 4b: Prepend high-quality seed data ----
    seed_samples = []
    if args.seed_jsonl and Path(args.seed_jsonl).exists():
        with open(args.seed_jsonl) as f:
            seed_samples = [json.loads(l) for l in f if l.strip()]
        log.info(f"Loaded {len(seed_samples)} seed samples from {args.seed_jsonl}")
        clean_samples = seed_samples + clean_samples
        log.info(f"  Total after prepending seed: {len(clean_samples)}")

    # ---- Stage 5: Write output ----
    out_path = Path(args.out)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    with open(out_path, "w") as f:
        for s in clean_samples:
            f.write(json.dumps(s) + "\n")

    from collections import Counter
    type_counts = Counter(s["task_type"] for s in clean_samples)
    scored_kept = [s for s in clean_samples if "quality_score" in s]
    avg_score = (sum(s["quality_score"] for s in scored_kept) / len(scored_kept)
                 if scored_kept else 0)

    log.info("=" * 60)
    log.info(f"DONE. Wrote {len(clean_samples)} samples to {out_path}")
    log.info(f"  spec_to_rtl: {type_counts['spec_to_rtl']}  (avg judge score: {avg_score:.2f})")
    log.info(f"  debugging:   {type_counts['debugging']}")
    log.info(f"  editing:     {type_counts['editing']}")
    log.info(f"  Total:       {len(clean_samples)}")
    log.info("=" * 60)


if __name__ == "__main__":
    main()
