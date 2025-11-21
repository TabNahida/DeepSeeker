from dataclasses import dataclass, field
from typing import Optional


@dataclass
class ModelConfig:
    """Configuration for a single LLM model."""
    name: str
    max_output_tokens: int = 2048
    temperature: float = 0.2


@dataclass
class DeepSeekerConfig:
    """
    Global configuration for DeepSeeker step 1 (LLM0 only).
    """
    llm0: ModelConfig = field(
        default_factory=lambda: ModelConfig(
            name="qwen-plus", 
            max_output_tokens=2048,
            temperature=0.2,
        )
    )

    openai_api_key: Optional[str] = None
    openai_base_url: Optional[str] = None