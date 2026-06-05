#!/usr/bin/env python3
"""Spec2RTL Web UI — FastAPI backend with SSE streaming."""

import json
import os
from pathlib import Path

import anthropic
from fastapi import FastAPI, Request
from fastapi.responses import StreamingResponse
from fastapi.staticfiles import StaticFiles
from openai import AsyncOpenAI


def _load_env():
    for candidate in [
        Path(__file__).parent.parent / ".env",
        Path(__file__).parent / ".env",
    ]:
        if candidate.exists():
            for line in candidate.read_text().splitlines():
                line = line.strip()
                if line and not line.startswith("#") and "=" in line:
                    k, v = line.split("=", 1)
                    os.environ.setdefault(k.strip(), v.strip().strip('"').strip("'"))
            break


_load_env()

app = FastAPI(title="Spec2RTL")

# ── Prompts (from scripts/run_agentic_v11.py) ─────────────────────────────────

SPEC_CLARIFY_SYSTEM = """You are an expert RTL hardware engineer.
Convert this natural-language specification into a precise, unambiguous implementation contract
that another engineer will use to write Verilog RTL from scratch.

The implementation contract must include:
1. **Module interface**: exact port names, widths, directions (from the spec or testbench)
2. **Functional behavior**: precise description of what the module computes, with concrete
   examples (inputs → expected outputs)
3. **Timing model**: which outputs are registered (clocked) vs combinational; when outputs
   are valid relative to inputs; reset behavior
4. **Edge cases**: what happens at boundaries (overflow, empty/full, zero inputs, etc.)
5. **Algorithm**: the specific algorithm to implement (not just what it does but HOW)

Be concrete and specific. Replace vague language ("the module processes...") with exact
statements ("on each rising clock edge when enable=1, output = (A+B)>>1, registered").
"""

GENERATOR_SYSTEM = (
    "You are an expert RTL hardware engineer. "
    "Output ONLY the complete, synthesizable Verilog module inside a ```verilog ... ``` block. "
    "Do NOT change any port names or the module name unless explicitly told to. "
    "Do NOT add explanations or comments outside the code block. "
    "Use only synthesizable constructs (no initial blocks with delays, no $display, no fork/join)."
)

CLAUDE_MODEL = "claude-sonnet-4-6"


def _build_clarify_prompt(spec: str) -> str:
    return (
        "Convert this RTL specification into an explicit implementation contract.\n\n"
        f"## Original Specification\n{spec}\n\n"
        "Write the implementation contract below. Focus on being precise and unambiguous."
    )


def _build_generate_prompt(clarified_spec: str) -> str:
    return (
        f"## Implementation Contract\n{clarified_spec}\n\n"
        "Generate complete synthesizable Verilog RTL. "
        "Return ONLY the Verilog in a ```verilog ... ``` block."
    )


def _sse(data: dict) -> str:
    return f"data: {json.dumps(data)}\n\n"


# ── SSE generator ──────────────────────────────────────────────────────────────

async def generate_stream(spec: str, model: str):
    api_key = os.environ.get("ANTHROPIC_API_KEY", "")

    # Step 1: Spec clarification (always uses Claude if key available)
    clarified_spec = spec
    if api_key:
        yield _sse({"type": "status", "message": "Clarifying specification with Claude Sonnet…"})
        try:
            aclient = anthropic.AsyncAnthropic(api_key=api_key)
            resp = await aclient.messages.create(
                model=CLAUDE_MODEL,
                max_tokens=800,
                system=SPEC_CLARIFY_SYSTEM,
                messages=[{"role": "user", "content": _build_clarify_prompt(spec)}],
            )
            clarified_spec = resp.content[0].text.strip()
            yield _sse({"type": "clarified", "clarified_spec": clarified_spec})
        except Exception as exc:
            yield _sse({"type": "warning", "message": f"Clarification skipped: {exc}"})
    else:
        yield _sse({"type": "warning", "message": "No ANTHROPIC_API_KEY — skipping spec clarification."})

    # Step 2: RTL generation
    model_label = "Claude Sonnet" if model == "claude" else "Qwen RL v2"
    yield _sse({"type": "status", "message": f"Generating RTL with {model_label}…"})

    generate_prompt = _build_generate_prompt(clarified_spec)
    full_text = ""

    try:
        if model == "claude":
            if not api_key:
                yield _sse({"type": "error", "message": "ANTHROPIC_API_KEY is not set. Add it to your .env file."})
                return
            aclient = anthropic.AsyncAnthropic(api_key=api_key)
            async with aclient.messages.stream(
                model=CLAUDE_MODEL,
                max_tokens=3000,
                system=GENERATOR_SYSTEM,
                messages=[{"role": "user", "content": generate_prompt}],
            ) as stream:
                async for chunk in stream.text_stream:
                    full_text += chunk
                    yield _sse({"type": "chunk", "text": chunk})

        elif model == "qwen":
            endpoint = os.environ.get("VLLM_ENDPOINT", "http://localhost:8000/v1")
            qclient = AsyncOpenAI(base_url=endpoint, api_key="token-abc123")
            # Discover model id from the endpoint
            model_id = "default"
            try:
                models = await qclient.models.list()
                if models.data:
                    model_id = models.data[0].id
            except Exception:
                pass

            stream = await qclient.chat.completions.create(
                model=model_id,
                messages=[
                    {"role": "system", "content": GENERATOR_SYSTEM},
                    {"role": "user", "content": generate_prompt},
                ],
                max_tokens=3000,
                temperature=0.3,
                stream=True,
            )
            async for chunk in stream:
                delta = chunk.choices[0].delta.content or ""
                if delta:
                    full_text += delta
                    yield _sse({"type": "chunk", "text": delta})

        yield _sse({"type": "done", "full_text": full_text})

    except Exception as exc:
        yield _sse({"type": "error", "message": str(exc)})


# ── Routes ─────────────────────────────────────────────────────────────────────

@app.post("/api/generate")
async def generate_endpoint(request: Request):
    body = await request.json()
    spec = body.get("spec", "").strip()
    model = body.get("model", "claude")

    if not spec:
        return {"error": "No spec provided"}

    return StreamingResponse(
        generate_stream(spec, model),
        media_type="text/event-stream",
        headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"},
    )


@app.get("/api/health")
async def health():
    return {
        "status": "ok",
        "anthropic_key": bool(os.environ.get("ANTHROPIC_API_KEY")),
        "vllm_endpoint": os.environ.get("VLLM_ENDPOINT", "http://localhost:8000/v1"),
    }


# Serve frontend — must be mounted last
app.mount("/", StaticFiles(directory=str(Path(__file__).parent / "static"), html=True), name="static")
