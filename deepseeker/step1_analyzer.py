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

    - raw_response: LLM0 原始回复
    - decision: "direct" 或 "search"
    - tool_call: 如果使用了 search，则为解析出的 ToolCall；否则为 None
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

        - `question`: 用户问题
        - `extra_history`: 可选的额外对话历史（role/content 字典）

        返回 Step1Result，包括：
        - LLM0 原始输出
        - 判定是 direct 还是 search
        - 如果是 search，包含解析出的 ToolCall
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
            # 我们只关注第一个 tool call
            call = tool_calls[0]
            if call.tool == "search":
                return Step1Result(
                    raw_response=raw,
                    decision="search",
                    tool_call=call,
                )

        # 没有工具调用，或不是 search，认为是 direct answer
        return Step1Result(
            raw_response=raw,
            decision="direct",
            tool_call=None,
        )
