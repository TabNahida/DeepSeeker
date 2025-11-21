from __future__ import annotations

import os
from dataclasses import dataclass


@dataclass
class LLMConfig:
    model: str
    temperature: float = 0.3
    max_output_tokens: int = 2048


def load_llm_configs() -> tuple[LLMConfig, LLMConfig]:
    """
    Load LLM0 / LLM1 model names from environment variables,
    with reasonable defaults.
    """
    llm0_model = os.getenv("DEEPSEEKER_LLM0_MODEL", "gpt-5.1-thinking")
    llm1_model = os.getenv("DEEPSEEKER_LLM1_MODEL", "gpt-4o-mini")

    llm0 = LLMConfig(model=llm0_model, temperature=0.2, max_output_tokens=4096)
    llm1 = LLMConfig(model=llm1_model, temperature=0.3, max_output_tokens=1536)
    return llm0, llm1
