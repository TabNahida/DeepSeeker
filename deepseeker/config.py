from __future__ import annotations
from pydantic import BaseModel, Field
from typing import List, Optional

class LLMConfig(BaseModel):
    base_url: str = "https://api.openai.com/v1"
    api_key: str
    model: str
    # optional: json mode hint
    use_json_mode: bool = True

class SearchConfig(BaseModel):
    bingsift_endpoint: str = "http://localhost:8787/search"
    per_query_limit: int = 8

class OrchestratorConfig(BaseModel):
    max_rounds: int = 3
    concurrency: int = 6
    save_log_path: str = ".deepseeker_run.jsonl"

class AppConfig(BaseModel):
    llm0: LLMConfig
    llm1: LLMConfig
    search: SearchConfig = Field(default_factory=SearchConfig)
    orchestrator: OrchestratorConfig = Field(default_factory=OrchestratorConfig)