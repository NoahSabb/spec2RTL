#!/usr/bin/env python3
"""
Pre-copy harness directories from a reference work dir into a new work dir
so the agentic factory can find them at model.prompt() call time.

Usage:
    python scripts/setup_harnesses.py \
        --source work_claude_sonnet46_1sample \
        --dest work_agentic_v2 \
        --problems cvdp_copilot_gcd cvdp_copilot_GFCM ...
"""
import argparse
import shutil
import os

BENCH_DIR = os.path.join(os.path.dirname(__file__), "..", "cvdp_benchmark")

def setup_harnesses(source: str, dest: str, problems: list[str]) -> None:
    bench = os.path.abspath(BENCH_DIR)
    copied, skipped, missing = 0, 0, 0

    for prob in problems:
        # Source dirs may omit the trailing _NNNN version suffix (e.g. _0001)
        src_name = prob
        src_harness = os.path.join(bench, source, src_name, "harness", "1")
        if not os.path.isdir(src_harness):
            # Strip version suffix: cvdp_copilot_gcd_0001 → cvdp_copilot_gcd
            import re
            src_name = re.sub(r'_\d{4}$', '', prob)
            src_harness = os.path.join(bench, source, src_name, "harness", "1")
        dst_harness = os.path.join(bench, dest, prob, "harness", "1")

        if not os.path.isdir(src_harness):
            print(f"MISSING source: {src_harness}")
            missing += 1
            continue

        if os.path.isdir(dst_harness):
            print(f"SKIP (exists): {dst_harness}")
            skipped += 1
            continue

        os.makedirs(os.path.dirname(dst_harness), exist_ok=True)
        shutil.copytree(src_harness, dst_harness)
        print(f"OK: {prob}")
        copied += 1

    print(f"\nDone. Copied: {copied}, Skipped: {skipped}, Missing: {missing}")


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--source", required=True, help="Source work dir (has existing harnesses)")
    parser.add_argument("--dest", required=True, help="Destination work dir to create harnesses in")
    parser.add_argument("--problems", nargs="+", required=True, help="Problem dir names (e.g. cvdp_copilot_gcd)")
    args = parser.parse_args()
    setup_harnesses(args.source, args.dest, args.problems)
