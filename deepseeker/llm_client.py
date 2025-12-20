from __future__ import annotations

import json
import os
import time
from typing import Any, Dict, List, Optional

from openai import OpenAI

from .config import LLMConfig
from .logging_utils import StepLogger
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
    
    Enhanced with logging capabilities to record full LLM I/O.
    """

    def __init__(self, config: LLMConfig, client: OpenAI | None = None, logger: Optional[StepLogger] = None, 
                 api_key: Optional[str] = None, base_url: Optional[str] = None):
        self.config = config
        self.logger = logger
        
        if client is not None:
            self.client = client
        else:
            # Priority: explicit parameters > environment variables
            use_api_key = api_key or os.getenv("OPENAI_API_KEY")
            use_base_url = base_url or os.getenv("OPENAI_BASE_URL")
            
            if use_base_url:
                self.client = OpenAI(api_key=use_api_key, base_url=use_base_url)
            else:
                self.client = OpenAI(api_key=use_api_key)

    def chat_json(self, messages: List[Dict[str, Any]], call_type: str = "unknown") -> Dict[str, Any]:
        """Make LLM call with full logging of input/output."""
        start_time = time.time()
        
        try:
            resp = self.client.chat.completions.create(
                model=self.config.model,
                messages=messages,
                max_tokens=self.config.max_output_tokens,
                response_format={"type": "json_object"},
            )
            
            duration_ms = int((time.time() - start_time) * 1000)
            content = resp.choices[0].message.content
            
            if content is None:
                raise RuntimeError("LLM returned empty content")
            
            # Parse response
            response_data = json.loads(content)
            
            # Log the full call if logger is available
            if self.logger:
                self.logger.log_llm_call(
                    call_type=call_type,
                    messages=messages,
                    response=response_data,
                    model=self.config.model,
                    duration_ms=duration_ms,
                )
            
            return response_data
            
        except Exception as e:
            # Log error details
            if self.logger:
                duration_ms = int((time.time() - start_time) * 1000)
                self.logger.log_llm_call(
                    call_type=call_type,
                    messages=messages,
                    response={"error": str(e)},
                    model=self.config.model,
                    duration_ms=duration_ms,
                )
            raise


# ---------- LLM0 prompts & helpers ----------


LLM0_SYSTEM_PROMPT_PLAN = """
You are LLM0, the planner and final analyst inside the DeepSeeker system.

Your job in this stage is:

1. Read the user's research question.
2. Decide whether:
   - You can answer directly without web search, OR
   - You need to perform one or more web searches first.
3. If you choose to search, you must propose ONE OR MORE search requests.

Always output a single JSON object with this structure:

{
  "action": "direct_answer" | "search_then_answer",
  "direct_answer": "...",   // required when action == "direct_answer"
  "searches": [             // required when action == "search_then_answer"
    {
      "query": "...",
      "when": "day" | "week" | "month" | "year" | "any",
      "include": ["optional", "keywords"],
      "exclude": [],
      "allow_domains": [],
      "deny_domains": [],
      "max_results": 10
    }
  ],
  "notes": "brief explanation of why you chose this action"
}

Guidance about `when`:
- Prefer "day" for breaking news or very fresh events.
- Prefer "month" for topics evolving over weeks.
- Prefer "year" or "any" for long-term background or theory.
- Use "week" only when you specifically need roughly last 7 days of information;
  avoid it as the default choice.

Guidance about multiple searches:
- Use multiple search requests when you want to cover different angles,
  e.g. "general background", "recent news", "technical docs".
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
    data = llm.chat_json(messages, call_type="llm0_plan")
    action = data.get("action")
    notes = data.get("notes")

    # --- direct_answer path ---
    if action == "direct_answer":
        return PlanDecision(
            action=action,
            direct_answer=data.get("direct_answer", ""),
            notes=notes,
        )

    # --- search_then_answer path (multi-search) ---
    if action == "search_then_answer":
        raw_searches = data.get("searches") or []

        # backward compatibility: allow a single "search" object
        if not raw_searches and "search" in data:
            raw_searches = [data["search"]]

        search_requests: list[SearchRequest] = []
        for s in raw_searches:
            if not isinstance(s, dict):
                continue
            """
            filters = SearchFilters(
                include=s.get("include", []) or [],
                exclude=s.get("exclude", []) or [],
                allow_domains=s.get("allow_domains", []) or [],
                deny_domains=s.get("deny_domains", []) or [],
            )
            """
            filters = SearchFilters()
            search_requests.append(
                SearchRequest(
                    query=s.get("query") or question,
                    when=s.get("when", "week"),
                    filters=filters,
                    max_results=int(s.get("max_results", 10)),
                )
            )

        return PlanDecision(
            action="search_then_answer",
            search_requests=search_requests,
            notes=notes,
        )

    # --- fallback: invalid action, force a single search_then_answer ---
    fallback_filters = SearchFilters()
    return PlanDecision(
        action="search_then_answer",
        search_requests=[
            SearchRequest(
                query=question,
                when="week",
                filters=fallback_filters,
                max_results=10,
            )
        ],
        notes="Fallback: invalid action, defaulting to a single search_then_answer.",
    )


LLM0_SYSTEM_PROMPT_SELECT = """
You are LLM0 inside DeepSeeker.

You receive:
- The original research question.
- A list of search results (title, snippet, url, time).

Your job is to choose which results should be deeply read by another model (LLM1).

Output a JSON object with this structure:

{
  "selected_ids": ["s1_r1", "s2_r3", "s4_r5"],
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
    data = llm.chat_json(messages, call_type="llm0_select")
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
    data = llm.chat_json(messages, call_type="llm0_synthesize")
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
- Extracted text content from one web page (cleaned text, not HTML).
- Its URL and title.

Task:
- Read the extracted text.
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
- Focus on the extracted text content.
- If the page is mostly irrelevant, set relevance_score < 0.3 and explain why.
- Do NOT answer the original question globally; only summarize THIS single page.
- The text may be truncated, so work with what's available.
- Remove any remaining duplicate content or boilerplate text.
""".strip()


def call_llm1_summarize(
    llm: JsonLLMClient,
    question: str,
    url: str,
    title: str,
    html_excerpt: str,  # Contains extracted text, not HTML
) -> ArticleSummary:
    payload = {
        "question": question,
        "url": url,
        "title": title,
        "extracted_text": html_excerpt,
    }
    messages = [
        {"role": "system", "content": LLM1_SYSTEM_PROMPT_SUMMARIZE},
        {
            "role": "user",
            "content": json.dumps(payload, ensure_ascii=False),
        },
    ]
    data = llm.chat_json(messages, call_type="llm1_summarize")

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
