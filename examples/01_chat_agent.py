"""Example 01 — Chat agent memory.

A multi-turn chat that remembers user preferences across runs.

Demonstrates the two verbs that ~80% of agent-memory use cases need:
``store`` to write a turn, ``recall`` to retrieve relevant context
for the next turn. Re-run the script and the agent picks up where it
left off — re-runs are conversations, not resets.

Run:
    uv run python examples/01_chat_agent.py
"""

from __future__ import annotations

import os

from z3rno import Z3rnoClient

# Stable per-example agent id so re-runs accumulate state.
AGENT_ID = "11111111-1111-1111-1111-111111111111"


def main() -> None:
    client = Z3rnoClient(
        base_url=os.environ.get("Z3RNO_BASE_URL", "http://localhost:8000"),
        api_key=os.environ.get("Z3RNO_API_KEY", "z3rno_sk_test_localdev"),
    )

    # --- Turn 1: user shares a preference -----------------------------------
    user_msg = "I prefer dark mode and weekly digest emails."
    print(f"USER: {user_msg}")
    client.store(
        agent_id=AGENT_ID,
        content=user_msg,
        memory_type="semantic",  # stable preferences live in semantic memory
        metadata={"role": "user", "kind": "preference"},
    )
    print("AGENT: Got it — dark mode + weekly digests.\n")

    # --- Turn 2: user asks something the agent should answer from memory ----
    user_msg = "Hey, can you remind me what email cadence I picked?"
    print(f"USER: {user_msg}")
    response = client.recall(
        agent_id=AGENT_ID,
        query=user_msg,
        top_k=3,
    )
    if response.results:
        top = response.results[0]
        print(f"AGENT: Based on what you told me — `{top.content}`")
        print(f"       (recalled via strategy={response.strategy_used}, "
              f"score={top.relevance_score:.2f})\n")
    else:
        print("AGENT: I don't have anything in memory yet — try running this script "
              "twice in a row.\n")

    # --- Turn 3: write the new exchange so memory keeps growing -------------
    client.store(
        agent_id=AGENT_ID,
        content=f"User asked: {user_msg}. Agent answered from semantic memory.",
        memory_type="episodic",
        metadata={"role": "agent", "turn": "3"},
    )

    client.close()


if __name__ == "__main__":
    main()
