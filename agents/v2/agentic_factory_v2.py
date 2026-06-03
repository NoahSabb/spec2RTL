"""
Agentic factory v2 — drop-in replacement for agentic_claude_factory.py.

Uses agentic_loop_v2 (better error parsing, targeted repair, 5-iter cap, JSON logs).
Generator model is Claude Sonnet 4.6 locally; swap claude_gen_factory for a
Qwen vLLM factory when running on the cluster.

Usage with benchmark runner:
    OSS_SIM_IMAGE=cvdp-sim:latest python run_benchmark.py \
        -f data/cid003_nonagentic.jsonl -l \
        -m claude-agentic-v2 \
        -c agents/v2/agentic_factory_v2.py \
        -p work_agentic_v2_test -t 1

Environment:
    ANTHROPIC_API_KEY       — required
    AGENTIC_V2_LOG          — iteration log path (default: logs/agentic_v2_run.jsonl)
    AGENTIC_V2_MAX_ITER     — max iterations per problem (default: 5)
"""

import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

import anthropic

_here = Path(__file__).parent
_root = _here.parent.parent
sys.path.insert(0, str(_here))
sys.path.insert(0, str(_root / "cvdp_benchmark"))

from agentic_loop_v2 import run_agentic_loop_v2
from claude_gen_factory import ClaudeGenerator

try:
    from src.llm_lib.model_factory import ModelFactory
except ImportError:
    class ModelFactory:
        def __init__(self): pass

logging.basicConfig(level=logging.INFO)
log = logging.getLogger(__name__)

_LOG_FILE = os.environ.get("AGENTIC_V2_LOG", str(_root / "logs/agentic_v2_run.jsonl"))
_MAX_ITER = int(os.environ.get("AGENTIC_V2_MAX_ITER", "5"))


class AgenticV2Instance:
    """Model instance wrapping agentic_loop_v2."""

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: Optional[str] = None):
        self.model = model
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.generator = ClaudeGenerator(model=model, api_key=key)
        self.client = anthropic.Anthropic(api_key=key)
        os.makedirs(os.path.dirname(_LOG_FILE), exist_ok=True)

    def prompt(self, spec: str, schema=None, prompt_log: str = "",
               files=None, timeout: int = 120, category: Optional[int] = None) -> Any:

        # Resolve harness directory from prompt_log path (same logic as v1)
        harness_dir = None
        rtl_filename = None
        problem_id = "unknown"

        if prompt_log:
            parts = prompt_log.replace("\\", "/").split("/")
            problem_name = next((p for p in parts if p.startswith("cvdp_")), None)
            prefix = parts[0] if parts else None
            if problem_name and prefix:
                problem_id = problem_name
                base = _root / "cvdp_benchmark" / prefix / problem_name / "harness" / "1"
                base = base.resolve()
                if base.is_dir():
                    harness_dir = str(base)
                    env_path = base / "src" / ".env"
                    if env_path.exists():
                        for line in env_path.read_text().splitlines():
                            if line.startswith("VERILOG_SOURCES"):
                                rtl_filename = line.split("=")[-1].strip().split("/")[-1]
                                break

        log.info(f"AgenticV2 prompt: problem={problem_id} harness={harness_dir} rtl={rtl_filename}")

        result = run_agentic_loop_v2(
            generator=self.generator,
            client=self.client,
            spec=spec,
            max_iterations=_MAX_ITER,
            harness_dir=harness_dir,
            rtl_filename=rtl_filename,
            initial_verilog=None,  # generate fresh when called via benchmark runner
            log_file=_LOG_FILE,
            problem_id=problem_id,
        )

        verilog = result.get("verilog", "")
        log.info(f"[{problem_id}] Loop done — passed={result['passed']} iter={result['iterations']}")

        if files and len(files) == 1:
            return ({"direct_text": verilog}, True)
        return verilog


class CustomModelFactory(ModelFactory):
    def __init__(self):
        super().__init__()

    def create_model(self, model_name: str, context: Any = None,
                     key: Optional[str] = None, **kwargs) -> Any:
        return AgenticV2Instance(model=model_name or "claude-sonnet-4-6", api_key=key)
