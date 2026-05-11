# z3rno-starter-kit

Five worked examples showing how to build with [Z3rno](https://z3rno.dev). Each example is a single Python script you can read top-to-bottom and run end-to-end.

| # | Example | What it demonstrates | Verbs used |
|---|---|---|---|
| 01 | [Chat agent memory](examples/01_chat_agent.py) | Multi-turn chat that remembers user preferences across sessions. | `store`, `recall` |
| 02 | [Customer support](examples/02_customer_support.py) | Per-user ticket history; surfacing relevant past issues. | `store`, `recall` (`LEXICAL`), `forget` |
| 03 | [SQL copilot](examples/03_sql_copilot.py) | Schema-aware copilot that remembers tables, frequent queries, and prior decisions. | `store`, `recall` (`AUTO` + `ASK`) |
| 04 | [Code memory](examples/04_code_memory.py) | Ingest a code file, build a function-level graph, query via the `CODE` strategy. | `ingest`, `recall` (`CODE`) |
| 05 | [Research notebook](examples/05_research_notebook.py) | Ingest several notes/URLs, distill the graph, refine for quality, then recall summaries. | `ingest`, `distill`, `refine`, `recall` |

## Quickstart

```bash
# 1. Boot the Z3rno stack (from a sibling checkout of z3rno-server)
cd ../z3rno-server && make dev-up && cd -

# 2. Set the one env var you need
export LLM_API_KEY=sk-...                  # OpenAI / Anthropic key
export OPENAI_API_KEY=$LLM_API_KEY          # alias the server reads
export Z3RNO_API_KEY=z3rno_sk_test_localdev # default dev key

# 3. Install
uv sync --dev

# 4. Run any example
uv run python examples/01_chat_agent.py
```

Examples 04 and 05 use Phase A/B/D features. Enable them in the server before running:

```bash
export INGEST_ENABLED=true
export DISTILL_ENABLED=true
export REFINE_ENABLED=true
export CODEGRAPH_ENABLED=true   # for example 04
docker compose -f ../z3rno-server/docker-compose.dev.yml restart server worker
```

## Repo layout

```
z3rno-starter-kit/
├── examples/
│   ├── 01_chat_agent.py
│   ├── 02_customer_support.py
│   ├── 03_sql_copilot.py
│   ├── 04_code_memory.py
│   └── 05_research_notebook.py
├── tests/
│   └── test_examples_smoke.py   # each example imports & has a main() callable
└── README.md
```

Each example is **single-file, no shared utilities, no abstractions**. The whole point is to be readable in one sitting.

## Conventions

- All scripts read `Z3RNO_BASE_URL` (default `http://localhost:8000`) and `Z3RNO_API_KEY` (default `z3rno_sk_test_localdev`).
- Agent IDs are stable UUIDs hard-coded per example so re-running picks up the same memories — re-runs are conversations, not fresh starts.
- Forge verbs (`ingest`, `distill`, `refine`) are called via raw HTTP because the SDK wrappers are queued for the next SDK release. See the canonical [verb reference](https://docs.z3rno.dev/concepts/verbs) for the surface map.

## License

Apache 2.0.
