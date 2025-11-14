from __future__ import annotations
import orjson, anyio
from typing import List, Optional
from .llm_client import OpenAIStyleClient
from .schema import (
    AppConfig, ControllerDecision, SearchPlan, ReadSelection, SearchDoc, ReaderReport, OrchestratorState
)
from .prompts import CFJ_CONTROLLER
from .utils import new_uuid, now_iso
from .search.bingsift import BingSiftProvider

async def orchestrate_question(question: str, cfg: AppConfig) -> dict:
    llm0 = OpenAIStyleClient(cfg.llm0.base_url, cfg.llm0.api_key)
    llm1 = OpenAIStyleClient(cfg.llm1.base_url, cfg.llm1.api_key)

    search = BingSiftProvider(cfg.search.bingsift_endpoint)

    state = OrchestratorState(question=question)

    sys_msg = {"role": "system", "content": CFJ_CONTROLLER}

    # Log File
    log_path = cfg.orchestrator.save_log_path
    async with await anyio.open_file(log_path, "a") as logf:
        async def log(entry: dict):
            await logf.write(orjson.dumps(entry).decode()+"\n")

        # Round 0: initial decision
        messages = [sys_msg, {"role": "user", "content": question}]
        decision_raw = await llm0.achat_json(cfg.llm0.model, messages, json_mode=True)
        decision = ControllerDecision(**decision_raw)
        await log({"t": now_iso(), "round": 0, "decision": decision_raw})

        messages.append({"role": "assistant", "content": orjson.dumps(decision_raw).decode()})

        final_answer = None
        for round_idx in range(cfg.orchestrator.max_rounds):
            state.round_index = round_idx

            if decision.action == "answer":
                final_answer = decision.direct_answer or ""
                break

            if decision.action == "search":
                sp: SearchPlan = decision.search_plan  # type: ignore
                # Multi-search
                pool = await search.search_multi([q.model_dump() for q in sp.queries], per_query_limit=sp.per_query_limit)
                state.search_pool = pool
                await log({"t": now_iso(), "round": round_idx, "search_pool": [d.model_dump() for d in pool]})
                # Report back to LLM0
                messages.extend([
                    {"role": "user", "content": f"SEARCH_RESULTS:\n" + orjson.dumps([d.model_dump() for d in pool]).decode()}
                ])
                decision_raw = await llm0.achat_json(cfg.llm0.model, messages, json_mode=True)
                decision = ControllerDecision(**decision_raw)
                await log({"t": now_iso(), "round": round_idx, "decision": decision_raw})
                messages.append({"role": "assistant", "content": orjson.dumps(decision_raw).decode()})

            if decision.action == "select_for_read":
                rs: ReadSelection = decision.read_selection  # type: ignore
                # Maching SearchDoc
                docs_map = {d.doc_id: d for d in state.search_pool}
                targets: List[SearchDoc] = [docs_map[x.doc_id] for x in rs.to_read if x.doc_id in docs_map]
                # Parallel Reader Calls
                from .reader import run_parallel_readers
                reports: List[ReaderReport] = await run_parallel_readers(
                    llm1, cfg.llm1.model, targets, concurrency=cfg.orchestrator.concurrency
                )
                state.reports.extend(reports)
                await log({"t": now_iso(), "round": round_idx, "reports": [r.model_dump() for r in reports]})

                # Report back to LLM0
                messages.append({"role": "user", "content": f"READER_REPORTS:\n" + orjson.dumps([r.model_dump() for r in reports]).decode()})
                decision_raw = await llm0.achat_json(cfg.llm0.model, messages, json_mode=True)
                decision = ControllerDecision(**decision_raw)
                await log({"t": now_iso(), "round": round_idx, "decision": decision_raw})
                messages.append({"role": "assistant", "content": orjson.dumps(decision_raw).decode()})

            if decision.action == "stop":
                final_answer = decision.direct_answer or ""
                break
        else:
            # Reached max rounds, force finalize
            fin_raw = await llm0.achat_json(cfg.llm0.model, messages + [
                {"role": "user", "content": "Finalize succinct result as 'stop' with direct_answer."}
            ], json_mode=True)
            fin = ControllerDecision(**fin_raw)
            final_answer = fin.direct_answer or ""
            await log({"t": now_iso(), "round": state.round_index, "forced_stop": fin_raw})

    return {
        "answer": final_answer,
        "rounds": state.round_index + 1,
        "reports": [r.model_dump() for r in state.reports],
    }