"""
Factory that serves pre-generated RTL from disk instead of calling a model.
Implements the CustomModelFactory interface required by the CVDP benchmark.

Usage:
    python run_benchmark.py \
        -f ../data/cid003_nonagentic.jsonl \
        -l -m qwen32b-lora \
        -c ../agents/pregenerated_factory.py \
        -p work_qwen32b_lora_raw \
        -t 4

Environment:
    RTL_DIR   — directory containing {problem_id}.sv files
                default: ~/Downloads/cid003_eval_results/rtl
    DATA_FILE — path to cid003_nonagentic.jsonl for spec→id mapping
"""

import json
import logging
import os
import sys
from pathlib import Path
from typing import Any, Optional

# Add benchmark src to path (needed when run via run_benchmark.py)
_this_dir = Path(__file__).parent
_bench_dir = _this_dir.parent / "cvdp_benchmark"
if str(_bench_dir) not in sys.path:
    sys.path.insert(0, str(_bench_dir))

from src.llm_lib.model_factory import ModelFactory

log = logging.getLogger(__name__)

_RTL_DIR = Path(
    os.environ.get(
        "RTL_DIR",
        os.path.expanduser("~/Downloads/cid003_eval_results/rtl"),
    )
)

_DATA_FILE = Path(
    os.environ.get(
        "DATA_FILE",
        str(_this_dir.parent / "data" / "cid003_nonagentic.jsonl"),
    )
)

# Build spec-text → problem-id lookup at import time
_spec_to_id: dict[str, str] = {}
try:
    with open(_DATA_FILE) as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            d = json.loads(line)
            _spec_to_id[d["input"]["prompt"]] = d["id"]
    log.info(f"[pregenerated] Loaded {len(_spec_to_id)} spec→id mappings from {_DATA_FILE}")
except Exception as e:
    log.warning(f"[pregenerated] Could not load data file {_DATA_FILE}: {e}")


class PregeneratedInstance:
    """Model instance that reads RTL from disk instead of calling a model."""

    def __init__(self, rtl_dir: Path, spec_to_id: dict):
        self.rtl_dir = rtl_dir
        self.spec_to_id = spec_to_id

    def prompt(self, spec: str, schema=None, prompt_log: str = "", **kwargs):
        # The benchmark builds the prompt as:
        #   "\nProvide me one answer for this request: {raw_spec}\n"
        #   "Please provide your response as plain text...\n"  (or similar)
        # Strategy: try exact match first, then substring search over known specs.
        problem_id = self.spec_to_id.get(spec)
        if not problem_id:
            # Substring search: find which known spec appears in the incoming prompt
            for known_spec, pid in self.spec_to_id.items():
                if known_spec in spec:
                    problem_id = pid
                    break

        if not problem_id:
            log.warning("[pregenerated] No problem ID found for spec (first 80 chars): %s", spec[:80])
            return ({"direct_text": "// pregenerated_factory: spec not matched\n"}, True)

        for ext in (".sv", ".v"):
            rtl_file = self.rtl_dir / f"{problem_id}{ext}"
            if rtl_file.exists():
                verilog = rtl_file.read_text()
                log.info("[pregenerated] Serving %s (%d chars)", problem_id, len(verilog))
                return ({"direct_text": verilog}, True)

        log.warning("[pregenerated] No RTL file found for %s in %s", problem_id, self.rtl_dir)
        return ({"direct_text": f"// pregenerated_factory: no file for {problem_id}\n"}, True)


class CustomModelFactory(ModelFactory):
    def __init__(self):
        super().__init__()

    def create_model(self, model_name: str, context: Any = None,
                     key: Optional[str] = None, **kwargs) -> Any:
        log.info("[pregenerated] Creating model instance (rtl_dir=%s)", _RTL_DIR)
        return PregeneratedInstance(rtl_dir=_RTL_DIR, spec_to_id=_spec_to_id)
