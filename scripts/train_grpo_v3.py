#!/usr/bin/env python3
"""
GRPO RL v3 — starts from the existing RL v2 adapter.

Loading strategy:
  1. Load Qwen2.5-Coder-32B-Instruct base in bf16.
  2. Merge SFT adapter (r=32) into base weights.
  3. Merge RL v2 adapter (r=16) into the SFT-merged base weights.
  4. Attach a fresh r=16 LoRA for this round of RL training.

Reward function (hybrid, in priority order):
  1. iverilog hard fail → 0.0
  2. iverilog soft fail (wire/reg/cast/select errors) → 0.2
  3. iverilog clean pass + Docker/cocotb unavailable → 1.0
  4. iverilog clean pass + cocotb pass → 1.0
  5. iverilog clean pass + cocotb fail → 0.5
  Fallback (no Docker): clean→1.0, soft→0.3, hard→0.0  (logged at startup)

Docker check runs once at startup via check_docker_available(). If Docker or
cvdp-sim image are absent, COCOTB_MODE is set to False and all rewards follow
the iverilog-only tiered scheme.

Differences from train_grpo.py (v2):
  - Two-adapter load (SFT then RL v2)
  - Hybrid cocotb reward when Docker is present
  - G=4 completions, max_new_tokens=512, lr=3e-6
  - Epoch checkpoints saved as epoch1/, epoch2/, epoch3/
  - Output: qwen32b-lora-rl-v3

Usage:
  # Dry run (5 problems, 2 steps):
  python3 scripts/train_grpo_v3.py --dry-run

  # Full training:
  python3 scripts/train_grpo_v3.py
"""

import argparse
import json
import logging
import math
import os
import re
import subprocess
import sys
import tempfile
import time
from pathlib import Path

import torch
import torch.nn.functional as F
from peft import PeftModel, LoraConfig, get_peft_model
from transformers import AutoModelForCausalLM, AutoTokenizer, get_cosine_schedule_with_warmup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"
SHARED_CACHE = "/home/_shared/models"

DEFAULT_SFT_ADAPTER = "/home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-35e941c1"
DEFAULT_RL_ADAPTER  = "/home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v2"
DEFAULT_OUT         = "/home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v3"
DEFAULT_BENCH_DIR   = "/home/noahsabb/spec2rtl/cvdp_benchmark"

USER_TEMPLATE = (
    "Generate synthesizable Verilog RTL for the following specification.\n\n"
    "## Specification\n{spec}"
)

SOFT_FAIL_PATTERNS = [
    "is not a net",
    "non-continuous assignment",
    "explicit cast required",
    "is not a constant",
    "out of range",
    "Unknown port",
    "port mismatch",
    "wrong number of ports",
    "unable to bind",
    "implicit definition",
]

HARD_FAIL_PATTERNS = [
    "Unknown module type",
    "No such file or directory",
]

REFUSAL_MARKERS = [
    "i give up", "i cannot", "i'm sorry", "as an ai",
    "i apologize", "unable to generate", "not able to",
]

DATA_SEARCH_PATHS = [
    "/home/noahsabb/spec2rtl/cvdp_benchmark/cid003_nonagentic.jsonl",
    "/home/noahsabb/data/cid003_nonagentic.jsonl",
]

# Set at startup by check_docker_available(); True = use hybrid cocotb reward.
COCOTB_MODE: bool = False
# If Docker check finds Docker but not the image, log which image name was missing.
_DOCKER_IMAGE_CANDIDATES = ["cvdp-sim:latest", "nvidia/cvdp-sim:v1.0.0"]


# ── Args ──────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=None)
    p.add_argument("--sft-adapter", default=DEFAULT_SFT_ADAPTER,
                   help="SFT LoRA adapter to merge first (r=32)")
    p.add_argument("--adapter", default=DEFAULT_RL_ADAPTER,
                   help="RL v2 LoRA adapter to merge second (r=16)")
    p.add_argument("--out", default=DEFAULT_OUT)
    p.add_argument("--bench-dir", default=DEFAULT_BENCH_DIR,
                   help="CVDP benchmark root for cocotb harnesses")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--lr", type=float, default=3e-6)
    p.add_argument("--max-new-tokens", type=int, default=512)
    p.add_argument("--num-generations", type=int, default=4,
                   help="Completions per problem per step (G in GRPO)")
    p.add_argument("--temperature", type=float, default=0.9)
    p.add_argument("--epsilon", type=float, default=0.2)
    p.add_argument("--max-problems", type=int, default=None)
    p.add_argument("--max-steps", type=int, default=-1)
    p.add_argument("--no-cocotb", action="store_true",
                   help="Skip cocotb check even if Docker is available")
    p.add_argument("--no-r2-upload", action="store_true")
    p.add_argument("--dry-run", action="store_true")
    return p.parse_args()


