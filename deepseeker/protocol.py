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
    """
    tool: str
    id: str
    args: Dict[str, Any]


def parse_tool_calls(text: str) -> List[ToolCall]:
    """
    Extract all DeepSeeker tool calls from a piece of model output.
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
