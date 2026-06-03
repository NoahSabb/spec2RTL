"""
Generator factory that uses Claude Sonnet 4.6 for RTL generation.
Used as a stand-in for local testing (Qwen RL v2 runs on the cluster).
"""

import os
import sys
import logging
from typing import Any, Optional

import anthropic

log = logging.getLogger(__name__)


class ClaudeGenerator:
    """Thin wrapper that calls Claude Sonnet for Verilog generation."""

    SYSTEM = (
        "You are an expert RTL hardware engineer. "
        "When asked to generate or fix Verilog/SystemVerilog, output ONLY the "
        "complete module code inside a single ```verilog ... ``` block. "
        "No explanation before or after the code block."
    )

    def __init__(self, model: str = "claude-sonnet-4-6", api_key: Optional[str] = None):
        key = api_key or os.environ.get("ANTHROPIC_API_KEY")
        if not key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        self.client = anthropic.Anthropic(api_key=key)
        self.model = model

    def prompt(self, text: str, schema=None, prompt_log: str = "",
               files=None, timeout: int = 120, category: Optional[int] = None) -> Any:
        response = self.client.messages.create(
            model=self.model,
            system=self.SYSTEM,
            max_tokens=4096,
            messages=[{"role": "user", "content": text}],
        )
        content = response.content[0].text.strip()
        # Return in the same format the loop expects
        if files and len(files) == 1:
            return ({"direct_text": content}, True)
        return content
