from __future__ import annotations

import json
import os
from typing import Any, Dict, List

from openai import OpenAI

from .config import LLMConfig
from .types import (
    ArticleSummary,
    FinalAnswer,
    PlanDecision,
    SearchFilters,
    SearchRequest,
    SearchResult,
    SelectionDecision,
)


class JsonLLMClient:
    """
    Small helper around OpenAI-style chat completion API that always expects
    a single JSON object as the assistant content.
    """

    def __init__(self, config: LLMConfig, client: OpenAI | None = None):
        self.config = config
        # Support custom base_url if you want to use an OpenAI-compatible endpoint
        base_url = os.getenv("OPENAI_BASE_URL")
        if client is not None:
            self.client = client
        else:
            if base_url:
                self.client = OpenAI(base_url=base_url)
            else:
                self.client = OpenAI()

    def chat_json(self, messages: List[Dict[str, Any]]) -> Dict[str, Any]:
        resp = self.client.chat.completions.create(
            model=self.config.model,
            messages=messages,
            temperature=self.config.temperature,
            max_tokens=self.config.max_output_tokens,
            response_format={"type": "json_object"},
        )
        content = resp.choices[0].message.content
        if content is None:
            raise RuntimeError("LLM returned empty content")
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Failed to parse LLM JSON: {content}") from exc


# ---------- LLM0 prompts & helpers ----------


LLM0_SYSTEM_PROMPT_PLAN = """
You are LLM0, the planner and final analyst inside the DeepSeeker system.

Your job in this stage is:

1. Read the user's research question.
2. Decide whether:
   - You can answer directly without web search, OR
   - You need to perform a Bing web search first.
3. If you choose to search, you must propose ONE SearchRequest.

Always output a single JSON object with this structure:

{
  "action": "direct_answer" | "search_then_answer",
  "direct_answer": "...",   // required when action == "direct_answer"
  "search": {                // required when action == "search_then_answer"
    "query": "...",
    "when": "day" | "week" | "month" | "any",
    "include": ["optional", "keywords"],
    "exclude": [],
    "allow_domains": [],
    "deny_domains": [],
    "max_results": 10
  },
  "notes": "brief explanation of why you chose this action"
}

Important:
- NEVER choose "when": "month" for scientific topics, because it filters out too many results.
- Prefer "week" or "any".
- If uncertain, ALWAYS use "when": "any".
- If you are unsure, prefer using search.
- Keep queries reasonably specific, not too broad or too narrow.
- Use English for queries and filters.
""".strip()


def call_llm0_plan(llm: JsonLLMClient, question: str) -> PlanDecision:
    messages = [
        {"role": "system", "content": LLM0_SYSTEM_PROMPT_PLAN},
        {
            "role": "user",
            "content": json.dumps({"question": question}, ensure_ascii=False),
        },
    ]
    data = llm.chat_json(messages)
    action = data.get("action")
    notes = data.get("notes")

    if action == "direct_answer":
        return PlanDecision(
            action=action,
            direct_answer=data.get("direct_answer", ""),
            notes=notes,
        )

    if action == "search_then_answer":
        search = data.get("search") or {}
        filters = SearchFilters(
            include=search.get("include", []) or [],
            exclude=search.get("exclude", []) or [],
            allow_domains=search.get("allow_domains", []) or [],
            deny_domains=search.get("deny_domains", []) or [],
        )
        sr = SearchRequest(
            query=search.get("query", question),
            when=search.get("when", "week"),
            filters=filters,
            max_results=int(search.get("max_results", 10)),
        )
        return PlanDecision(
            action=action,
            search_request=sr,
            notes=notes,
        )

    # Fallback: force a search
    fallback_filters = SearchFilters()
    sr = SearchRequest(query=question, when="week", filters=fallback_filters, max_results=10)
    return PlanDecision(
        action="search_then_answer",
        search_request=sr,
        notes="Fallback: invalid action, defaulting to search_then_answer.",
    )


LLM0_SYSTEM_PROMPT_SELECT = """
You are LLM0 inside DeepSeeker.

You receive:
- The original research question.
- A list of search results (title, snippet, url, time).

Your job is to choose which results should be deeply read by another model (LLM1).

Output a JSON object with this structure:

{
  "selected_ids": ["r1", "r3", "r5"],
  "notes": "why you chose these results"
}

Guidelines:
- Prefer diverse, detailed, and authoritative sources.
- Avoid obvious duplicates.
- If all results are weak, you may return an empty list but explain why.
""".strip()