# ── Data ──────────────────────────────────────────────────────────────────────

def find_data(explicit):
    if explicit and Path(explicit).exists():
        return explicit
    if explicit:
        log.warning(f"Specified path not found: {explicit}")
    for p in DATA_SEARCH_PATHS:
        if Path(p).exists():
            log.info(f"Data: {p}")
            return p
    raise FileNotFoundError(f"cid003_nonagentic.jsonl not found; tried: {DATA_SEARCH_PATHS}")


def load_problems(path, max_problems=None):
    problems = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if line:
                problems.append(json.loads(line))
    if max_problems:
        problems = problems[:max_problems]
    log.info(f"Loaded {len(problems)} problems from {path}")
    return problems


# ── Docker / cocotb ───────────────────────────────────────────────────────────

def check_docker_available(bench_dir: str) -> tuple[bool, str]:
    """Return (available, reason_string).

    Checks:
      1. `docker info` — daemon is running and reachable.
      2. One of _DOCKER_IMAGE_CANDIDATES exists in the local image store.
    """
    try:
        r = subprocess.run(
            ["docker", "info"],
            capture_output=True, text=True, timeout=15,
        )
        if r.returncode != 0:
            return False, f"docker info failed (rc={r.returncode}): {r.stderr[:200]}"
    except FileNotFoundError:
        return False, "docker binary not found on PATH"
    except subprocess.TimeoutExpired:
        return False, "docker info timed out (15s)"

    available_image = None
    for img in _DOCKER_IMAGE_CANDIDATES:
        r = subprocess.run(
            ["docker", "image", "inspect", img],
            capture_output=True, timeout=10,
        )
        if r.returncode == 0:
            available_image = img
            break

    if available_image is None:
        return False, (
            f"Docker daemon OK but none of {_DOCKER_IMAGE_CANDIDATES} found. "
            "Pull or build cvdp-sim before training."
        )

    # Verify at least one problem harness exists in bench_dir.
    bench = Path(bench_dir)
    has_harness = any(
        True for _ in bench.glob("work_*/*/harness/1/src/.env")
    ) if bench.is_dir() else False
    if not has_harness:
        return False, (
            f"Docker+image OK but no harnesses found under {bench_dir}/work_*/. "
            "Run the benchmark at least once to create harness directories."
        )

    return True, f"Docker OK, image={available_image}, harnesses present"


def _get_harness_dir(problem_id: str, bench_dir: str) -> Path | None:
    """Return Path to harness/1 for problem_id, or None if not found."""
    bench = Path(bench_dir)
    for work in bench.glob("work_*/"):
        h = work / problem_id / "harness" / "1"
        if h.is_dir() and (h / "src" / ".env").exists():
            return h
    return None


def _parse_verilog_sources_filename(env_path: Path) -> str | None:
    """Read VERILOG_SOURCES from a harness .env and return the leaf filename."""
    for line in env_path.read_text().splitlines():
        line = line.strip()
        if line.startswith("VERILOG_SOURCES"):
            _, _, rhs = line.partition("=")
            parts = rhs.strip().split()
            if parts:
                return Path(parts[0]).name
    return None


