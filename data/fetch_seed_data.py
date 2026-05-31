#!/usr/bin/env python3
"""
Fetch high-quality (spec, RTL) seed pairs from public benchmarks:
  - VerilogEval-Human (via NVlabs GitHub repo — most reliable)
  - HDLBits-style datasets from HuggingFace (multiple fallback paths)

These are ground-truth pairs with human-authored specs — much higher quality
than OSS-Instruct generated specs. Even ~400 seed samples can significantly
anchor fine-tuning quality.

Output: data/seed_finetune.jsonl (same format as prepare_finetune_data.py output)

Usage:
    python data/fetch_seed_data.py --out data/seed_finetune.jsonl
"""
import argparse
import json
import os
import re
import subprocess
import tempfile
from pathlib import Path


def iverilog_check(verilog: str) -> bool:
    with tempfile.NamedTemporaryFile(suffix=".v", mode="w", delete=False) as f:
        f.write(verilog)
        path = f.name
    try:
        r = subprocess.run(
            ["iverilog", "-g2012", "-o", "/dev/null", path],
            capture_output=True, text=True, timeout=10
        )
        return r.returncode == 0
    except Exception:
        return False
    finally:
        os.unlink(path)


def extract_verilog(text: str) -> str:
    m = re.search(r'```(?:verilog|systemverilog|sv)?\s*\n(.*?)```', text, re.DOTALL)
    if m:
        return m.group(1).strip()
    return text.strip()


def to_training_sample(spec: str, verilog: str, source: str) -> dict:
    return {
        "messages": [
            {"role": "user",
             "content": f"Generate synthesizable Verilog RTL for the following specification.\n\n## Specification\n{spec}"},
            {"role": "assistant",
             "content": f"```verilog\n{verilog}\n```"},
        ],
        "task_type": "spec_to_rtl",
        "quality_score": 5,  # human-authored = top quality
        "source": source,
    }


def fetch_verilogeval_github(out_samples: list) -> int:
    """
    Clone NVlabs/verilog-eval from GitHub and extract (description, solution) pairs.
    The repo uses paired files: ProbXXX_name_prompt.txt + ProbXXX_name_ref.sv
    in dataset_spec-to-rtl/ and dataset_code-complete-iccad2023/.
    """
    import shutil

    tmpdir = tempfile.mkdtemp(prefix="verilogeval_")
    try:
        print("Cloning NVlabs/verilog-eval from GitHub...")
        r = subprocess.run(
            ["git", "clone", "--depth=1",
             "https://github.com/NVlabs/verilog-eval.git", tmpdir],
            capture_output=True, text=True, timeout=120
        )
        if r.returncode != 0:
            print(f"  Git clone failed: {r.stderr.strip()}")
            return 0

        count = 0
        # Each dataset dir has ProbXXX_name_prompt.txt + ProbXXX_name_ref.sv pairs
        for dataset_dir in ["dataset_spec-to-rtl", "dataset_code-complete-iccad2023"]:
            ddir = Path(tmpdir) / dataset_dir
            if not ddir.exists():
                continue
            for prompt_file in sorted(ddir.glob("*_prompt.txt")):
                # Derive ref file: replace _prompt.txt with _ref.sv
                ref_file = Path(str(prompt_file).replace("_prompt.txt", "_ref.sv"))
                if not ref_file.exists():
                    continue
                spec = prompt_file.read_text().strip()
                verilog = ref_file.read_text().strip()
                if not spec or not verilog or "module" not in verilog:
                    continue
                if not iverilog_check(verilog):
                    continue
                out_samples.append(to_training_sample(spec, verilog, "verilogeval_human"))
                count += 1

        print(f"  VerilogEval GitHub: {count} samples")
        return count
    finally:
        shutil.rmtree(tmpdir, ignore_errors=True)