def call_llm0_select(
    llm: JsonLLMClient, question: str, search_results: list[SearchResult]
) -> SelectionDecision:
    # Compact representation of search results
    results_payload = [
        {
            "id": r.id,
            "title": r.title,
            "snippet": r.snippet,
            "guessed_time": r.guessed_time,
        }
        for r in search_results
    ]
    messages = [
        {"role": "system", "content": LLM0_SYSTEM_PROMPT_SELECT},
        {
            "role": "user",
            "content": json.dumps(
                {"question": question, "results": results_payload},
                ensure_ascii=False,
            ),
        },
    ]
    data = llm.chat_json(messages)
    selected_ids = data.get("selected_ids") or []
    notes = data.get("notes")
    return SelectionDecision(selected_ids=selected_ids, notes=notes)


LLM0_SYSTEM_PROMPT_SYNTHESIZE = """
You are LLM0 inside DeepSeeker.

You receive:
- The original research question.
- A list of search results.
- A list of article summaries produced by LLM1.

Your job is to write a structured, well-organized final answer.

Output a JSON object with this structure:

{
  "answer": "long, well-structured report in Markdown",
  "key_points": ["...", "..."],
  "used_results": ["r1", "r3"],
  "notes": "optional notes about uncertainty or limitations"
}

- The answer should be in the same language as the question, if possible.
- Explicitly integrate information from multiple sources.
- Mention limitations when evidence is weak or conflicting.
""".strip()


def call_llm0_synthesize(
    llm: JsonLLMClient,
    question: str,
    search_results: list[SearchResult],
    summaries: list[ArticleSummary],
) -> FinalAnswer:
    results_payload = [
        {
            "id": r.id,
            "title": r.title,
            "url": r.url,
            "snippet": r.snippet,
            "domain": r.domain,
            "guessed_time": r.guessed_time,
        }
        for r in search_results
    ]
    summaries_payload = [
        {
            "result_id": s.result_id,
            "url": s.url,
            "title": s.title,
            "summary": s.summary,
            "key_points": s.key_points,
            "relevance_score": s.relevance_score,
        }
        for s in summaries
    ]

    messages = [
        {"role": "system", "content": LLM0_SYSTEM_PROMPT_SYNTHESIZE},
        {
            "role": "user",
            "content": json.dumps(
                {
                    "question": question,
                    "search_results": results_payload,
                    "summaries": summaries_payload,
                },
                ensure_ascii=False,
            ),
        },
    ]
    data = llm.chat_json(messages)
    answer = data.get("answer", "")
    key_points = data.get("key_points") or []
    used_results = data.get("used_results") or []
    notes = data.get("notes")

    return FinalAnswer(
        answer=answer,
        key_points=key_points,
        used_results=used_results,
        notes=notes,
    )


# ---------- LLM1 prompt & helper ----------


LLM1_SYSTEM_PROMPT_SUMMARIZE = """
You are LLM1 inside DeepSeeker. You are a focused reader and summarizer.

Input:
- A research question.
- One web page (HTML content).
- Its URL and title.

Task:
- Read the page.
- Extract information relevant to the question.
- Produce a concise but rich summary.

Output a JSON object with this structure:

{
  "title": "cleaned title of the page (if available)",
  "summary": "short, focused summary",
  "key_points": ["bullet", "points"],
  "relevance_score": 0.0_to_1.0,
  "notes": "optional notes, e.g., low relevance"
}

Guidelines:
- Ignore navigation, ads, boilerplate.
- If the page is mostly irrelevant, set relevance_score < 0.3 and explain why.
- Do NOT answer the original question globally; only summarize THIS single page.
""".strip()


def call_llm1_summarize(
    llm: JsonLLMClient,
    question: str,
    url: str,
    title: str,
    html_excerpt: str,
) -> ArticleSummary:
    payload = {
        "question": question,
        "url": url,
        "title": title,
        "html_excerpt": html_excerpt,
    }
    messages = [
        {"role": "system", "content": LLM1_SYSTEM_PROMPT_SUMMARIZE},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False),
        },
    ]
    data = llm.chat_json(messages)

    clean_title = data.get("title") or title
    summary_text = data.get("summary", "")
    key_points = data.get("key_points") or []
    relevance_score = float(data.get("relevance_score", 0.0))
    notes = data.get("notes")

    # result_id is filled later by the orchestrator (we know which SearchResult it came from)
    return ArticleSummary(
        result_id="",
        url=url,
        title=clean_title,
        summary=summary_text,
        key_points=key_points,
        relevance_score=relevance_score,
        notes=notes,
    )