def cocotb_test(problem_id: str, rtl_text: str, bench_dir: str, timeout: int = 120) -> bool | None:
    """Run the cocotb harness for one problem.

    Returns:
      True   — cocotb tests passed (exit code 0)
      False  — cocotb tests failed
      None   — harness not found or Docker error (treat as no test result)
    """
    harness_dir = _get_harness_dir(problem_id, bench_dir)
    if harness_dir is None:
        log.debug(f"cocotb_test: no harness found for {problem_id}")
        return None

    src_dir = harness_dir / "src"
    env_path = src_dir / ".env"
    rtl_filename = _parse_verilog_sources_filename(env_path) or f"{problem_id}.sv"

    # Determine the Docker image to use.
    image = None
    for img in _DOCKER_IMAGE_CANDIDATES:
        r = subprocess.run(
            ["docker", "image", "inspect", img],
            capture_output=True, timeout=5,
        )
        if r.returncode == 0:
            image = img
            break
    if image is None:
        return None

    with tempfile.TemporaryDirectory() as tmpdir:
        tmp = Path(tmpdir)
        rtl_dir = tmp / "rtl"
        run_dir = tmp / "rundir"
        rtl_dir.mkdir()
        run_dir.mkdir()
        (rtl_dir / rtl_filename).write_text(rtl_text)

        cmd = [
            "docker", "run", "--rm",
            "--network", "none",
            "--user", f"{os.getuid()}:{os.getgid()}",
            "-e", "HOME=/code/rundir",
            "-w", "/code/rundir",
            "--env-file", str(env_path),
            "-v", f"{rtl_dir}:/code/rtl:ro",
            "-v", f"{src_dir}:/src:ro",
            "-v", f"{src_dir}:/code/src:ro",
            "-v", f"{run_dir}:/code/rundir",
            image,
            "pytest", "-s", "-q",
            "-o", "cache_dir=/code/rundir/harness/.cache",
            "/src/test_runner.py",
        ]

        try:
            r = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
            passed = r.returncode == 0
            log.debug(
                f"cocotb_test {problem_id}: {'PASS' if passed else 'FAIL'} "
                f"(rc={r.returncode})"
            )
            return passed
        except subprocess.TimeoutExpired:
            log.warning(f"cocotb_test {problem_id}: TIMEOUT after {timeout}s")
            return False
        except Exception as e:
            log.warning(f"cocotb_test {problem_id}: exception {e}")
            return None


# ── Model loading ─────────────────────────────────────────────────────────────

def find_base_model():
    cache_name = "models--" + MODEL_ID.replace("/", "--")
    for base in [SHARED_CACHE, os.environ.get("HF_HOME", "/home/noahsabb/.cache/huggingface")]:
        p = Path(base) / "hub" / cache_name / "snapshots"
        if p.is_dir():
            snaps = sorted(p.iterdir())
            if snaps:
                log.info(f"Base model: {snaps[-1]}")
                return str(snaps[-1])
    log.info(f"Base model not cached; will download {MODEL_ID}")
    return MODEL_ID


def load_model_and_tokenizer(sft_adapter_path: str, rl_adapter_path: str):
    base_path = find_base_model()

    log.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        base_path, trust_remote_code=True, padding_side="left"
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    log.info("Loading base model in bf16 to CPU...")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_path, torch_dtype=torch.bfloat16, trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    log.info("Base model loaded.")

    log.info(f"Merging SFT adapter from {sft_adapter_path} ...")
    sft_peft = PeftModel.from_pretrained(base_model, sft_adapter_path, is_trainable=False)
    base_model = sft_peft.merge_and_unload()
    log.info("SFT adapter merged.")

    log.info(f"Merging RL v2 adapter from {rl_adapter_path} ...")
    rl_peft = PeftModel.from_pretrained(base_model, rl_adapter_path, is_trainable=False)
    base_model = rl_peft.merge_and_unload()
    log.info("RL v2 adapter merged.")

    log.info("Attaching fresh r=16 LoRA for RL v3 training...")
    lora_config = LoraConfig(
        r=16,
        lora_alpha=32,
        target_modules=["q_proj", "k_proj", "v_proj", "o_proj",
                        "gate_proj", "up_proj", "down_proj"],
        lora_dropout=0.05,
        bias="none",
        task_type="CAUSAL_LM",
    )
    model = get_peft_model(base_model, lora_config)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log.info(f"Trainable: {trainable:,} / {total:,} params ({100*trainable/total:.3f}%)")

    model.enable_input_require_grads()
    model.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={"use_reentrant": False}
    )
    log.info("Gradient checkpointing enabled.")

    log.info("Moving to cuda:0...")
    model = model.to("cuda:0")

    alloc = torch.cuda.memory_allocated() / 1e9
    total_vram = torch.cuda.get_device_properties(0).total_memory / 1e9
    log.info(f"cuda:0: {alloc:.1f} GB / {total_vram:.1f} GB ({total_vram-alloc:.1f} GB free)")
    return model, tokenizer


