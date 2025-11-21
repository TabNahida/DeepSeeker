from __future__ import annotations

from typing import List

from .logging_utils import StepLogger
from .llm_client import (
    JsonLLMClient,
    call_llm0_plan,
    call_llm0_select,
    call_llm0_synthesize,
    call_llm1_summarize,
)
from .search_client import SearchClient
from .types import ArticleSummary, DeepSeekerReport, SearchResult


class DeepSeekerOrchestrator:
    """
    High-level orchestrator for one DeepSeeker research session.
    """

    def __init__(
        self,
            llm0: JsonLLMClient,
            llm1: JsonLLMClient,
            search_client: SearchClient,
            logger: StepLogger,
        ):
        self.llm0 = llm0
        self.llm1 = llm1
        self.search_client = search_client
        self.logger = logger

    def run(self, question: str) -> DeepSeekerReport:
        """
        Run the full pipeline for a single user question.
        """
        report = DeepSeekerReport(question=question, steps=[], final_answer=None)

        # ---------- Step 1: LLM0 decides plan ----------
        self.logger.log("plan", "LLM0 is planning: direct answer vs. search.")
        plan = call_llm0_plan(self.llm0, question=question)
        report.steps.extend(self.logger.events)

        if plan.action == "direct_answer" and plan.direct_answer:
            self.logger.log("final", "LLM0 decided to answer directly without search.")
            report.final_answer = self._wrap_direct_answer(plan.direct_answer)
            report.steps.extend(self.logger.events[len(report.steps) :])
            return report

        if not plan.search_request:
            # Fallback: if LLM0 gave no search_request, we cannot proceed.
            self.logger.log(
                "error",
                "LLM0 did not provide a valid search_request. Aborting.",
                error=True,
            )
            report.steps.extend(self.logger.events[len(report.steps) :])
            return report

        # ---------- Step 2: Run BingSift search ----------
        self.logger.log(
            "search",
            f"Running Bing search with query='{plan.search_request.query}' "
            f"when='{plan.search_request.when}'.",
        )
        try:
            search_results: List[SearchResult] = self.search_client.search(plan.search_request)
        except Exception as e:  # network / BingSift errors
            self.logger.log(
                "error",
                f"Search failed: {e}",
                error=True,
            )
            report.steps.extend(self.logger.events[len(report.steps) :])
            return report

        report.search_results = search_results
        self.logger.log(
            "search",
            f"Search returned {len(search_results)} results.",
        )

        # ---------- Step 3: LLM0 selects which results to read ----------
        if not search_results:
            self.logger.log(
                "final",
                "No search results found; returning empty answer.",
                error=True,
            )
            report.steps.extend(self.logger.events[len(report.steps) :])
            return report

        self.logger.log("select", "LLM0 is selecting which results to read.")
        selection = call_llm0_select(self.llm0, question=question, search_results=search_results)
        self.logger.log(
            "select",
            f"LLM0 selected {len(selection.selected_ids)} results for deep reading.",
            data={"selected_ids": selection.selected_ids},
        )

        selected_map = {r.id: r for r in search_results}
        read_targets: List[SearchResult] = [
            selected_map[rid] for rid in selection.selected_ids if rid in selected_map
        ]

        # ---------- Step 4: LLM1 summarizes selected articles ----------
        summaries: List[ArticleSummary] = []
        for r in read_targets:
            self.logger.log("summarize", f"Fetching and summarizing URL: {r.url}")
            try:
                html_excerpt = self.search_client.fetch_page_excerpt(r.url)
            except Exception as e:
                self.logger.log(
                    "error",
                    f"Failed to fetch page for {r.url}: {e}",
                    error=True,
                )
                continue

            try:
                summary = call_llm1_summarize(
                    llm=self.llm1,
                    question=question,
                    url=r.url,
                    title=r.title,
                    html_excerpt=html_excerpt,
                )
                # Attach result_id
                summary.result_id = r.id
                summaries.append(summary)
                self.logger.log(
                    "summarize",
                    f"LLM1 summarized {r.url} (relevance={summary.relevance_score:.2f}).",
                    data={"result_id": r.id},
                )
            except Exception as e:
                self.logger.log(
                    "error",
                    f"LLM1 summarization failed for {r.url}: {e}",
                    error=True,
                )

        report.raw_summaries = summaries

        if not summaries:
            self.logger.log(
                "final",
                "No article summaries available; returning empty answer.",
                error=True,
            )
            report.steps.extend(self.logger.events[len(report.steps) :])
            return report

        # ---------- Step 5: LLM0 synthesizes final answer ----------
        self.logger.log(
            "final",
            "LLM0 is synthesizing the final report from all summaries.",
        )
        final_answer = call_llm0_synthesize(
            llm=self.llm0,
            question=question,
            search_results=search_results,
            summaries=summaries,
        )
        report.final_answer = final_answer

        # Collect all remaining logs
        report.steps.extend(self.logger.events[len(report.steps) :])
        return report

    @staticmethod
    def _wrap_direct_answer(answer_text: str) -> "FinalAnswer":
        from .types import FinalAnswer

        return FinalAnswer(
            answer=answer_text,
            key_points=[],
            used_results=[],
            notes="Direct answer from LLM0 without web search.",
        )
