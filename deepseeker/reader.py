from __future__ import annotations
import anyio
from typing import List
from .llm_client import OpenAIStyleClient
from .schema import ReaderReport, SearchDoc
from .prompts import CFJ_READER

async def run_single_reader(client: OpenAIStyleClient, model: str, doc: SearchDoc) -> ReaderReport:
    sys = {"role": "system", "content": CFJ_READER}
    user = {"role": "user", "content": f"Read this item and produce a CFJ reader_report JSON.\nURL: {doc.url}\nTITLE: {doc.title}\nSNIPPET: {doc.snippet or ''}"}
    out = await client.achat_json(model, [sys, user], json_mode=True)
    return ReaderReport(**out)

async def run_parallel_readers(client: OpenAIStyleClient, model: str, docs: List[SearchDoc], concurrency: int = 6) -> List[ReaderReport]:
    results: List[ReaderReport] = []
    async def worker(doc: SearchDoc):
        try:
            rep = await run_single_reader(client, model, doc)
            results.append(rep)
        except Exception as e:
            # Return a negative report on error
            results.append(ReaderReport(
                doc_id=doc.doc_id,
                source_url=str(doc.url),
                title=doc.title,
                verdict="not_relevant",
                reliability={"rating": 0.0, "reasons": f"reader error: {e}"},
                key_points=[],
                mini_summary="",
                citation=str(doc.url),
            ))

    async with anyio.create_task_group() as tg:
        for d in docs:
            tg.start_soon(worker, d)
    return results