# ── Verilog extraction ────────────────────────────────────────────────────────

def extract_verilog(text):
    for pat in [
        r'```(?:verilog|systemverilog|sv)\n(.*?)```',
        r'```\n(.*?(?:module|endmodule).*?)```',
    ]:
        m = re.search(pat, text, re.DOTALL | re.IGNORECASE)
        if m:
            return m.group(1).strip()
    m = re.search(
        r'((?:^|\n)(?:`timescale\s+\S+|module\s+\w+).*?endmodule)', text, re.DOTALL
    )
    if m:
        return m.group(1).strip()
    return text.strip() if ("module" in text and "endmodule" in text) else text.strip()


# ── Reward ────────────────────────────────────────────────────────────────────

def iverilog_compile(code):
    with tempfile.TemporaryDirectory() as tmpdir:
        path = os.path.join(tmpdir, "design.sv")
        with open(path, "w") as f:
            f.write(code)
        try:
            r = subprocess.run(
                ["iverilog", "-g2012", "-o", "/dev/null", path],
                capture_output=True, text=True, timeout=30,
            )
            return r.returncode == 0, r.stderr.strip()
        except FileNotFoundError:
            return False, "iverilog not found"
        except subprocess.TimeoutExpired:
            return False, "timeout"


def compute_reward(completion: str, problem_id: str = None, bench_dir: str = None) -> float:
    """Hybrid iverilog + cocotb reward.

    When COCOTB_MODE is True and problem_id is given:
      hard iverilog fail → 0.0
      soft iverilog fail → 0.2
      clean compile + cocotb pass → 1.0
      clean compile + cocotb fail → 0.5
      clean compile + cocotb unavailable (no harness) → 1.0

    When COCOTB_MODE is False (fallback iverilog-only):
      hard fail → 0.0
      soft fail → 0.3
      clean compile → 1.0
    """
    global COCOTB_MODE

    low = completion.lower()
    if any(m in low for m in REFUSAL_MARKERS):
        return 0.0

    verilog = extract_verilog(completion)
    if "module" not in verilog or "endmodule" not in verilog:
        return 0.0

    ok, stderr = iverilog_compile(verilog)
    if ok:
        if COCOTB_MODE and problem_id and bench_dir:
            result = cocotb_test(problem_id, verilog, bench_dir)
            if result is True:
                return 1.0
            elif result is False:
                return 0.5
            else:
                # Harness not available for this problem → treat as clean compile
                return 1.0
        return 1.0

    sl = stderr.lower()
    if any(p.lower() in sl for p in HARD_FAIL_PATTERNS):
        return 0.0
    if any(p.lower() in sl for p in SOFT_FAIL_PATTERNS):
        return 0.2 if COCOTB_MODE else 0.3
    return 0.0


# ── Generation ────────────────────────────────────────────────────────────────

def build_prompt_text(spec, tokenizer):
    messages = [{"role": "user", "content": USER_TEMPLATE.format(spec=spec)}]
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )


def generate_completions(model, tokenizer, prompt_text, G, max_new_tokens, temperature):
    prompt_ids = tokenizer(prompt_text, return_tensors="pt").input_ids.to("cuda:0")
    prompt_len = prompt_ids.shape[-1]

    comp_ids_list = []
    comp_texts = []

    model.eval()
    with torch.no_grad():
        for _ in range(G):
            out = model.generate(
                input_ids=prompt_ids,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True,
                pad_token_id=tokenizer.eos_token_id,
            )
            cids = out[0][prompt_len:]
            comp_ids_list.append(cids)
            comp_texts.append(tokenizer.decode(cids, skip_special_tokens=True))
            torch.cuda.empty_cache()
    model.train()

    return prompt_ids, comp_ids_list, comp_texts


# ── GRPO loss ─────────────────────────────────────────────────────────────────

