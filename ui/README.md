# Spec2RTL Web UI

A chat interface for generating synthesizable Verilog RTL from natural-language hardware specifications. Supports two backends — Claude Sonnet (cloud) and a locally-served Qwen 32B RL fine-tune.

## Quick start

```bash
cd ui
pip install -r requirements.txt
# copy and fill the env file (or use the repo root .env)
cp .env.example .env
uvicorn app:app --reload --port 7860
```

Open http://localhost:7860.

The `.env` at the **repo root** is also loaded automatically, so if you already have `ANTHROPIC_API_KEY` there you're good.

---

## Configuration

| Variable | Default | Description |
|---|---|---|
| `ANTHROPIC_API_KEY` | — | Required for Claude Sonnet backend and spec clarification |
| `VLLM_ENDPOINT` | `http://localhost:8000/v1` | OpenAI-compatible endpoint for the Qwen model |

---

## Running the Qwen RL v2 model locally

The fine-tuned model is [`Noahsabb/spec2rtl-qwen32b-lora-rl-v2`](https://huggingface.co/Noahsabb/spec2rtl-qwen32b-lora-rl-v2) — a LoRA adapter on Qwen2.5-32B-Instruct trained with GRPO on the CVDP RTL benchmark.

### 1 · Pull the adapter from HuggingFace

```bash
pip install huggingface_hub
huggingface-cli download Noahsabb/spec2rtl-qwen32b-lora-rl-v2 \
    --local-dir ~/models/spec2rtl-qwen32b-lora-rl-v2
```

Or inside a Python script:

```python
from huggingface_hub import snapshot_download
snapshot_download(
    repo_id="Noahsabb/spec2rtl-qwen32b-lora-rl-v2",
    local_dir="~/models/spec2rtl-qwen32b-lora-rl-v2",
)
```

### 2 · Merge the LoRA weights (recommended for serving)

```bash
pip install peft transformers
python - <<'EOF'
from peft import AutoPeftModelForCausalLM
import torch

model = AutoPeftModelForCausalLM.from_pretrained(
    "~/models/spec2rtl-qwen32b-lora-rl-v2",
    torch_dtype=torch.bfloat16,
    device_map="auto",
)
merged = model.merge_and_unload()
merged.save_pretrained("~/models/spec2rtl-qwen32b-merged")
EOF
```

### 3 · Serve with vLLM

```bash
pip install vllm

python -m vllm.entrypoints.openai.api_server \
    --model ~/models/spec2rtl-qwen32b-merged \
    --dtype bfloat16 \
    --tensor-parallel-size 2 \      # adjust to GPU count
    --max-model-len 8192 \
    --port 8000
```

For 4-bit quantized inference on fewer GPUs:

```bash
python -m vllm.entrypoints.openai.api_server \
    --model ~/models/spec2rtl-qwen32b-merged \
    --quantization awq \
    --dtype auto \
    --port 8000
```

Once the server is running, set `VLLM_ENDPOINT=http://localhost:8000/v1` and select **Qwen RL v2 (Local)** in the UI toggle.

### Running on the SLURM cluster

```bash
#!/bin/bash
#SBATCH --partition=small
#SBATCH --gres=gpu:2
#SBATCH --cpus-per-task=16
#SBATCH --time=04:00:00
#SBATCH --job-name=spec2rtl-serve

srun --container-image='nvcr.io#nvidia/pytorch:24.12-py3' \
     --cpus-per-task=16 \
  bash -c "
    pip install -q --no-deps --break-system-packages vllm &&
    python3 -m vllm.entrypoints.openai.api_server \
      --model /home/noahsabb/models/spec2rtl-qwen32b-merged \
      --dtype bfloat16 \
      --tensor-parallel-size 2 \
      --port 8000
  "
```

Then port-forward to your laptop:

```bash
kubectl port-forward -n slurm <your-login-pod> 8000:8000 -c login
```

---

## How it works

1. **Spec clarification** — Claude Sonnet rewrites the free-form spec as an explicit implementation contract (exact I/O, timing, algorithm). Always uses Claude; skipped gracefully if no API key.
2. **RTL generation** — The selected model generates Verilog from the clarified spec using the same system prompt as `scripts/run_agentic_v11.py`.
3. **Block diagram** — The returned Verilog is parsed client-side (regex) and rendered as an SVG showing module name, input/output ports with bit widths, parameters, internal signals, and submodule instances.

---

## Development

```bash
uvicorn app:app --reload --port 7860
```

The backend is a single FastAPI file (`app.py`). The frontend is a single static HTML file (`static/index.html`) with vanilla JS and inline CSS — no build step.
