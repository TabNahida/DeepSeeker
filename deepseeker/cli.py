from __future__ import annotations
import typer, yaml, anyio
from rich import print
from typing import Optional
from .config import AppConfig, LLMConfig, SearchConfig, OrchestratorConfig
from .orchestrator import orchestrate_question

app = typer.Typer(add_completion=False)

@app.command()
def run(
    question: str = typer.Option(..., help="Your question"),
    config: Optional[str] = typer.Option(None, help="YAML config path"),
    llm0_model: Optional[str] = typer.Option(None),
    llm1_model: Optional[str] = typer.Option(None),
    api_key: Optional[str] = typer.Option(None),
    base_url: str = typer.Option("https://api.openai.com/v1"),
    bingsift_endpoint: str = typer.Option("http://localhost:8787/search"),
    max_rounds: int = typer.Option(3),
    per_query_limit: int = typer.Option(8),
    concurrency: int = typer.Option(6),
):
    if config:
        cfg = AppConfig(**yaml.safe_load(open(config, "r", encoding="utf-8")))
    else:
        if not api_key or not llm0_model or not llm1_model:
            raise typer.BadParameter("Provide --config or minimal --api-key, --llm0-model, --llm1-model")
        cfg = AppConfig(
            llm0=LLMConfig(base_url=base_url, api_key=api_key, model=llm0_model),
            llm1=LLMConfig(base_url=base_url, api_key=api_key, model=llm1_model),
            search=SearchConfig(bingsift_endpoint=bingsift_endpoint, per_query_limit=per_query_limit),
            orchestrator=OrchestratorConfig(max_rounds=max_rounds, concurrency=concurrency),
        )

    async def _main():
        out = await orchestrate_question(question, cfg)
        print("\n[bold green]Final Answer[/bold green]:\n", out["answer"])
        print("\n[dim]Reports collected:[/dim]", len(out.get("reports", [])))

    anyio.run(_main)