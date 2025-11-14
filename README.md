# DeepSeeker


DeepSeeker is a small but capable deep‑search engine built around a simple idea: let one model think, let many models read. Instead of trying to shove everything into one giant prompt, DeepSeeker breaks the job into two cooperating roles:


**LLM0** acts as the strategist. It decides whether your question even needs searching. If it does, it plans search queries, asks for results, picks what should be read, and decides whether more rounds are necessary. When it's satisfied, it writes the final answer.


**LLM1** is the reader squad. Each LLM1 instance takes one document, summarizes it briefly, evaluates relevance, and sends back a tiny report. These run in parallel, so the cost stays predictable and fast.


Everything is held together by a lightweight JSON protocol written directly into the system prompt. No external servers. No heavy tool frameworks. The orchestrator simply parses the JSON and loops.


DeepSeeker works naturally with your own BingSift setup, but it's not tied to it—you can plug in any search provider as long as it returns basic metadata.


---


## How it feels to use


You ask a question, and DeepSeeker quietly spins up a miniature research workflow:


- Think first → search if necessary.
- Search → shortlist documents.
- Read those documents in parallel.
- Reflect → search again or conclude.


To you, it looks like a single command:


```bash
deepseeker run --question "What are the recent breakthroughs in LLM reasoning optimization?" \
--llm0-model gpt-4.1 \
--llm1-model gpt-4o-mini \
--api-key $OPENAI_KEY