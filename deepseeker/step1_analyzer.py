from dataclasses import dataclass
from pathlib import Path
from typing import List, Dict, Optional, Tuple

from .config import DeepSeekerConfig
from .llm_client import LLMClient
from .protocol import parse_tool_calls, ToolCall


def _load_llm0_prompt() -> str:
    """
    Load the LLM0 system prompt for step 1 from the prompts directory.
    """
    here = Path(__file__).resolve().parent
    prompt_path = here / "prompts" / "llm0_orchestrator_step1.md"
    return prompt_path.read_text(encoding="utf-8")


@dataclass
class Step1Result:
    """
    Result of DeepSeeker step 1 decision.
    """
    raw_response: str
    decision: str
    tool_call: Optional[ToolCall]


class DeepSeekerStep1:
    """
    Run only the first step of DeepSeeker:

    - Ask LLM0 to analyse the user's question.
    - Decide whether to answer directly or trigger a search.
    """

    def __init__(self, config: DeepSeekerConfig, client: Optional[LLMClient] = None) -> None:
        self.config = config
        self.client = client or LLMClient(
            api_key=config.openai_api_key,
            base_url=config.openai_base_url
        )
        self.system_prompt = _load_llm0_prompt()

    def run(self, question: str, extra_history: Optional[List[Dict[str, str]]] = None) -> Step1Result:
        """
        Execute step 1 for a single question.
        """
        messages: List[Dict[str, str]] = [
            {"role": "system", "content": self.system_prompt},
        ]

        if extra_history:
            messages.extend(extra_history)

        messages.append({"role": "user", "content": question})

        raw = self.client.chat(self.config.llm0, messages)
        tool_calls = parse_tool_calls(raw)

        if tool_calls:
            call = tool_calls[0]
            if call.tool == "search":
                return Step1Result(
                    raw_response=raw,
                    decision="search",
                    tool_call=call,
                )
                
        return Step1Result(
            raw_response=raw,
            decision="direct",
            tool_call=None,
        )