def fetch_verilogeval_hf(out_samples: list) -> int:
    """Try several known HuggingFace paths for the VerilogEval dataset."""
    try:
        from datasets import load_dataset
    except ImportError:
        return 0

    candidates = [
        ("NVlabs/verilog-eval", "verilog_eval_human", "test"),
        ("NVlabs/verilog-eval", None, "test"),
        ("GaTech-EIC/VerilogEval-Human", None, "test"),
        ("Siwei7/verilog-eval", None, "test"),
        ("Ruijie-Mao/verilog-eval-v2", None, "test"),
    ]

    for ds_name, config, split in candidates:
        try:
            kwargs = {"split": split}
            if config:
                kwargs["name"] = config
            ds = load_dataset(ds_name, **kwargs)
            count = 0
            for row in ds:
                spec = (row.get("prompt") or row.get("problem_description")
                        or row.get("description") or "")
                solution = (row.get("canonical_solution") or row.get("solution")
                            or row.get("reference") or "")
                if not spec or not solution:
                    continue
                verilog = extract_verilog(solution) if "```" in solution else solution.strip()
                if not verilog or "module" not in verilog:
                    continue
                if not iverilog_check(verilog):
                    continue
                out_samples.append(to_training_sample(spec.strip(), verilog, ds_name))
                count += 1
            if count > 0:
                print(f"  VerilogEval HuggingFace ({ds_name}): {count} samples")
                return count
        except Exception as e:
            print(f"  {ds_name} not available: {e}")

    return 0


def fetch_hdlbits(out_samples: list) -> int:
    """Try several HuggingFace paths for HDLBits-style datasets."""
    try:
        from datasets import load_dataset
    except ImportError:
        return 0

    candidates = [
        ("Databean/HDLBits-Verilog", "train"),
        ("vlsi-lab/hdl-bits", "train"),
        ("verigen/HDLBits", "train"),
        ("RTLBench/HDLBits", "train"),
        ("hdlbits/hdlbits", "train"),
    ]

    for ds_name, split_name in candidates:
        try:
            ds = load_dataset(ds_name, split=split_name)
            count = 0
            for row in ds:
                spec = (row.get("description") or row.get("prompt") or
                        row.get("problem_statement") or "")
                solution = (row.get("solution") or row.get("canonical_solution") or
                            row.get("code") or row.get("verilog") or "")
                if not spec or not solution:
                    continue
                verilog = extract_verilog(solution) if "```" in solution else solution.strip()
                if not verilog or "module" not in verilog:
                    continue
                if not iverilog_check(verilog):
                    continue
                out_samples.append(to_training_sample(spec.strip(), verilog, ds_name))
                count += 1
            if count > 0:
                print(f"  HDLBits ({ds_name}): {count} samples")
                return count
        except Exception as e:
            print(f"  {ds_name} not available: {e}")

    return 0


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--out", default="data/seed_finetune.jsonl")
    parser.add_argument("--skip-github", action="store_true",
                        help="Skip GitHub clone (use only HuggingFace)")
    args = parser.parse_args()

    samples = []

    # 1. Try GitHub clone first (most reliable)
    n_ve_gh = 0
    if not args.skip_github:
        n_ve_gh = fetch_verilogeval_github(samples)

    # 2. Try HuggingFace fallback for VerilogEval
    n_ve_hf = 0
    if n_ve_gh == 0:
        print("GitHub clone yielded 0 samples, trying HuggingFace...")
        n_ve_hf = fetch_verilogeval_hf(samples)

    # 3. HDLBits from HuggingFace
    n_hb = fetch_hdlbits(samples)

    if not samples:
        print("WARNING: No seed samples collected from any source.")
        print("  The main pipeline (prepare_finetune_data.py) will still work without seeds.")
        return

    out = Path(args.out)
    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w") as f:
        for s in samples:
            f.write(json.dumps(s) + "\n")

    total = len(samples)
    print(f"\nDone. Wrote {total} seed samples to {out}")
    print(f"  VerilogEval (GitHub): {n_ve_gh}")
    print(f"  VerilogEval (HF):     {n_ve_hf}")
    print(f"  HDLBits:              {n_hb}")


if __name__ == "__main__":
    main()
