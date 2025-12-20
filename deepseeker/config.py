from __future__ import annotations

import json
import os
from dataclasses import dataclass, asdict
from typing import Optional


@dataclass
class LLMConfig:
    model: str
    max_output_tokens: int = 2048


@dataclass
class DeepSeekerConfig:
    llm0: LLMConfig
    llm1: LLMConfig
    api_key: Optional[str] = None
    base_url: Optional[str] = None
    search_max_results: int = 10
    search_freshness: str = "week"


def load_llm_configs(config_file: Optional[str] = None) -> tuple[LLMConfig, LLMConfig]:
    """
    Load LLM0 / LLM1 model names from config file or environment variables,
    with reasonable defaults.
    
    Priority order:
    1. Explicit config file (if specified via --config)
    2. Default config.json (if exists in current directory)
    3. Environment variables
    4. Default values
    """
    # Priority 1: Explicit config file specified
    if config_file:
        if os.path.exists(config_file):
            return _load_from_config_file(config_file)
        else:
            raise FileNotFoundError(f"Config file not found: {config_file}")
    
    # Priority 2: Default config.json in current directory
    default_config_path = "config.json"
    if os.path.exists(default_config_path):
        return _load_from_config_file(default_config_path)
    
    # Priority 3: Environment variables
    llm0_model = os.getenv("DEEPSEEKER_LLM0_MODEL", "gpt-5.1-thinking")
    llm1_model = os.getenv("DEEPSEEKER_LLM1_MODEL", "gpt-4o-mini")
    
    llm0_max_tokens = int(os.getenv("DEEPSEEKER_LLM0_MAX_TOKENS", "4096"))
    llm1_max_tokens = int(os.getenv("DEEPSEEKER_LLM1_MAX_TOKENS", "1536"))

    llm0 = LLMConfig(model=llm0_model, max_output_tokens=llm0_max_tokens)
    llm1 = LLMConfig(model=llm1_model, max_output_tokens=llm1_max_tokens)
    return llm0, llm1


def _load_from_config_file(config_file: str) -> tuple[LLMConfig, LLMConfig]:
    """Load configuration from a JSON config file."""
    with open(config_file, 'r', encoding='utf-8') as f:
        config_data = json.load(f)
    
    llm0_data = config_data.get("llm0", {})
    llm1_data = config_data.get("llm1", {})
    
    llm0 = LLMConfig(
        model=llm0_data.get("model", "gpt-5.1-thinking"),
        max_output_tokens=llm0_data.get("max_output_tokens", 4096)
    )
    
    llm1 = LLMConfig(
        model=llm1_data.get("model", "gpt-4o-mini"),
        max_output_tokens=llm1_data.get("max_output_tokens", 1536)
    )
    
    return llm0, llm1


def load_full_config(config_file: Optional[str] = None) -> DeepSeekerConfig:
    """
    Load full DeepSeeker configuration from config file or environment variables.
    
    Priority order:
    1. Explicit config file (if specified via --config)
    2. Default config.json (if exists in current directory)
    3. Environment variables
    4. Default values
    """
    llm0, llm1 = load_llm_configs(config_file)
    
    # Determine which config file to use for additional settings
    config_path = None
    if config_file and os.path.exists(config_file):
        config_path = config_file
    elif os.path.exists("config.json"):
        config_path = "config.json"
    
    # Try config file for additional settings
    if config_path:
        with open(config_path, 'r', encoding='utf-8') as f:
            config_data = json.load(f)
        
        # Get API settings from config file
        api_key = config_data.get("api_key")
        base_url = config_data.get("base_url")
        
        # If not in config file, try environment variables
        if api_key is None:
            api_key = os.getenv("OPENAI_API_KEY")
        if base_url is None:
            base_url = os.getenv("OPENAI_BASE_URL")
        
        return DeepSeekerConfig(
            llm0=llm0,
            llm1=llm1,
            api_key=api_key,
            base_url=base_url,
            search_max_results=config_data.get("search_max_results", 10),
            search_freshness=config_data.get("search_freshness", "week")
        )
    
    # Use environment variables or defaults
    api_key = os.getenv("OPENAI_API_KEY")
    base_url = os.getenv("OPENAI_BASE_URL")
    search_max_results = int(os.getenv("DEEPSEEKER_SEARCH_MAX_RESULTS", "10"))
    search_freshness = os.getenv("DEEPSEEKER_SEARCH_FRESHNESS", "week")
    
    return DeepSeekerConfig(
        llm0=llm0,
        llm1=llm1,
        api_key=api_key,
        base_url=base_url,
        search_max_results=search_max_results,
        search_freshness=search_freshness
    )


def create_default_config_file(file_path: str = "config.json") -> str:
    """
    Create a default configuration file template.
    
    Returns:
        Path to the created config file.
    """
    default_config = {
        "api_key": "",  # Set your OpenAI API key here or use environment variable
        "base_url": "",  # Optional: custom OpenAI-compatible endpoint
        "llm0": {
            "model": "gpt-5.1-thinking",
            "max_output_tokens": 4096
        },
        "llm1": {
            "model": "gpt-4o-mini",
            "max_output_tokens": 1536
        },
        "search_max_results": 10,
        "search_freshness": "week"
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(default_config, f, indent=2, ensure_ascii=False)
    
    return file_path


def save_config_to_file(config: DeepSeekerConfig, file_path: str) -> None:
    """
    Save a DeepSeekerConfig object to a JSON file.
    """
    config_dict = {
        "api_key": config.api_key if config.api_key else "",
        "base_url": config.base_url if config.base_url else "",
        "llm0": {
            "model": config.llm0.model,
            "max_output_tokens": config.llm0.max_output_tokens
        },
        "llm1": {
            "model": config.llm1.model,
            "max_output_tokens": config.llm1.max_output_tokens
        },
        "search_max_results": config.search_max_results,
        "search_freshness": config.search_freshness
    }
    
    with open(file_path, 'w', encoding='utf-8') as f:
        json.dump(config_dict, f, indent=2, ensure_ascii=False)