def compute_grpo_step(model, prompt_ids, comp_ids_list, advantages, optimizer):
    G = len(comp_ids_list)
    optimizer.zero_grad()
    step_loss = 0.0

    for comp_ids, adv in zip(comp_ids_list, advantages):
        adv_t = torch.tensor(adv, device="cuda:0", dtype=torch.float32)
        comp_len = comp_ids.shape[0]
        if comp_len == 0:
            continue

        full_ids = torch.cat(
            [prompt_ids, comp_ids.unsqueeze(0)], dim=-1
        )
        plen = prompt_ids.shape[-1]

        logits = model(input_ids=full_ids).logits

        shift_logits = logits[0, plen - 1 : -1, :].float()
        shift_labels = full_ids[0, plen:]

        log_probs = F.log_softmax(shift_logits, dim=-1)
        token_lp = log_probs.gather(-1, shift_labels.unsqueeze(-1)).squeeze(-1)
        mean_lp = token_lp.mean()

        loss = -adv_t * mean_lp / G
        loss.backward()
        step_loss += loss.item()

        del logits, shift_logits, log_probs, token_lp, full_ids
        torch.cuda.empty_cache()

    torch.nn.utils.clip_grad_norm_(
        [p for p in model.parameters() if p.requires_grad], max_norm=1.0
    )
    optimizer.step()
    torch.cuda.empty_cache()
    return step_loss


# ── Training loop ─────────────────────────────────────────────────────────────

def train(model, tokenizer, problems, args):
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    lora_params = [p for p in model.parameters() if p.requires_grad]
    log.info(f"Optimizer: AdamW, {sum(p.numel() for p in lora_params):,} params, lr={args.lr}")
    optimizer = torch.optim.AdamW(lora_params, lr=args.lr, weight_decay=0.01)

    total_steps = args.epochs * len(problems)
    if args.max_steps > 0:
        total_steps = min(total_steps, args.max_steps)
    warmup_steps = max(1, int(0.05 * total_steps))
    scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    log.info(
        f"Training: {args.epochs} epochs × {len(problems)} problems = "
        f"{args.epochs * len(problems)} steps (capped at {total_steps})"
    )

    global_step = 0
    for epoch in range(args.epochs):
        epoch_rewards = []
        epoch_loss = 0.0
        epoch_t0 = time.time()

        for prob_idx, prob in enumerate(problems):
            if args.max_steps > 0 and global_step >= args.max_steps:
                break

            pid = prob["id"]
            spec = prob["input"]["prompt"]
            prompt_text = build_prompt_text(spec, tokenizer)

            t0 = time.time()
            prompt_ids, comp_ids_list, comp_texts = generate_completions(
                model, tokenizer, prompt_text,
                G=args.num_generations,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature,
            )
            gen_time = time.time() - t0

            rewards = [
                compute_reward(c, problem_id=pid, bench_dir=args.bench_dir)
                for c in comp_texts
            ]
            epoch_rewards.extend(rewards)

            r_mean = sum(rewards) / len(rewards)
            r_std = math.sqrt(sum((r - r_mean) ** 2 for r in rewards) / len(rewards))
            if r_std > 1e-6:
                advantages = [(r - r_mean) / (r_std + 1e-8) for r in rewards]
            else:
                advantages = [0.0] * len(rewards)

            t1 = time.time()
            step_loss = compute_grpo_step(
                model, prompt_ids, comp_ids_list, advantages, optimizer
            )
            scheduler.step()
            train_time = time.time() - t1
            epoch_loss += step_loss
            global_step += 1

            lr_now = scheduler.get_last_lr()[0]
            log.info(
                f"[ep{epoch+1} step{global_step}/{total_steps}] {pid} | "
                f"rewards={[f'{r:.2f}' for r in rewards]} mean={r_mean:.2f} | "
                f"loss={step_loss:.4f} | lr={lr_now:.2e} | "
                f"gen={gen_time:.0f}s train={train_time:.1f}s"
            )

        # ── End of epoch ──────────────────────────────────────────────────────
        n_done = len(epoch_rewards)
        clean_rate = sum(1 for r in epoch_rewards if r >= 1.0) / max(n_done, 1)
        partial_rate = sum(1 for r in epoch_rewards if 0.0 < r < 1.0) / max(n_done, 1)
        log.info(
            f"=== Epoch {epoch+1} done | "
            f"mean_reward={sum(epoch_rewards)/max(n_done,1):.3f} | "
            f"clean={clean_rate:.1%} partial={partial_rate:.1%} | "
            f"loss={epoch_loss:.4f} | elapsed={time.time()-epoch_t0:.0f}s ==="
        )

        if not args.dry_run:
            ckpt = out_dir / f"epoch{epoch+1}"
            model.save_pretrained(str(ckpt))
            tokenizer.save_pretrained(str(ckpt))
            log.info(f"Epoch checkpoint saved: {ckpt}")

        if args.max_steps > 0 and global_step >= args.max_steps:
            log.info("Max steps reached — stopping early.")
            break

    log.info("Training complete.")


