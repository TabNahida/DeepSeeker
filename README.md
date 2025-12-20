# DeepSeeker — Lightweight Multi-LLM Deep Research Engine

DeepSeeker is a modular deep-research system inspired by OpenAI’s **Deep Research**, designed for transparent reasoning, iterative search, and multi-model collaboration.

It integrates:
- **LLM0** — Planner & Final Analyst (high-quality model)
- **LLM1** — Reader & Summarizer (cost-efficient model)
- **BingSift** — Web search + result extraction backend

DeepSeeker runs a full research pipeline:
1. **LLM0** analyzes the question and decides whether to perform web search.  
2. If search is required, DeepSeeker uses **BingSift** to fetch SERP results.  
3. **LLM0** inspects results (title + snippet) and chooses which pages require deep reading.  
4. **LLM1** reads each selected page and produces structured summaries.  
5. **LLM0** synthesizes all summaries and generates a final, well-structured report.

All LLM responses follow a **lightweight JSON protocol** (MCP-like, but much simpler), ensuring predictable, controllable system behavior.

---

## Features

- **Two-LLM architecture** for optimal cost/performance.
- **Deterministic JSON protocol** for plan/selection/summarization/synthesis stages.
- **Extensible orchestrator** written in Python.
- **Search powered by BingSift** (keyword filtering, domain control, freshness filters).
- **Human-readable step logging** for full transparency.
- **CLI utilities** for testing each stage:
  - `plan` — LLM0 planning behaviour
  - `search` — BingSift integration
  - `run` — full research pipeline

---

## Installation

```bash
pip install -r requirements.txt
````

Set environment variables:

```bash
export OPENAI_API_KEY="your-key"
# Optional: custom endpoint
# export OPENAI_BASE_URL="https://your-host/v1"
```

## Configuration

DeepSeeker supports configuration via JSON file or environment variables.

### Option 1: Configuration File (Recommended)

Create a default configuration file:

```bash
python -m deepseeker.cli init
```

This creates `config.json` in your current directory:

```json
{
  "api_key": "your-openai-api-key",
  "base_url": "https://api.openai.com/v1",
  "llm0": {
    "model": "gpt-5.1-thinking",
    "max_output_tokens": 4096
  },
  "llm1": {
    "model": "gpt-4o-mini",
    "max_output_tokens": 1536
  },
  "search_max_results": 10,
  "search_freshness": "week"
}
```

**Automatic Detection**: If `config.json` exists in the current directory, it will be automatically used by all commands.

**Custom Config File**: You can also specify a custom config file:

```bash
python -m deepseeker.cli --config custom_config.json run --question "your question"
```

### Option 2: Environment Variables

If no `config.json` file is found, DeepSeeker falls back to environment variables:

```bash
# API Configuration
export OPENAI_API_KEY="your-api-key"
export OPENAI_BASE_URL="https://api.openai.com/v1"  # Optional

# LLM Configuration
export DEEPSEEKER_LLM0_MODEL="gpt-5.1-thinking"
export DEEPSEEKER_LLM0_MAX_TOKENS="4096"
export DEEPSEEKER_LLM1_MODEL="gpt-4o-mini"
export DEEPSEEKER_LLM1_MAX_TOKENS="1536"

# Search Configuration
export DEEPSEEKER_SEARCH_MAX_RESULTS="10"
export DEEPSEEKER_SEARCH_FRESHNESS="week"
```

**Note**: To use environment variables, either delete `config.json` or specify a different config file with `--config`.

### Priority Order

Configuration is loaded in this priority order:
1. Explicit `--config` parameter
2. Default `config.json` file (if exists)
3. Environment variables
4. Built-in defaults

### Configuration Example

Here's a complete example of a `config.json` file:

```json
{
  "api_key": "sk-your-openai-api-key-here",
  "base_url": "https://api.openai.com/v1",
  "llm0": {
    "model": "gpt-4o",
    "max_output_tokens": 4096
  },
  "llm1": {
    "model": "gpt-4o-mini",
    "max_output_tokens": 1536
  },
  "search_max_results": 15,
  "search_freshness": "week"
}
```

**Tips**:
- Leave `api_key` empty (`""`) to use environment variable `OPENAI_API_KEY`
- Leave `base_url` empty (`""`) to use default OpenAI endpoint
- You can use different config files for different projects:
  ```bash
  deepseeker --config project1.json run --question "..."
  deepseeker --config project2.json run --question "..."
  ```

---

## CLI Usage

### 1. Initialize Configuration

```bash
# Create default config.json
python -m deepseeker.cli init

# Create custom config file
python -m deepseeker.cli init --output my_config.json
```

### 2. Search

```bash
# Uses config.json or environment variables
python -m deepseeker.cli search --query "intel earnings"

# Override config settings
python -m deepseeker.cli search --query "intel earnings" --when week --max-results 20
```

### 3. Planning

```bash
# Uses config.json or environment variables
python -m deepseeker.cli plan --question "Explain ARM vs RISC-V for servers."

# Use custom config file
python -m deepseeker.cli --config custom.json plan --question "your question"
```

### 4. Run full pipeline

```bash
# Uses config.json or environment variables
python -m deepseeker.cli run --question "Latest advances in large-scale model training using distributed computing and GPU clusters?"

# Use custom config file
python -m deepseeker.cli --config custom.json run --question "your question"
```

You will see:

* Markdown final answer
* Key summary points
* A full JSON log of internal steps

## Lightweight JSON Protocol

DeepSeeker enforces strict JSON outputs:

### LLM0 Plan

```json
{
  "action": "direct_answer" | "search_then_answer",
  "direct_answer": "...",
  "search": {
    "query": "...",
    "when": "week",
    "include": [],
    "exclude": [],
    "allow_domains": [],
    "deny_domains": [],
    "max_results": 10
  },
  "notes": "..."
}
```

### LLM1 Summary

```json
{
  "title": "...",
  "summary": "...",
  "key_points": ["..."],
  "relevance_score": 0.0,
  "notes": "..."
}
```

### LLM0 Final Synthesis

```json
{
  "answer": "markdown report",
  "key_points": [],
  "used_results": [],
  "notes": "..."
}
```

## Roadmap

- [x] Two-LLM orchestration
- [x] BingSift search integration
- [x] Enhanced Log System
- [ ] WebUI
- [ ] Deep Iterative Search
- [ ] Smart Page Reader
- [ ] Plugin System

## License

MIT License (or replace with your preferred license).

