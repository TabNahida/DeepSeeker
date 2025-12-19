from __future__ import annotations

import argparse
import json
import sys
from dataclasses import asdict

from .config import load_llm_configs, load_full_config, create_default_config_file
from .logging_utils import StepLogger
from .llm_client import JsonLLMClient
from .orchestrator import DeepSeekerOrchestrator
from .search_client import SearchClient


def cmd_search(args: argparse.Namespace) -> int:
    # Load config with optional config file
    config = load_full_config(args.config)
    
    # Use config values if not overridden by command line args
    max_results = args.max_results if args.max_results is not None else config.search_max_results
    when = args.when if args.when is not None else config.search_freshness
    
    search_client = SearchClient()
    logger = StepLogger(verbose=True, debug=args.debug)

    from .types import SearchFilters, SearchRequest

    req = SearchRequest(
        query=args.query,
        when=when,
        filters=SearchFilters(),
        max_results=max_results,
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

    llm0_cfg, _ = load_llm_configs(args.config)
    logger = StepLogger(verbose=True, debug=args.debug)
    llm0 = JsonLLMClient(llm0_cfg, logger=logger)

    logger.log("plan", "Calling LLM0 planning endpoint.")
    plan = call_llm0_plan(llm0, question=args.question)
    print(json.dumps(asdict(plan), ensure_ascii=False, indent=2))
    
    # Save log
    full_log_path = logger.save_full_log()
    print(f"\nLog saved to: {full_log_path}")
    return 0


def cmd_run(args: argparse.Namespace) -> int:
    llm0_cfg, llm1_cfg = load_llm_configs(args.config)
    llm0 = JsonLLMClient(llm0_cfg)
    llm1 = JsonLLMClient(llm1_cfg)
    search_client = SearchClient()
    logger = StepLogger(verbose=True, debug=args.debug)

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
    
    # Save full log with LLM I/O records
    full_log_path = logger.save_full_log()
    summary = logger.get_summary()
    
    print(f"\n===== SESSION SUMMARY =====")
    print(f"Total steps: {summary['total_steps']}")
    print(f"LLM calls: {summary['total_llm_calls']}")
    print(f"Errors: {summary['errors']}")
    print(f"Full log saved to: {full_log_path}")
    print(f"Console log saved to: {summary['log_file']}")
    
    return 0


def cmd_init(args: argparse.Namespace) -> int:
    """Create a default configuration file."""
    try:
        config_path = create_default_config_file(args.output)
        print(f"Created default configuration file: {config_path}")
        print("\nYou can customize this file and use it with:")
        print(f"  deepseeker --config {config_path} run --question \"your question\"")
        return 0
    except Exception as e:
        print(f"Error creating config file: {e}", file=sys.stderr)
        return 1


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="deepseeker", description="DeepSeeker research CLI")
    parser.add_argument("--debug", action="store_true", help="Enable DEBUG logging for detailed LLM I/O records")
    parser.add_argument("--config", help="Path to JSON configuration file")
    subparsers = parser.add_subparsers(dest="command", required=True)

    # init - create config file
    p_init = subparsers.add_parser("init", help="Create a default configuration file.")
    p_init.add_argument("--output", default="deepseeker_config.json", help="Output path for config file.")
    p_init.set_defaults(func=cmd_init)

    # search
    p_search = subparsers.add_parser("search", help="Test BingSift search only.")
    p_search.add_argument("--query", required=True, help="Search query.")
    p_search.add_argument(
        "--when",
        default=None,
        choices=["day", "week", "month", "year", "any"],
        help="Freshness filter for Bing search (overrides config).",
    )
    p_search.add_argument(
        "--max-results",
        type=int,
        default=None,
        help="Maximum number of results to return (overrides config).",
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
