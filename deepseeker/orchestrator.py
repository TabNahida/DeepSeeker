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
        
        # Ensure LLM clients have logger for full I/O recording
        if hasattr(llm0, 'logger'):
            llm0.logger = logger
        if hasattr(llm1, 'logger'):
            llm1.logger = logger

    def run(self, question: str) -> DeepSeekerReport:
        """
        Run the full pipeline for a single user question.
        """
        report = DeepSeekerReport(question=question, steps=[], final_answer=None)

        # ---------- Step 1: LLM0 decides plan ----------
        self.logger.log("plan", "LLM0 is planning: direct answer vs. search.")
        plan = call_llm0_plan(self.llm0, question=question)

        if plan.action == "direct_answer" and plan.direct_answer:
            self.logger.log("final", "LLM0 decided to answer directly without search.")
            report.final_answer = self._wrap_direct_answer(plan.direct_answer)
            report.steps = self.logger.events[:]
            return report

        if plan.action != "search_then_answer" or not plan.search_requests:
            self.logger.log(
                "error",
                "LLM0 did not provide any search_requests. Aborting.",
                error=True,
            )
            report.steps = self.logger.events[:]
            return report

        # ---------- Step 2: Run multiple searches ----------
        all_results: list[SearchResult] = []
        for idx, sreq in enumerate(plan.search_requests, start=1):
            self.logger.log(
                "search",
                f"Running search #{idx} with query='{sreq.query}' when='{sreq.when}'.",
                data={"search_index": idx, "query": sreq.query, "when": sreq.when, "filters": sreq.filters.__dict__},
            )
            try:
                partial = self.search_client.search(sreq)
            except Exception as e:  # network / BingSift errors
                self.logger.log(
                    "error",
                    f"Search #{idx} failed: {e}",
                    error=True,
                    data={"search_index": idx, "query": sreq.query},
                )
                continue

            # Relabel IDs so they are unique across searches
            for r_index, r in enumerate(partial, start=1):
                r.id = f"s{idx}_r{r_index}"
                all_results.append(r)

            self.logger.log(
                "search",
                f"Search #{idx} returned {len(partial)} results.",
                data={"search_index": idx, "result_count": len(partial)},
            )

        if not all_results:
            self.logger.log(
                "final",
                "All searches failed or returned no results; aborting.",
                error=True,
            )
            report.steps = self.logger.events[:]
            return report

        report.search_results = all_results
        self.logger.log(
            "search",
            f"Total of {len(all_results)} results collected from "
            f"{len(plan.search_requests)} searches.",
        )

        # ---------- Step 3: LLM0 selects which results to read ----------
        self.logger.log("select", "LLM0 is selecting which results to read.")
        selection = call_llm0_select(self.llm0, question=question, search_results=all_results)
        self.logger.log(
            "select",
            f"LLM0 selected {len(selection.selected_ids)} results for deep reading.",
            data={"selected_ids": selection.selected_ids},
        )

        selected_map = {r.id: r for r in all_results}
        read_targets: list[SearchResult] = [
            selected_map[rid] for rid in selection.selected_ids if rid in selected_map
        ]

        if not read_targets:
            self.logger.log(
                "final",
                "LLM0 did not select any results to read; aborting.",
                error=True,
            )
            report.steps = self.logger.events[:]
            return report

        # ---------- Step 4: LLM1 summarizes selected articles ----------
        summaries: list[ArticleSummary] = []
        for r in read_targets:
            self.logger.log("summarize", f"Fetching and summarizing URL: {r.url}")
            try:
                text_content = self.search_client.fetch_page_excerpt(r.url)
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
                    html_excerpt=text_content,  # Contains extracted text, not HTML
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
            report.steps = self.logger.events[:]
            return report

        # ---------- Step 5: LLM0 synthesizes final answer ----------
        self.logger.log(
            "final",
            "LLM0 is synthesizing the final report from all summaries.",
        )
        final_answer = call_llm0_synthesize(
            llm=self.llm0,
            question=question,
            search_results=all_results,
            summaries=summaries,
        )
        report.final_answer = final_answer
        report.steps = self.logger.events[:]
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

    @staticmethod
    def _wrap_direct_answer(answer_text: str) -> "FinalAnswer":
        from .types import FinalAnswer

        return FinalAnswer(
            answer=answer_text,
            key_points=[],
            used_results=[],
            notes="Direct answer from LLM0 without web search.",
        )