# ── R2 upload ─────────────────────────────────────────────────────────────────

def upload_to_r2(local_dir, r2_path):
    env = os.environ.copy()
    creds = Path("/home/noahsabb/.r2_creds")
    if creds.exists():
        for line in creds.read_text().splitlines():
            if "=" in line and not line.startswith("#"):
                k, _, v = line.partition("=")
                env.setdefault(k.strip(), v.strip())
    endpoint = env.get(
        "CLOUDFLARE_R2_ENDPOINT",
        "https://a5000aacae3e74e21534569c0bf2909b.r2.cloudflarestorage.com",
    )
    cmd = ["aws", "s3", "sync", local_dir, r2_path, "--endpoint-url", endpoint]
    log.info(f"Uploading {local_dir} → {r2_path}")
    r = subprocess.run(cmd, env=env, capture_output=True, text=True)
    if r.returncode != 0:
        log.warning(f"R2 upload failed: {r.stderr[:500]}")
    else:
        log.info("R2 upload complete.")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    global COCOTB_MODE

    args = parse_args()
    if args.dry_run:
        args.max_problems = args.max_problems or 5
        args.max_steps = 2 if args.max_steps < 0 else args.max_steps
        log.info(f"=== DRY RUN: {args.max_problems} problems, {args.max_steps} steps ===")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # ── Docker / cocotb availability check ────────────────────────────────────
    if not args.no_cocotb:
        docker_ok, docker_reason = check_docker_available(args.bench_dir)
        if docker_ok:
            COCOTB_MODE = True
            log.info(f"REWARD MODE: hybrid (iverilog + cocotb) — {docker_reason}")
            log.info("Reward scale: hard_fail=0.0 soft_fail=0.2 cocotb_fail=0.5 cocotb_pass=1.0")
        else:
            COCOTB_MODE = False
            log.warning(f"REWARD MODE: iverilog-only fallback — {docker_reason}")
            log.info("Reward scale: hard_fail=0.0 soft_fail=0.3 clean_compile=1.0")
    else:
        COCOTB_MODE = False
        log.info("REWARD MODE: iverilog-only (--no-cocotb flag set)")
        log.info("Reward scale: hard_fail=0.0 soft_fail=0.3 clean_compile=1.0")

    # ── Reward smoke test ─────────────────────────────────────────────────────
    log.info("Reward function smoke test...")
    r = compute_reward("```verilog\nmodule ok(input a, output b); assign b = a; endmodule\n```")
    assert r == 1.0, f"Clean Verilog should score 1.0, got {r}"
    r = compute_reward("I give up, this is too hard")
    assert r == 0.0, f"Refusal should score 0.0, got {r}"
    log.info("Reward smoke test passed.")

    data_path = find_data(args.data)
    problems = load_problems(data_path, args.max_problems)

    model, tokenizer = load_model_and_tokenizer(args.sft_adapter, args.adapter)

    train(model, tokenizer, problems, args)

    if args.dry_run:
        log.info(f"=== DRY RUN PASSED — reward_mode={'cocotb' if COCOTB_MODE else 'iverilog-only'} ===")
        log.info("Ready to submit: sbatch scripts/run_grpo_v3.sbatch")
        return

    log.info(f"Saving final adapter to {out_dir} ...")
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    log.info("Adapter saved.")

    if not args.no_r2_upload:
        adapter_name = Path(args.out).name
        upload_to_r2(str(out_dir), f"s3://spec2rtl-checkpoints/adapters/{adapter_name}/")


if __name__ == "__main__":
    main()
