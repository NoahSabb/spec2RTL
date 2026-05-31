#!/usr/bin/env python3
"""
QLoRA fine-tuning of Qwen2.5-Coder-32B-Instruct on spec-to-RTL data.

Expected layout on cluster:
  /home/noahsabb/data/final_finetune.jsonl   — prepared training data
  /home/noahsabb/spec2rtl/                   — this repo
  /home/_shared/models/Qwen/                 — shared HF cache (checked first)

Outputs:
  /home/noahsabb/checkpoints/spec2rtl-<run_id>/   — LoRA adapter + tokenizer
  Uploads final adapter to R2 bucket spec2rtl-checkpoints/adapters/<run_id>/

Run via sbatch train_qwen.sbatch (sets up environment first).
"""

import argparse
import json
import logging
import os
import subprocess
import sys
from pathlib import Path

import torch
from datasets import Dataset
from peft import LoraConfig, TaskType, get_peft_model, prepare_model_for_kbit_training
from transformers import (
    AutoModelForCausalLM,
    AutoTokenizer,
    BitsAndBytesConfig,
    TrainingArguments,
)
from trl import SFTConfig, SFTTrainer, DataCollatorForCompletionOnlyLM

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[logging.StreamHandler(sys.stdout)],
)
log = logging.getLogger(__name__)


# ── Config ───────────────────────────────────────────────────────────────────

MODEL_ID = "Qwen/Qwen2.5-Coder-32B-Instruct"
SHARED_CACHE = "/home/_shared/models"
MAX_SEQ_LEN = 4096

LORA_R = 32
LORA_ALPHA = 64
LORA_DROPOUT = 0.05
# All linear projections — maximizes representational capacity per LoRA param
LORA_TARGET_MODULES = [
    "q_proj", "k_proj", "v_proj", "o_proj",
    "gate_proj", "up_proj", "down_proj",
]


def parse_args():
    p = argparse.ArgumentParser()
    p.add_argument("--data", default="/home/noahsabb/data/final_finetune.jsonl")
    p.add_argument("--out", default="/home/noahsabb/checkpoints/spec2rtl")
    p.add_argument("--epochs", type=int, default=3)
    p.add_argument("--batch-size", type=int, default=2, help="per-device batch size")
    p.add_argument("--grad-accum", type=int, default=8)
    p.add_argument("--lr", type=float, default=2e-4)
    p.add_argument("--warmup-ratio", type=float, default=0.03)
    p.add_argument("--run-id", default=None, help="W&B / checkpoint name suffix")
    p.add_argument("--max-samples", type=int, default=None, help="cap dataset for debugging")
    p.add_argument("--no-r2-upload", action="store_true")
    return p.parse_args()


# ── Data ─────────────────────────────────────────────────────────────────────

def load_data(path: str, tokenizer, max_samples=None) -> Dataset:
    records = []
    with open(path) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            obj = json.loads(line)
            records.append(obj)
            if max_samples and len(records) >= max_samples:
                break

    log.info(f"Loaded {len(records)} raw samples from {path}")

    # Apply chat template to each message list → single formatted string
    texts = []
    skipped = 0
    for rec in records:
        msgs = rec.get("messages", [])
        if not msgs:
            skipped += 1
            continue
        try:
            text = tokenizer.apply_chat_template(
                msgs,
                tokenize=False,
                add_generation_prompt=False,
            )
        except Exception:
            skipped += 1
            continue
        # Length filter — drop samples that won't fit in context
        toks = tokenizer(text, return_length=True, truncation=False)["length"][0]
        if toks > MAX_SEQ_LEN:
            skipped += 1
            continue
        texts.append(text)

    log.info(f"Formatted {len(texts)} samples ({skipped} skipped)")
    return Dataset.from_dict({"text": texts})


# ── Model ─────────────────────────────────────────────────────────────────────

def find_model_path() -> str:
    """
    Check shared HF hub cache first (structured as hub/models--Qwen--...),
    then fall back to the HuggingFace Hub download (uses HF_HOME env var).
    """
    # HuggingFace hub cache names like: models--Qwen--Qwen2.5-Coder-32B-Instruct
    cache_name = "models--" + MODEL_ID.replace("/", "--")
    shared_hub = os.path.join(SHARED_CACHE, "hub", cache_name)
    if os.path.isdir(shared_hub):
        log.info(f"Model found in shared cache: {shared_hub}")
        # Return the snapshots dir's latest snapshot
        snapshots = sorted((Path(shared_hub) / "snapshots").iterdir())
        if snapshots:
            return str(snapshots[-1])
    log.info(f"Model not in shared cache; will download {MODEL_ID}")
    return MODEL_ID


