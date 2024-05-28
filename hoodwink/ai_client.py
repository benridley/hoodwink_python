import os
from typing import Any, Literal
from openai import OpenAI
from openai.types.chat import ChatCompletion
import anthropic
import json
from tenacity import retry, stop_after_attempt, wait_random_exponential

OPENAI_MODEL = "gpt-4o"
ANTHROPIC_MODEL = "claude-3-sonnet-20240229"

OPENAI_TOOLS = [
    {
        "type": "function",
        "function": {
            "name": "save_ingredients",
            "description": "Saves the provided ingredients to the database",
            "parameters": {
                "type": "object",
                "properties": {
                    "name": {"type": "string"},
                    "ingredients": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "name": {"type": "string"},
                                "unit": {"type": "string"},
                                "quantity": {"type": "number", "format": "float"},
                                "notes": {"type": "string"},
                            },
                            "required": ["name", "unit", "quantity"],
                            "additionalProperties": False,
                        },
                    },
                },
                "required": ["name", "ingredients"],
            },
        },
    },
]

ANTHROPIC_TOOLS = [
    {
        "name": "save_ingredients",
        "description": "Saves the provided ingredients to the database",
        "input_schema": {
            "type": "object",
            "properties": {
                "name": {"type": "string"},
                "ingredients": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {"type": "string"},
                            "unit": {"type": "string"},
                            "quantity": {"type": "number", "format": "float"},
                            "notes": {"type": "string"},
                        },
                        "required": ["name", "unit", "quantity"],
                        "additionalProperties": False,
                    },
                },
            },
            "required": ["name", "ingredients"],
        },
    },
]


class AIClient:
    def __init__(self, mode: Literal["openai", "anthropic"]):
        self.model = OPENAI_MODEL if mode == "openai" else ANTHROPIC_MODEL
        self.mode = mode

    # @retry(
    #     wait=wait_random_exponential(multiplier=1, max=40), stop=stop_after_attempt(3)
    # )
    def tool_call_request(self, messages, system_prompt=None) -> dict[str, Any]:
        if self.mode == "openai":
            try:
                client = OpenAI(
                    api_key=os.environ["OPENAI_API_KEY"],
                )
                if system_prompt:
                    messages.insert(0, {"role": "system", "content": system_prompt})
                response = client.chat.completions.create(
                    model=self.model,
                    messages=messages,
                    tools=OPENAI_TOOLS,  # type: ignore
                    tool_choice={
                        "type": "function",
                        "function": {"name": "save_ingredients"},
                    },
                )
                return self.extract_function_params(response)
            except Exception as e:
                print("Unable to generate ChatCompletion response")
                print(f"Exception: {e}")
                return e
        else:
            client = anthropic.Client(
                api_key=os.environ["ANTHROPIC_API_KEY"],
            )
            if system_prompt:
                response = client.beta.tools.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    system=system_prompt,
                    messages=messages,
                    tools=ANTHROPIC_TOOLS,  # type: ignore
                )
            else:
                response = client.beta.tools.messages.create(
                    model=self.model,
                    max_tokens=4096,
                    messages=messages,
                    tools=ANTHROPIC_TOOLS,  # type: ignore
                )
            return self.extract_function_params(response)

    def extract_function_params(self, response):
        if self.mode == "openai":
            return json.loads(
                response.choices[0].message.tool_calls[0].function.arguments
            )
        else:
            return response.content[1].input
