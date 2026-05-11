"""Example 02 — Customer support memory.

Each user message is stored under a ``user_id`` tag so the support
agent can surface that user's prior tickets — *and only that user's
tickets* — on the next contact. Demonstrates:

  * per-user filtering via ``filters`` on ``recall``
  * pinning the ``LEXICAL`` strategy when the query is an exact-ish
    keyword lookup (ticket numbers, product SKUs)
  * ``forget`` for GDPR right-to-be-forgotten

Run:
    uv run python examples/02_customer_support.py
"""

from __future__ import annotations

import os

from z3rno import Z3rnoClient

AGENT_ID = "22222222-2222-2222-2222-222222222222"

# Three customers writing in. Hard-coded UUIDs so re-runs reuse the same rows.
ALICE = "aaaaaaaa-1111-1111-1111-aaaaaaaaaaaa"
BOB = "bbbbbbbb-2222-2222-2222-bbbbbbbbbbbb"


def _store_ticket(client: Z3rnoClient, user_id: str, body: str, ticket: str) -> None:
    client.store(
        agent_id=AGENT_ID,
        user_id=user_id,
        content=body,
        memory_type="episodic",
        metadata={"kind": "support_ticket", "ticket_id": ticket},
    )


def main() -> None:
    client = Z3rnoClient(
        base_url=os.environ.get("Z3RNO_BASE_URL", "http://localhost:8000"),
        api_key=os.environ.get("Z3RNO_API_KEY", "z3rno_sk_test_localdev"),
    )

    # --- Seed a few tickets across two users --------------------------------
    _store_ticket(client, ALICE, "Dashboard was slow this morning around 9am UTC.", "T-001")
    _store_ticket(client, ALICE, "Export-to-CSV timed out for the Q3 report.", "T-002")
    _store_ticket(client, BOB, "Pricing page is showing the wrong tier on mobile.", "T-003")

    # --- Alice writes in again ---------------------------------------------
    incoming = "I'm having issues with the dashboard again."
    print(f"ALICE: {incoming}")

    # Filter to *only* this user's history. The server enforces RLS by
    # org_id; the user_id filter narrows further inside the tenant.
    response = client.recall(
        agent_id=AGENT_ID,
        query=incoming,
        top_k=3,
        filters={"user_id": ALICE},
        strategy="LEXICAL",  # ticket bodies are keyword-rich; lexical excels
    )
    print(f"\nFound {len(response.results)} matching ticket(s) for Alice "
          f"(strategy={response.strategy_used}):")
    for r in response.results:
        ticket = (r.metadata or {}).get("ticket_id", "?")
        print(f"  [{ticket}] {r.content}")

    # Sanity check: a query about pricing should NOT surface Bob's ticket
    # when scoped to Alice.
    cross_check = client.recall(
        agent_id=AGENT_ID,
        query="pricing tier mobile",
        top_k=3,
        filters={"user_id": ALICE},
        strategy="LEXICAL",
    )
    print(f"\nAlice asking about 'pricing tier mobile' → {len(cross_check.results)} hit(s) "
          "(should be 0 — Bob's ticket is scoped to him).")

    # --- GDPR: Bob exercises his right to be forgotten ----------------------
    # In practice you'd page through his memories first; this is the spirit.
    print("\nBob exercises right-to-be-forgotten (cascade)...")
    bob_history = client.recall(agent_id=AGENT_ID, query="*", top_k=10, filters={"user_id": BOB})
    for r in bob_history.results:
        client.forget(
            agent_id=AGENT_ID,
            memory_id=str(r.memory_id),
            hard_delete=True,
            reason="GDPR Art. 17 request",
        )
    print(f"  Removed {len(bob_history.results)} ticket(s) for Bob.")

    client.close()


if __name__ == "__main__":
    main()
