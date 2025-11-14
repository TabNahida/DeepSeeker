from __future__ import annotations
import httpx, orjson
from typing import Any, Dict, List, Optional

class OpenAIStyleClient:
    def __init__(self, base_url: str, api_key: str, timeout: float = 60.0):
        self.base_url = base_url.rstrip("/")
        self.api_key = api_key
        self.timeout = timeout
        self.headers = {
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        }

    async def achat_json(self, model: str, messages: List[Dict[str, str]], *, json_mode: bool = True,
                         response_schema: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """Call chat completions and try to coerce the response to JSON.
        Tries response_format JSON when provider supports. Falls back to best-effort JSON extraction.
        """
        payload: Dict[str, Any] = {
            "model": model,
            "messages": messages,
            "temperature": 0.2,
        }
        if json_mode:
            # compatible with OpenAI responses and some compatible vendors
            payload["response_format"] = {"type": "json_object"}
            if response_schema:
                # Some providers support json_schema; if not, ignored.
                payload["response_format"] = {"type": "json_schema", "json_schema": response_schema}

        url = f"{self.base_url}/chat/completions"
        async with httpx.AsyncClient(timeout=self.timeout) as client:
            r = await client.post(url, headers=self.headers, content=orjson.dumps(payload))
            r.raise_for_status()
            data = r.json()
            text = data["choices"][0]["message"]["content"]
            try:
                return orjson.loads(text)
            except Exception:
                from .utils import extract_json
                return extract_json(text)