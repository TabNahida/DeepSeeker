from __future__ import annotations

import argparse
import json
import sys

from .config import load_llm_configs
from .logging_utils import StepLogger
from .llm_client import JsonLLMClient
from .orchestrator import DeepSeekerOrchestrator
from .search_client import SearchClient


def cmd_search(args: argparse.Namespace) -> int:
    llm0_cfg, llm1_cfg = load_llm_configs()  # not needed here, but kept for symmetry
    search_client = SearchClient()
    logger = StepLogger(verbose=True)

    from .types import SearchFilters, SearchRequest

    req = SearchRequest(
        query=args.query,
        when=args.when,
        filters=SearchFilters(),
        max_results=args.max_results,
    )

    logger.log("search", f"Searching for query='{req.query}', when='{req.when}'.")
    try:
        results = search_client.search(req)
    except Exception as e:
        logger.log("error", f"Search failed: {e}", error=True)
        return 1

    logger.log("search", f"Got {len(results)} results.")
    print(json.dumps([r.__dict__ for r in results], ensure_ascii=False, indent=2))
    return 0


def cmd_plan(args: argparse.Namespace) -> int:
    from .llm_client import call_llm0_plan

    llm0_cfg, _ = load_llm_configs()
    llm0 = JsonLLMClient(llm0_cfg)
    logger = StepLogger(verbose=True)

    logger.log("plan", "Calling LLM0 planning endpoint.")
    plan = call_llm0_plan(llm0, question=args.question)
    print(json.dumps(plan.__dict__, ensure_ascii=False, indent=2))
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    llm0_cfg, llm1_cfg = load_llm_configs()
    llm0 = JsonLLMClient(llm0_cfg)
    llm1 = JsonLLMClient(llm1_cfg)
    search_client = SearchClient()
    logger = StepLogger(verbose=True)

    orchestrator = DeepSeekerOrchestrator(
        llm0=llm0,
        llm1=llm1,
        search_client=search_client,
        logger=logger,
    )

    report = orchestrator.run(question=args.question)

    # Print human-readable summary + JSON
    if report.final_answer:
        print("\n===== FINAL ANSWER (Markdown) =====\n")
        print(report.final_answer.answer)
        print("\n===== KEY POINTS =====\n")
        for idx, kp in enumerate(report.final_answer.key_points, start=1):
            print(f"{idx}. {kp}")

    print("\n===== RAW STEPS (JSON) =====\n")
    print(logger.to_json())
    return 0


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="deepseeker", description="DeepSeeker research CLI")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # search
    p_search = subparsers.add_parser("search", help="Test BingSift search only.")
    p_search.add_argument("--query", required=True, help="Search query.")
    p_search.add_argument(
        "--when",
        default="week",
        choices=["day", "week", "month", "any"],
        help="Freshness filter for Bing search.",
    )
    p_search.add_argument(
        "--max-results",
        type=int,
        default=10,
        help="Maximum number of results to return.",
    )
    p_search.set_defaults(func=cmd_search)

    # plan
    p_plan = subparsers.add_parser(
        "plan",
        help="Test LLM0 planning (direct answer vs. search).",
    )
    p_plan.add_argument("--question", required=True, help="User research question.")
    p_plan.set_defaults(func=cmd_plan)

    # run
    p_run = subparsers.add_parser(
        "run",
        help="Run the full DeepSeeker pipeline for one question.",
    )
    p_run.add_argument("--question", required=True, help="User research question.")
    p_run.set_defaults(func=cmd_run)

    args = parser.parse_args(argv)
    return args.func(args)


if __name__ == "__main__":
    raise SystemExit(main())
