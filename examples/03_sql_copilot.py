"""Example 03 — SQL copilot.

A copilot that learns your database. It remembers:

  * table + column definitions (semantic — long-lived facts)
  * frequently-run queries (episodic — recent events)
  * design decisions the team made about the schema (semantic, pinned)

Demonstrates:

  * mixing memory types in one agent
  * pinning high-value memories so they survive auto-decay
  * AUTO routing — the LLM picks the right strategy based on the query

Run:
    uv run python examples/03_sql_copilot.py
"""

from __future__ import annotations

import os

from z3rno import Z3rnoClient

AGENT_ID = "33333333-3333-3333-3333-333333333333"


def main() -> None:
    client = Z3rnoClient(
        base_url=os.environ.get("Z3RNO_BASE_URL", "http://localhost:8000"),
        api_key=os.environ.get("Z3RNO_API_KEY", "z3rno_sk_test_localdev"),
    )

    # --- Schema facts: long-lived, pinned ----------------------------------
    schema_facts = [
        ("table users", "users(id UUID PK, email TEXT UNIQUE NOT NULL, created_at TIMESTAMPTZ)"),
        ("table orders", "orders(id UUID PK, user_id UUID FK→users, total_cents BIGINT, placed_at TIMESTAMPTZ)"),
        ("table products", "products(sku TEXT PK, name TEXT, price_cents BIGINT, active BOOL)"),
    ]
    for label, ddl in schema_facts:
        client.store(
            agent_id=AGENT_ID,
            content=f"{label}: {ddl}",
            memory_type="semantic",
            metadata={"kind": "schema", "label": label},
            importance=0.9,    # high importance so it ranks well
            ttl_seconds=None,  # never expires
        )

    # --- A design decision the team made (pinned) --------------------------
    client.store(
        agent_id=AGENT_ID,
        content=(
            "Decision (2026-03-04): all monetary fields are *_cents BIGINT, never DECIMAL. "
            "Rationale: avoid scale-mismatch bugs when joining across services."
        ),
        memory_type="semantic",
        metadata={"kind": "decision", "topic": "money_columns"},
        importance=1.0,
    )

    # --- Recently-run queries (episodic, naturally decays) -----------------
    recent_queries = [
        "SELECT count(*) FROM orders WHERE placed_at > now() - interval '7 days';",
        "SELECT user_id, sum(total_cents) FROM orders GROUP BY user_id ORDER BY 2 DESC LIMIT 10;",
    ]
    for q in recent_queries:
        client.store(
            agent_id=AGENT_ID,
            content=q,
            memory_type="episodic",
            metadata={"kind": "recent_query"},
        )

    # --- Now: the user asks a question --------------------------------------
    user_q = "What columns does the orders table have, and why are amounts in cents?"
    print(f"USER: {user_q}\n")

    # AUTO routes — the LLM router will pick GRAPH or AUTO→VECTOR here.
    response = client.recall(agent_id=AGENT_ID, query=user_q, top_k=5)

    print(f"AGENT recalled {len(response.results)} memory/ies "
          f"(strategy={response.strategy_used}):")
    for r in response.results:
        kind = (r.metadata or {}).get("kind", "?")
        print(f"  [{kind:<12}] {r.content[:120]}{'…' if len(r.content) > 120 else ''}")

    print(
        "\nThe copilot now has enough context to answer accurately — the schema "
        "row tells it the columns; the decision row tells it the *why*."
    )

    client.close()


if __name__ == "__main__":
    main()
