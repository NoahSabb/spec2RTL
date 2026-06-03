"""
Local test runner for agentic loop v2.

Runs 5 problems that failed cocotb but passed iverilog in RL v2 eval.
Starts each problem from the pre-generated RL v2 RTL (no initial generation call).
Logs every iteration to logs/agentic_loop_test.jsonl.

Usage:
    python agents/v2/run_local_test.py

Environment:
    ANTHROPIC_API_KEY  — required (falls back to cvdp_benchmark config_manager)
    RL_V2_RTL_DIR      — directory with RL v2 .sv files
                         (default: ~/Downloads/cid003_eval_rl_v2)
    HARNESS_BASE       — benchmark work directory
                         (default: cvdp_benchmark/work_qwen32b_lora_rl_v2)
    LOG_FILE           — iteration log path
                         (default: logs/agentic_loop_test.jsonl)
"""

import json
import logging
import os
import sys
from pathlib import Path
from datetime import datetime

# ── path setup ───────────────────────────────────────────────────────────────
_here = Path(__file__).parent
_root = _here.parent.parent
sys.path.insert(0, str(_here))
sys.path.insert(0, str(_root / "cvdp_benchmark"))

# Resolve API key early (falls back to config_manager if env not set)
if not os.environ.get("ANTHROPIC_API_KEY"):
    try:
        from src.config_manager import config
        key = config.get("ANTHROPIC_API_KEY")
        if key:
            os.environ["ANTHROPIC_API_KEY"] = key
    except Exception:
        pass

import anthropic
from agentic_loop_v2 import run_agentic_loop_v2
from claude_gen_factory import ClaudeGenerator

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    datefmt="%H:%M:%S",
)
log = logging.getLogger(__name__)

# ── configuration ─────────────────────────────────────────────────────────────

# Problems: failed cocotb, passed iverilog in RL v2 — representative mix
TEST_PROBLEMS = [
    {
        "id": "cvdp_copilot_moving_average_0001",
        "harness_subdir": "cvdp_copilot_moving_average/harness/1",
        "rtl_filename": "moving_average.v",
        "rtl_stem": "cvdp_copilot_moving_average_0001",
    },
    {
        "id": "cvdp_copilot_morse_code_0001",
        "harness_subdir": "cvdp_copilot_morse_code/harness/1",
        "rtl_filename": "morse_encoder.sv",
        "rtl_stem": "cvdp_copilot_morse_code_0001",
    },
    {
        "id": "cvdp_copilot_piso_0001",
        "harness_subdir": "cvdp_copilot_piso/harness/1",
        "rtl_filename": "piso_8bit.sv",
        "rtl_stem": "cvdp_copilot_piso_0001",
    },
    {
        "id": "cvdp_copilot_fsm_seq_detector_0001",
        "harness_subdir": "cvdp_copilot_fsm_seq_detector/harness/1",
        "rtl_filename": "fsm_seq_detector.sv",
        "rtl_stem": "cvdp_copilot_fsm_seq_detector_0001",
    },
    {
        "id": "cvdp_copilot_clock_divider_0003",
        "harness_subdir": "cvdp_copilot_clock_divider/harness/3",
        "rtl_filename": "clock_divider.sv",
        "rtl_stem": "cvdp_copilot_clock_divider_0003",
    },
]

RL_V2_RTL_DIR = Path(
    os.environ.get("RL_V2_RTL_DIR", Path.home() / "Downloads/cid003_eval_rl_v2")
)
HARNESS_BASE = Path(
    os.environ.get("HARNESS_BASE", _root / "cvdp_benchmark/work_qwen32b_lora_rl_v2")
)
DATA_FILE = _root / "data/cid003_nonagentic.jsonl"
LOG_FILE = Path(
    os.environ.get("LOG_FILE", _root / "logs/agentic_loop_test.jsonl")
)
MAX_ITER = 5


def load_specs() -> dict:
    specs = {}
    with open(DATA_FILE) as f:
        for line in f:
            if not line.strip():
                continue
            d = json.loads(line)
            specs[d["id"]] = d["input"]["prompt"]
    return specs


def load_initial_verilog(rtl_stem: str) -> str | None:
    for ext in (".sv", ".v"):
        p = RL_V2_RTL_DIR / f"{rtl_stem}{ext}"
        if p.exists():
            log.info(f"Loaded initial RTL from {p}")
            return p.read_text()
    log.warning(f"No pre-generated RTL found for {rtl_stem} in {RL_V2_RTL_DIR}")
    return None


def main():
    api_key = os.environ.get("ANTHROPIC_API_KEY")
    if not api_key:
        print("ERROR: ANTHROPIC_API_KEY not set", file=sys.stderr)
        sys.exit(1)

    LOG_FILE.parent.mkdir(parents=True, exist_ok=True)

    generator = ClaudeGenerator(model="claude-sonnet-4-6", api_key=api_key)
    client = anthropic.Anthropic(api_key=api_key)

    specs = load_specs()
    summary = []

    log.info(f"=== Agentic Loop v2 — Local Test Run ({len(TEST_PROBLEMS)} problems) ===")
    log.info(f"Harness base: {HARNESS_BASE}")
    log.info(f"RTL dir:      {RL_V2_RTL_DIR}")
    log.info(f"Log file:     {LOG_FILE}")

    for prob in TEST_PROBLEMS:
        pid = prob["id"]
        spec = specs.get(pid)
        if not spec:
            log.error(f"Spec not found for {pid}")
            continue

        harness_dir = str(HARNESS_BASE / prob["harness_subdir"])
        if not os.path.isdir(harness_dir):
            log.warning(f"Harness dir missing: {harness_dir} — skipping {pid}")
            continue

        initial_rtl = load_initial_verilog(prob["rtl_stem"])

        log.info(f"\n{'='*60}")
        log.info(f"Running: {pid}")
        log.info(f"Harness: {harness_dir}")
        log.info(f"RTL:     {prob['rtl_filename']}")
        log.info(f"Initial: {'pre-loaded RL v2 RTL' if initial_rtl else 'generating fresh'}")

        try:
            result = run_agentic_loop_v2(
                generator=generator,
                client=client,
                spec=spec,
                max_iterations=MAX_ITER,
                harness_dir=harness_dir,
                rtl_filename=prob["rtl_filename"],
                initial_verilog=initial_rtl,
                log_file=str(LOG_FILE),
                problem_id=pid,
            )
        except Exception as e:
            log.error(f"Loop crashed for {pid}: {e}", exc_info=True)
            result = {"passed": False, "iterations": 0, "error": str(e)}

        summary.append({
            "problem_id": pid,
            "passed": result.get("passed", False),
            "iterations": result.get("iterations", 0),
        })
        status = "PASS" if result.get("passed") else "FAIL"
        log.info(f"RESULT {pid}: {status} after {result.get('iterations', 0)} iter")

    # ── final summary ─────────────────────────────────────────────────────────
    passed = [s for s in summary if s["passed"]]
    print("\n" + "="*60)
    print(f"AGENTIC LOOP v2 LOCAL TEST SUMMARY")
    print(f"  Pass: {len(passed)}/{len(summary)}")
    for s in summary:
        status = "PASS" if s["passed"] else "FAIL"
        print(f"  [{status}] {s['problem_id']} (iter={s['iterations']})")
    print("="*60)

    summary_entry = {
        "event": "summary",
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "total": len(summary),
        "passed": len(passed),
        "results": summary,
    }
    with open(LOG_FILE, "a") as f:
        f.write(json.dumps(summary_entry) + "\n")

    log.info(f"Full iteration log: {LOG_FILE}")


if __name__ == "__main__":
    main()
