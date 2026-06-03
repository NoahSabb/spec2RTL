import os
import sys
import logging
from typing import Optional, Any

import anthropic
from src.config_manager import config

sys.path.append(os.path.dirname(os.path.abspath(__file__)))
from agentic_loop_v1 import run_parallel, extract_verilog

from src.llm_lib.model_factory import ModelFactory

logging.basicConfig(level=logging.INFO)


class Agentic_Claude_Instance:
    def __init__(self, context: Any = None, key: Optional[str] = None, model: str = "claude-sonnet-4-6",
        num_processes: int = 1, max_iterations: int = 6):

        self.context = context
        self.model = model
        self.num_processes = num_processes
        self.max_iterations = max_iterations

        api_key = key or config.get("ANTHROPIC_API_KEY")
        if api_key is None:
            raise ValueError("No API key provided")

        self.client = anthropic.Anthropic(api_key=api_key)
        logging.info(f"Created Agentic Claude Instance. Model: {self.model}, "
                     f"Processes: {self.num_processes}, Max iterations: {self.max_iterations}")

    def prompt(self, prompt: str, schema=None, prompt_log: str = "",
               files=None, timeout: int = 60, category: Optional[int] = None):


        from claude_factory import CustomModelFactory
        factory = CustomModelFactory()
        generator = factory.create_model(model_name=self.model)
#         from ollama_factory import CustomModelFactory
#         factory = CustomModelFactory()
#         generator = factory.create_model(model_name="hf.co/mradermacher/RTLCoder-v1.1-GGUF:Q4_K_M")

        harness_dir = None
        rtl_filename = None

        if prompt_log:
            parts = prompt_log.replace("\\", "/").split("/")
            problem_name = next((p for p in parts if p.startswith("cvdp_")), None)
            prefix = parts[0] if parts else None

            if problem_name and prefix:
                harness_dir = os.path.join(
                    os.path.dirname(os.path.abspath(__file__)),
                    "..", "cvdp_benchmark", prefix, problem_name, "harness", "1"
                )
                harness_dir = os.path.normpath(harness_dir)

                env_path = os.path.join(harness_dir, "src", ".env")
                if os.path.exists(env_path):
                    with open(env_path) as f:
                        for line in f:
                            if line.startswith("VERILOG_SOURCES"):
                                rtl_filename = line.split("=")[-1].strip().split("/")[-1]
                                break

        logging.info(f"Harness dir: {harness_dir}, RTL file: {rtl_filename}")

        result = run_parallel(
            generator=generator,
            client=self.client,
            spec=prompt,
            num_processes=self.num_processes,
            max_iterations=self.max_iterations,
            harness_dir=harness_dir,
            rtl_filename=rtl_filename
        )

        verilog = result.get("verilog", "")
        logging.info(f"Agentic loop finished. Passed: {result['passed']}, Iterations: {result['iterations']}")

        if files and len(files) == 1:
            return ({"direct_text": verilog}, True)
        return verilog


class CustomModelFactory(ModelFactory):
    def __init__(self):
        super().__init__()

    def create_model(self, model_name: str, context: Any = None, key: Optional[str] = None, **kwargs) -> Any:
        return Agentic_Claude_Instance(context=context, key=key, model=model_name)