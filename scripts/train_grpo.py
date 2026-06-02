#!/usr/bin/env python3
"""
GRPO reinforcement learning fine-tuning of Qwen2.5-Coder-32B-Instruct.

Starts from the existing SFT LoRA adapter and continues training it with
a custom GRPO loop using a tiered iverilog compilation reward.

TRL's GRPOTrainer is NOT used — it requires TRL ≥0.14 which conflicts with the
container's pinned transformers==4.46.0.  This script implements GRPO directly:
  1. For each problem, generate G completions (G=4) sequentially.
  2. Score each with iverilog (tiered: 1.0 / 0.3 / 0.0).
  3. Normalize rewards → advantages.
  4. Forward pass (with grad) for each completion → accumulate GRPO gradients.
  5. One AdamW step + LR scheduler step.

Since we do one gradient step per episode (K=1, on-policy), the importance-
sampling ratio is always 1.0 and the algorithm reduces to REINFORCE with
normalized baseline — a valid and stable choice at LR=5e-6 over 3 epochs.

Memory design (single H100 80 GB):
  - bf16 base model + LoRA: ~64 GB (bitsandbytes CUDA kernels broken in NGC 24.12)
  - No device_map: zero Accelerate dispatch hooks (avoids the 1 t/s throughput bug)
  - gradient_checkpointing: caps activation memory; only stores one layer at a time
  - G=4 completions generated sequentially, logprobs computed one-at-a-time

Reward tiers:
  1.0  —  clean iverilog compile (returncode 0)
  0.3  —  soft failure: wire/reg assignment, cast, constant-select errors
  0.0  —  hard failure: unknown module, severe syntax, no Verilog, refusal

Usage:
  # Full training run (3 epochs, 78 problems):
  python3 scripts/train_grpo.py \\
      --adapter /home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-35e941c1

  # Dry run (5 problems, 2 steps — verifies memory + reward):
  python3 scripts/train_grpo.py \\
      --adapter ... --dry-run --max-problems 5 --max-steps 2
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
from peft import PeftModel
from transformers import AutoModelForCausalLM, AutoTokenizer, get_cosine_schedule_with_warmup

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)

MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"
SHARED_CACHE = "/home/_shared/models"

USER_TEMPLATE = (
    "Generate synthesizable Verilog RTL for the following specification.\n\n"
    "## Specification\n{spec}"
)

# Errors that indicate structurally-correct Verilog with minor type/assignment issues.
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


# ── Args ─────────────────────────────────────────────────────────────────────

def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default=None,
                   help="Path to cid003_nonagentic.jsonl (auto-searched if omitted)")
    p.add_argument("--adapter", required=True,
                   help="Path to existing SFT LoRA adapter directory")
    p.add_argument("--out",
                   default="/home/noahsabb/checkpoints/spec2rtl/qwen32b-lora-rl-v1")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--lr", type=float, default=5e-6)
    p.add_argument("--max-new-tokens", type=int, default=2048)
    p.add_argument("--num-generations", type=int, default=4,
                   help="Completions per problem per step (G in GRPO)")
    p.add_argument("--temperature", type=float, default=0.9)
    p.add_argument("--epsilon", type=float, default=0.2,
                   help="PPO clip ratio (unused when K=1, kept for reference)")
    p.add_argument("--max-problems", type=int, default=None,
                   help="Cap dataset size (dry run)")
    p.add_argument("--max-steps", type=int, default=-1,
                   help="Cap total training steps, -1 = run all epochs")
    p.add_argument("--no-r2-upload", action="store_true")
    p.add_argument("--dry-run", action="store_true",
                   help="Quick validation: 5 problems, 2 steps, no checkpoint save")
    return p.parse_args()


# ── Data ─────────────────────────────────────────────────────────────────────

def find_data(explicit):
    if explicit and Path(explicit).exists():
        return explicit
    if explicit:
        log.warning(f"Specified path not found: {explicit} — searching defaults")
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


def load_model_and_tokenizer(adapter_path):
    base_path = find_base_model()

    log.info("Loading tokenizer...")
    tokenizer = AutoTokenizer.from_pretrained(
        base_path, trust_remote_code=True, padding_side="left"
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    # CPU load avoids device_map dispatch hooks (which cause ~1 t/s throughput).
    log.info("Loading base model in bf16 to CPU...")
    base_model = AutoModelForCausalLM.from_pretrained(
        base_path, torch_dtype=torch.bfloat16, trust_remote_code=True,
        low_cpu_mem_usage=True,
    )
    log.info("Base model loaded.")

    log.info(f"Loading LoRA adapter from {adapter_path} (is_trainable=True)...")
    model = PeftModel.from_pretrained(base_model, adapter_path, is_trainable=True)

    trainable = sum(p.numel() for p in model.parameters() if p.requires_grad)
    total = sum(p.numel() for p in model.parameters())
    log.info(f"Trainable: {trainable:,} / {total:,} params ({100*trainable/total:.3f}%)")

    # gradient_checkpointing with PeftModel requires input embeddings to have
    # requires_grad so the checkpoint segments' backward can propagate correctly.
    model.enable_input_require_grads()
    model.gradient_checkpointing_enable(
        gradient_checkpointing_kwargs={"use_reentrant": False}
    )
    log.info("Gradient checkpointing enabled (use_reentrant=False).")

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


def compute_reward(completion):
    low = completion.lower()
    if any(m in low for m in REFUSAL_MARKERS):
        return 0.0
    verilog = extract_verilog(completion)
    if "module" not in verilog or "endmodule" not in verilog:
        return 0.0
    ok, stderr = iverilog_compile(verilog)
    if ok:
        return 1.0
    sl = stderr.lower()
    if any(p.lower() in sl for p in HARD_FAIL_PATTERNS):
        return 0.0
    if any(p.lower() in sl for p in SOFT_FAIL_PATTERNS):
        return 0.3
    return 0.0


# ── Generation ────────────────────────────────────────────────────────────────

def build_prompt_text(spec, tokenizer):
    messages = [{"role": "user", "content": USER_TEMPLATE.format(spec=spec)}]
    return tokenizer.apply_chat_template(
        messages, tokenize=False, add_generation_prompt=True
    )


def generate_completions(model, tokenizer, prompt_text, G, max_new_tokens, temperature):
    """Generate G completions sequentially to minimise peak VRAM."""
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
    """
    Compute GRPO loss over G completions for one problem and do one optimizer step.

    K=1 on-policy update: old logprob == new logprob at step start, so ratio=1.0
    and clipping is inactive.  This reduces to REINFORCE with normalised baseline,
    which is well-suited to the small LR / few epochs regime here.

    Completions are processed one at a time with gradient accumulation to minimise
    peak activation memory (gradient checkpointing handles the rest).
    """
    G = len(comp_ids_list)
    optimizer.zero_grad()
    step_loss = 0.0

    for comp_ids, adv in zip(comp_ids_list, advantages):
        adv_t = torch.tensor(adv, device="cuda:0", dtype=torch.float32)
        comp_len = comp_ids.shape[0]
        if comp_len == 0:
            continue

        # Full sequence: [prompt_tokens | completion_tokens]
        full_ids = torch.cat(
            [prompt_ids, comp_ids.unsqueeze(0)], dim=-1
        )  # [1, prompt_len + comp_len]

        plen = prompt_ids.shape[-1]

        # Forward pass — gradient checkpointing stores only one layer's input at a time.
        logits = model(input_ids=full_ids).logits  # [1, seq_len, vocab]

        # Logits at positions [plen-1 : -1] predict completion tokens at [plen : end].
        shift_logits = logits[0, plen - 1 : -1, :].float()   # [comp_len, vocab]
        shift_labels = full_ids[0, plen:]                      # [comp_len]

        log_probs = F.log_softmax(shift_logits, dim=-1)
        token_lp = log_probs.gather(-1, shift_labels.unsqueeze(-1)).squeeze(-1)

        # Mean per-token log-prob normalises across completions of different lengths.
        mean_lp = token_lp.mean()

        # GRPO loss contribution from this completion (accumulated over G completions).
        loss = -adv_t * mean_lp / G
        loss.backward()
        step_loss += loss.item()

        # Free computation graph between completions.
        del logits, shift_logits, log_probs, token_lp, full_ids
        torch.cuda.empty_cache()

    torch.nn.utils.clip_grad_norm_(
        [p for p in model.parameters() if p.requires_grad], max_norm=1.0
    )
    optimizer.step()
    return step_loss


# ── Training loop ─────────────────────────────────────────────────────────────

def train(model, tokenizer, problems, args):
    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Optimizer on LoRA params only.
    lora_params = [p for p in model.parameters() if p.requires_grad]
    log.info(f"Optimizer: AdamW, {sum(p.numel() for p in lora_params):,} params, lr={args.lr}")
    optimizer = torch.optim.AdamW(lora_params, lr=args.lr, weight_decay=0.01)

    total_steps = args.epochs * len(problems)
    if args.max_steps > 0:
        total_steps = min(total_steps, args.max_steps)
    warmup_steps = max(1, int(0.05 * total_steps))
    scheduler = get_cosine_schedule_with_warmup(optimizer, warmup_steps, total_steps)

    log.info(f"Training: {args.epochs} epochs × {len(problems)} problems = "
             f"{args.epochs * len(problems)} steps (capped at {total_steps})")

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

            # ── Generate G completions ──────────────────────────────
            t0 = time.time()
            prompt_ids, comp_ids_list, comp_texts = generate_completions(
                model, tokenizer, prompt_text,
                G=args.num_generations,
                max_new_tokens=args.max_new_tokens,
                temperature=args.temperature,
            )
            gen_time = time.time() - t0

            # ── Score with iverilog ─────────────────────────────────
            rewards = [compute_reward(c) for c in comp_texts]
            epoch_rewards.extend(rewards)

            # ── Compute advantages (normalised rewards) ─────────────
            r_mean = sum(rewards) / len(rewards)
            r_std = math.sqrt(sum((r - r_mean) ** 2 for r in rewards) / len(rewards))
            if r_std > 1e-6:
                advantages = [(r - r_mean) / (r_std + 1e-8) for r in rewards]
            else:
                # All rewards identical → zero advantage → no update
                advantages = [0.0] * len(rewards)

            # ── GRPO gradient step ──────────────────────────────────
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
                f"rewards={[f'{r:.1f}' for r in rewards]} mean={r_mean:.2f} | "
                f"loss={step_loss:.4f} | lr={lr_now:.2e} | "
                f"gen={gen_time:.0f}s train={train_time:.1f}s"
            )

        # ── End of epoch ────────────────────────────────────────────
        n_done = len(epoch_rewards)
        pass_rate = sum(1 for r in epoch_rewards if r >= 1.0) / max(n_done, 1)
        soft_rate = sum(1 for r in epoch_rewards if r == 0.3) / max(n_done, 1)
        log.info(
            f"=== Epoch {epoch+1} done | "
            f"mean_reward={sum(epoch_rewards)/max(n_done,1):.3f} | "
            f"clean_compile={pass_rate:.1%} | soft={soft_rate:.1%} | "
            f"loss={epoch_loss:.4f} | elapsed={time.time()-epoch_t0:.0f}s ==="
        )

        if not args.dry_run:
            ckpt = out_dir / f"checkpoint-epoch{epoch+1}"
            model.save_pretrained(str(ckpt))
            tokenizer.save_pretrained(str(ckpt))
            log.info(f"Checkpoint saved: {ckpt}")

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
    args = parse_args()
    if args.dry_run:
        args.max_problems = args.max_problems or 5
        args.max_steps = 2 if args.max_steps < 0 else args.max_steps
        log.info(f"=== DRY RUN: {args.max_problems} problems, {args.max_steps} steps ===")

    out_dir = Path(args.out)
    out_dir.mkdir(parents=True, exist_ok=True)

    # Sanity-check reward function before loading the 32B model.
    log.info("Reward function smoke test...")
    r = compute_reward("```verilog\nmodule ok(input a, output b); assign b = a; endmodule\n```")
    assert r == 1.0, f"Clean Verilog should score 1.0, got {r}"
    r = compute_reward("I give up, this is too hard")
    assert r == 0.0, f"Refusal should score 0.0, got {r}"
    log.info("Reward smoke test passed.")

    data_path = find_data(args.data)
    problems = load_problems(data_path, args.max_problems)

    model, tokenizer = load_model_and_tokenizer(args.adapter)

    train(model, tokenizer, problems, args)

    if args.dry_run:
        log.info("=== DRY RUN PASSED — memory OK, reward OK, TRL not needed ===")
        log.info("Ready to submit: sbatch scripts/run_grpo.sbatch")
        return

    # Save final adapter.
    log.info(f"Saving final adapter to {out_dir} ...")
    model.save_pretrained(str(out_dir))
    tokenizer.save_pretrained(str(out_dir))
    log.info("Adapter saved.")

    if not args.no_r2_upload:
        upload_to_r2(str(out_dir), "s3://spec2rtl-checkpoints/adapters/qwen32b-lora-rl-v1/")


if __name__ == "__main__":
    main()
