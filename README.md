# Research Swarm

A local-first **multi-agent research orchestrator** in your terminal.
Ask one question, watch N researcher agents fan out in parallel with
different lenses, then get a single cited markdown report.

```
you: "is fusion close?"
  ├─ academic ──► web_search ──► findings + cites
  ├─ skeptic ───► web_search ──► findings + cites
  ├─ practitioner ► web_search ─► findings + cites
  └─ futurist ──► web_search ──► findings + cites
        │ synthesize + critic pass
        ▼
  reports/20260101-120000-is-fusion-close.md
```

Zero required dependencies (stdlib only). Works offline out of the box
with `--provider mock`, plugs into OpenAI or Ollama when you want brains.

## Quickstart

```bash
cd ~/ai-orchestrator

# env lives inside the project
uv venv 2>/dev/null || python3 -m venv .venv
source .venv/bin/activate
pip install -e .

# offline demo, no key needed
python -m research_swarm "is small modular nuclear economical?" --depth quick --provider mock

# chat mode
python -m research_swarm --interactive --angles 4 --depth standard --provider mock
```

With uv: `uv run python -m research_swarm "..." --depth quick --provider mock`

## Real brains

```bash
export OPENAI_API_KEY=sk-...            # + optional OPENAI_BASE_URL, RESEARCH_MODEL
python -m research_swarm "what breaks at 10M-doc RAG?" --provider openai --depth standard

# local Ollama
export RESEARCH_PROVIDER=ollama         # or --provider ollama
python -m research_swarm "best local LLM for tool use?" --provider ollama
```

Live web search uses DuckDuckGo HTML (no key). If network fails it falls
back to labeled offline results. Force offline with `--offline` or
`RESEARCH_OFFLINE=1`. `--provider mock` auto-runs offline for speed;
set `RESEARCH_OFFLINE=0` to test mock brains + live search.

## Angles

`--list-angles` shows the lens presets: academic, skeptic, practitioner,
futurist, historian, operator. `--angles N` (1-8) cycles them so every
run gets named viewpoints. Depth controls tool rounds + critic pass:

| depth | rounds | critic |
|---|---|---|
| quick | 1 | no |
| standard | 2 | yes |
| deep | 3 | yes |

## Layout

- `src/research_swarm/config.py` — angles, depths, run config
- `src/research_swarm/providers.py` — mock / OpenAI-compat / Ollama
- `src/research_swarm/tools.py` — web_search, web_fetch, calc
- `src/research_swarm/agents.py` — ReAct researcher, synthesize, critic
- `src/research_swarm/orchestrator.py` — asyncio fan-out
- `src/research_swarm/cli.py` — one-shot + REPL
- `tests/test_swarm.py` — stdlib unittest, no pytest needed

## Tests

```bash
source .venv/bin/activate
python -m unittest discover -s tests -v
```

## Roadmap ideas

- streaming per-agent output + token/cost meter
- `--format memo|bullets|debate` report styles
- Tavily/Brave search plugin, SQLite cache
- eval harness: same query across providers, judge diffs
