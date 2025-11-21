from typing import List, Dict, Optional
from openai import OpenAI

from .config import ModelConfig


class LLMClient:
    """
    Thin wrapper around OpenAI-style chat completion API for LLM0.
    """

    def __init__(self, api_key: Optional[str] = None, base_url: Optional[str] = None) -> None:
        self._client = OpenAI(api_key=api_key, base_url=base_url)

    def chat(self, model_cfg: ModelConfig, messages: List[Dict[str, str]]) -> str:
        """
        Send a chat completion request and return the assistant content.
        """
        resp = self._client.chat.completions.create(
            model=model_cfg.name,
            messages=messages,
            temperature=model_cfg.temperature,
            max_tokens=model_cfg.max_output_tokens,
        )
        msg = resp.choices[0].message
        return msg.content or ""
