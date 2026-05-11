# CLAUDE.md

## Project

z3rno-starter-kit is the public examples repository for [Z3rno](https://z3rno.dev). Five worked Python examples, each a single-file script. No shared utilities, no abstractions — the value is readability + copy-pasteability.

## Quick Reference

```bash
uv sync --dev                              # Install
uv run ruff check .                        # Lint
uv run ruff format .                       # Format
uv run mypy examples                       # Type check
uv run pytest                              # Smoke tests (every example imports + has main)
uv run python examples/01_chat_agent.py    # Run an example
```

## Architecture

- `examples/01..05_<name>.py` — five single-file demos, ordered roughly by complexity.
- `tests/test_examples_smoke.py` — imports every example module and asserts each exposes a callable `main()`. Cheap regression gate.
- No `src/` directory: this is not an importable library.

## Key Conventions

- Every script:
  - Reads `Z3RNO_BASE_URL` (default `http://localhost:8000`) and `Z3RNO_API_KEY` (default `z3rno_sk_test_localdev`).
  - Uses a hard-coded UUID for `agent_id` per example so re-runs accumulate state — re-runs are conversations, not resets.
  - Exposes a top-level `main()` so the smoke test can import without running.
- Forge verbs (`ingest`, `distill`, `refine`) call the server's HTTP endpoints directly via `httpx` — SDK wrappers ship later.
- No example imports another. Copy-paste must work.
- Ruff + mypy strict. `print()` is fine (T201 ignored for `examples/`).
- Conventional commits.

## Phase E acceptance bar

> Starter kit demos run end-to-end against a fresh Docker Compose with one env var (`LLM_API_KEY`).

The structural deliverable is met when `uv sync && uv run pytest` is green and the five examples import cleanly. The interactive runs are documented in the README; CI verifies only the import gate.