def build_model_and_tokenizer(run_id: str):
    model_path = find_model_path()

    tokenizer = AutoTokenizer.from_pretrained(
        model_path,
        trust_remote_code=True,
        padding_side="right",  # SFT needs right-padding
    )
    if tokenizer.pad_token is None:
        tokenizer.pad_token = tokenizer.eos_token

    bnb_config = BitsAndBytesConfig(
        load_in_4bit=True,
        bnb_4bit_quant_type="nf4",
        bnb_4bit_use_double_quant=True,  # saves ~0.4 bits/param extra
        bnb_4bit_compute_dtype=torch.bfloat16,
    )

    # With DDP each rank gets device_map={"": local_rank} so the 4-bit model
    # stays on one GPU and DDP syncs only LoRA gradients.
    local_rank = int(os.environ.get("LOCAL_RANK", 0))
    try:
        import flash_attn  # noqa: F401
        from flash_attn.flash_attn_interface import flash_attn_func  # noqa: F401
        attn_impl = "flash_attention_2"
        log.info("Flash Attention 2 available — using it")
    except (ImportError, RuntimeError, OSError):
        attn_impl = "sdpa"
        log.info("Flash Attention 2 not found or incompatible — falling back to sdpa")

    model = AutoModelForCausalLM.from_pretrained(
        model_path,
        quantization_config=bnb_config,
        device_map={"": local_rank},
        attn_implementation=attn_impl,
        torch_dtype=torch.bfloat16,
        trust_remote_code=True,
    )
    model = prepare_model_for_kbit_training(model, use_gradient_checkpointing=True)

    lora_cfg = LoraConfig(
        task_type=TaskType.CAUSAL_LM,
        r=LORA_R,
        lora_alpha=LORA_ALPHA,
        lora_dropout=LORA_DROPOUT,
        target_modules=LORA_TARGET_MODULES,
        bias="none",
    )
    model = get_peft_model(model, lora_cfg)

    trainable, total = model.get_nb_trainable_parameters()
    log.info(f"Trainable params: {trainable:,} / {total:,} ({100*trainable/total:.2f}%)")
    return model, tokenizer


# ── Upload to R2 ──────────────────────────────────────────────────────────────

def upload_to_r2(local_dir: str, run_id: str):
    bucket = os.environ.get("CLOUDFLARE_R2_BUCKET", "spec2rtl-checkpoints")
    endpoint = os.environ.get("CLOUDFLARE_R2_ENDPOINT", "")
    if not endpoint:
        log.warning("CLOUDFLARE_R2_ENDPOINT not set — skipping R2 upload")
        return

    dest = f"s3://{bucket}/adapters/{run_id}/"
    cmd = [
        "aws", "s3", "sync", local_dir, dest,
        "--endpoint-url", endpoint,
        "--no-progress",
    ]
    log.info(f"Uploading {local_dir} → {dest}")
    result = subprocess.run(cmd, capture_output=True, text=True)
    if result.returncode != 0:
        log.error(f"R2 upload failed: {result.stderr}")
    else:
        log.info("R2 upload complete")


# ── Main ──────────────────────────────────────────────────────────────────────

def main():
    args = parse_args()

    import uuid
    run_id = args.run_id or f"qwen32b-lora-{uuid.uuid4().hex[:8]}"
    out_dir = os.path.join(args.out, run_id)
    Path(out_dir).mkdir(parents=True, exist_ok=True)
    log.info(f"Run ID: {run_id}  |  Output: {out_dir}")

    model, tokenizer = build_model_and_tokenizer(run_id)
    dataset = load_data(args.data, tokenizer, max_samples=args.max_samples)

    # 95/5 train/eval split for loss tracking
    splits = dataset.train_test_split(test_size=0.05, seed=42)

    # Completion-only loss: only backprop on the assistant's RTL output,
    # not on the system/user spec prompt. This focuses gradient signal on
    # what we actually care about and prevents the model from memorizing prompts.
    # Qwen2.5 chat format puts "<|im_start|>assistant\n" before the response.
    response_template = "<|im_start|>assistant\n"
    collator = DataCollatorForCompletionOnlyLM(
        response_template=response_template,
        tokenizer=tokenizer,
    )

    sft_config = SFTConfig(
        output_dir=out_dir,
        num_train_epochs=args.epochs,
        per_device_train_batch_size=args.batch_size,
        per_device_eval_batch_size=args.batch_size,
        gradient_accumulation_steps=args.grad_accum,
        gradient_checkpointing=True,
        gradient_checkpointing_kwargs={"use_reentrant": False},
        optim="paged_adamw_8bit",
        learning_rate=args.lr,
        lr_scheduler_type="cosine",
        warmup_ratio=args.warmup_ratio,
        weight_decay=0.01,
        bf16=True,
        max_seq_length=MAX_SEQ_LEN,
        dataset_text_field="text",
        packing=False,                      # must be False with DataCollatorForCompletionOnlyLM
        eval_strategy="epoch",
        save_strategy="epoch",
        save_total_limit=3,
        load_best_model_at_end=False,
        logging_steps=10,
        report_to="none",
        dataloader_num_workers=4,
        group_by_length=True,               # group by length to minimize padding (replaces packing)
        ddp_find_unused_parameters=False,
    )

    # Enable wandb if key present
    if os.environ.get("WANDB_API_KEY"):
        import wandb
        wandb.init(project="spec2rtl", name=run_id, config=vars(args))
        sft_config.report_to = "wandb"

    trainer = SFTTrainer(
        model=model,
        tokenizer=tokenizer,
        train_dataset=splits["train"],
        eval_dataset=splits["test"],
        data_collator=collator,
        args=sft_config,
    )

    log.info("Starting training...")
    trainer.train()

    # Save final LoRA adapter
    log.info(f"Saving adapter to {out_dir}")
    trainer.model.save_pretrained(out_dir)
    tokenizer.save_pretrained(out_dir)

    # Write a small metadata file
    meta = {
        "run_id": run_id,
        "base_model": MODEL_ID,
        "lora_r": LORA_R,
        "lora_alpha": LORA_ALPHA,
        "target_modules": LORA_TARGET_MODULES,
        "epochs": args.epochs,
        "lr": args.lr,
        "n_train": len(splits["train"]),
        "n_eval": len(splits["test"]),
    }
    with open(os.path.join(out_dir, "training_meta.json"), "w") as f:
        json.dump(meta, f, indent=2)

    # Upload to R2 (only from rank 0)
    if not args.no_r2_upload and int(os.environ.get("RANK", 0)) == 0:
        upload_to_r2(out_dir, run_id)

    log.info("Done.")


if __name__ == "__main__":
    main()
