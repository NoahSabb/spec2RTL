# SPDX-FileCopyrightText: Copyright (c) 2025 NVIDIA CORPORATION & AFFILIATES. All rights reserved.
# SPDX-License-Identifier: Apache-2.0

"""
Example of a Claude model instance implementation.

This is a skeleton implementation that shows how to create a custom model instance
compatible with the benchmark system. Users should implement their own model instances
by following a similar pattern.
"""

import os
import logging
import re
import json
import sys
from typing import Optional, Any, Dict, List
from src.config_manager import config

# Uncomment and install anthropic package
# pip install anthropic
import anthropic

# Import ModelHelpers - used for processing responses
try:
    from src.model_helpers import ModelHelpers
except ImportError:
    try:
        # Try alternate import path
        sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
        from src.model_helpers import ModelHelpers
    except (ImportError, NameError):
        # Define minimal ModelHelpers class for standalone usage
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
                if expected_single_file:
                    return content
                return content
                
            def fix_json_formatting(self, content):
                try:
                    content = re.sub(r'(\{|\,)\s*([a-zA-Z_][a-zA-Z0-9_]*)\s*:', r'\1 "\2":', content)
                    content = re.sub(r':\s*([a-zA-Z][a-zA-Z0-9_\s]*[a-zA-Z0-9])(\s*[,}])', r': "\1"\2', content)
                    try:
                        json.loads(content)
                    except json.JSONDecodeError:
                        pass
                except:
                    pass
                return content

logging.basicConfig(level=logging.INFO)

class Claude_Instance:
    """
    Example implementation of an Anthropic Claude model instance.
    
    This provides the same interface as OpenAI_Instance but uses Anthropic's Claude API.
    """

    def __init__(self, context: Any = "You are a helpful assistant.", key: Optional[str] = None, model: str = "claude-3-opus-20240229"):
        """
        Initialize a Claude model instance.
        
        Args:
            context: The system prompt or context for the model
            key: Anthropic API key (will fall back to ANTHROPIC_API_KEY environment variable)
            model: The Claude model version to use
        """
        self.context = context
        self.model = model
        self.debug = False
        
        api_key = config.get("ANTHROPIC_API_KEY")
        
        if (key is None) and (api_key is None):
            raise ValueError("Unable to create Claude Model - No API key provided")
            
        # Use provided key or fallback to environment variable
        if key is not None:
            actual_key = key
        else:
            actual_key = api_key
            
        # Initialize Anthropic client
        # Uncomment when implementing with actual Anthropic API
        self.client = anthropic.Anthropic(api_key=actual_key)
        logging.info(f"Created Claude Model using the provided key. Using model: {self.model}")
    
    def set_debug(self, debug: bool = True) -> None:
        """
        Enable or disable debug mode.
        
        Args:
            debug: Whether to enable debug mode (default: True)
        """
        self.debug = debug
        logging.info(f"Debug mode {'enabled' if debug else 'disabled'}")
    
    def prompt(self, prompt: str, schema: Optional[str] = None, prompt_log: str = "", 
               files: Optional[list] = None, timeout: int = 60, category: Optional[int] = None) -> str:
        """
        Send a prompt to the Claude model and get a response.
        
        Args:
            prompt: The user prompt/query
            schema: Optional JSON schema for structured output
            prompt_log: Path to log the prompt (if not empty)
            files: List of expected output files (if any)
            timeout: Timeout in seconds for the API call (default: 60)
            category: Optional integer indicating the category/problem ID
            
        Returns:
            The model's response as text
        """
        if hasattr(self, 'client') is False:
            raise ValueError("Claude client not initialized")
            
        # Import and use ModelHelpers
        helper = ModelHelpers()
        system_prompt = helper.create_system_prompt(self.context, schema, category)
        
        # Use timeout from config if not specified
        if timeout == 60:
            timeout = config.get("MODEL_TIMEOUT", 60)
            
        # Determine if we're expecting a single file (direct text mode)
        expected_single_file = files and len(files) == 1 and schema is None
        expected_file_name = files[0] if expected_single_file else None

        if self.debug:
            logging.debug(f"Requesting prompt using the model: {self.model}")
            logging.debug(f"System prompt: {system_prompt}")
            logging.debug(f"User prompt: {prompt}")
            logging.debug(f"Timeout: {timeout} seconds")
            if files:
                logging.debug(f"Expected files: {files}")
                if expected_single_file:
                    logging.debug(f"Using direct text mode for single file: {expected_file_name}")
            
        if prompt_log != "":
            try:
                # Ensure directory exists
                os.makedirs(os.path.dirname(prompt_log), exist_ok=True)
                
                # Write to a temporary file first
                temp_log = f"{prompt_log}.tmp"
                with open(temp_log, "w+") as f:
                    f.write(system_prompt + "\n\n----------------------------------------\n" + prompt)
                
                # Atomic rename to final file
                os.replace(temp_log, prompt_log)
            except Exception as e:
                logging.error(f"Failed to write prompt log to {prompt_log}: {str(e)}")
                # Continue anyway, don't fail because of logging issues
        
        # This is where you would call the actual Claude API
        # Uncomment and update when implementing with actual Anthropic API
        
        try:
            response = self.client.messages.create(
                model=self.model,
                system=system_prompt,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=4096
            )
            
            content = response.content[0].text.strip()
            
            # Print response details if debug is enabled
            if self.debug:
                logging.debug(f"Response received:\n{response}")
                logging.debug(f"  - Message: {content}")
            
            # Process the response using the ModelHelpers
            if expected_single_file:
                pass
            elif schema is not None and content.startswith('{') and content.endswith('}'):
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
        return Claude_Instance(context=context, key=key, model=model_name)