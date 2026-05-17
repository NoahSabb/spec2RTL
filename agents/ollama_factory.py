# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

import os
import logging
import re
import json
import sys
from typing import Optional, Any
from src.config_manager import config
from openai import OpenAI

try:
    from src.model_helpers import ModelHelpers
except ImportError:
    try:
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from src.model_helpers import ModelHelpers
    except (ImportError, NameError):
        class ModelHelpers:
            def create_system_prompt(self, base_context, schema=None, category=None):
                context = base_context if base_context is not None else ""
                if schema is not None:
                    if isinstance(schema, list):
                        context += f"\nProvide the response in one of the following JSON schemas: \n"
                        schemas = []
                        for sch in schema:
                            schemas.append(f"{sch}")
                        context += "\nor\n".join(schemas)
                    else:
                        context += f"\nProvide the response in the following JSON schema: {schema}"
                    context += "\nThe response should be in JSON format, including double-quotes around keys and values, and proper escaping of quotes within values, and escaping of newlines."
                return context

            def parse_model_response(self, content, files=None, expected_single_file=False):
                return content

            def fix_json_formatting(self, content):
                try:
                    content = re.sub(r'(\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1 "\2":', content)
                    content = re.sub(r':\s*([a-zA-Z][a-zA-Z0-9_\s]*[a-zA-Z0-9])(\s*[,}])', r': "\1"\2', content)
                except:
                    pass
                return content

logging.basicConfig(level=logging.INFO)


class Ollama_Instance:
    def __init__(self, context: Any = "You are a helpful assistant.", key: Optional[str] = None, model: str = "hf.co/mradermacher/RTLCoder-v1.1-GGUF:Q4_K_M"):
        self.context = context
        self.model_name = model
        self.debug = False

        ollama_host = config.get("OLLAMA_HOST", "http://100.77.218.78:11434")
        self.client = OpenAI(base_url=f"{ollama_host}/v1", api_key="ollama")
        logging.info(f"Created Ollama Model at {ollama_host}. Using model: {self.model_name}")

    def set_debug(self, debug: bool = True) -> None:
        self.debug = debug

    def prompt(self, prompt: str, schema: Optional[str] = None, prompt_log: str = "",
               files: Optional[list] = None, timeout: int = 60, category: Optional[int] = None) -> str:
        helper = ModelHelpers()
        system_prompt = helper.create_system_prompt(self.context, schema, category)

        if timeout == 60:
            timeout = config.get("MODEL_TIMEOUT", 60)

        expected_single_file = files and len(files) == 1 and schema is None

        if prompt_log != "":
            try:
                os.makedirs(os.path.dirname(prompt_log), exist_ok=True)
                temp_log = f"{prompt_log}.tmp"
                with open(temp_log, "w+") as f:
                    f.write(system_prompt + "\n\n----------------------------------------\n" + prompt)
                os.replace(temp_log, prompt_log)
            except Exception as e:
                logging.error(f"Failed to write prompt log: {str(e)}")

        try:
            response = self.client.chat.completions.create(
                model=self.model_name,
                messages=[
                    {"role": "system", "content": system_prompt},
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096,
            )
            content = response.choices[0].message.content.strip()

            if self.debug:
                logging.debug(f"Response: {content}")

            if not expected_single_file and schema is not None and content.startswith('{') and content.endswith('}'):
                content = helper.fix_json_formatting(content)

            return helper.parse_model_response(content, files, expected_single_file)

        except Exception as e:
            logging.error(f"Error in prompt: {str(e)}")
            return None


from src.llm_lib.model_factory import ModelFactory

class CustomModelFactory(ModelFactory):
    def __init__(self):
        super().__init__()

    def create_model(self, model_name: str, context: Any = None, key: Optional[str] = None, **kwargs) -> Any:
        return Ollama_Instance(context=context, key=key, model=model_name)