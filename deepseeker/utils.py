from __future__ import annotations
import json, re, uuid, datetime
from typing import Any, Dict

JSON_PATTERN = re.compile(r"\{[\s\S]*\}")

def extract_json(text: str) -> Dict[str, Any]:
    """Best-effort: grab the first JSON object in text."""
    m = JSON_PATTERN.search(text)
    if not m:
        raise ValueError("No JSON object found in model output")
    return json.loads(m.group(0))

def new_uuid() -> str:
    return str(uuid.uuid4())

def now_iso() -> str:
    return datetime.datetime.utcnow().isoformat() + "Z"