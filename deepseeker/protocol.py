import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List


# 匹配 fenced code block：
# ```deepseeker-tool
# { ...json... }
# ```
TOOL_BLOCK_RE = re.compile(
    r"```deepseeker-tool\s*(\{.*?\})\s*```",
    re.DOTALL | re.IGNORECASE,
)


@dataclass
class ToolCall:
    """
    Parsed representation of a DeepSeeker tool call emitted by LLM0.

    对 Step 1 来说，只会有 "search" 这个 tool。
    """
    tool: str
    id: str
    args: Dict[str, Any]


def parse_tool_calls(text: str) -> List[ToolCall]:
    """
    Extract all DeepSeeker tool calls from a piece of model output.

    - 不抛异常，解析失败就忽略
    - 允许多个 code block，但我们一般只用第一个
    """
    calls: List[ToolCall] = []

    for match in TOOL_BLOCK_RE.finditer(text):
        raw_json = match.group(1)
        try:
            data = json.loads(raw_json)
        except json.JSONDecodeError:
            continue

        tool = data.get("tool")
        call_id = data.get("id") or tool or "tool"
        args = data.get("args") or {}

        if not tool or not isinstance(args, dict):
            continue

        calls.append(ToolCall(tool=tool, id=str(call_id), args=args))

    return calls
