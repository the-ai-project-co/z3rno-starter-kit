"""Example 04 — Code memory (Phase D).

Ingest a Python source file into Z3rno. The Phase D code-graph
extractor turns it into a function-level Memo graph (MODULE / CLASS /
FUNCTION / IMPORT nodes; DEFINES / IMPORTS / CALLS / INHERITS edges).
The new ``CODE`` retrieval strategy walks the graph to surface a
focal symbol plus its 1-hop neighborhood.

Requires the server to have these flags on:

    INGEST_ENABLED=true
    CODEGRAPH_ENABLED=true

Run:
    uv run python examples/04_code_memory.py
"""

from __future__ import annotations

import os
import time

import httpx
from z3rno import Z3rnoClient

AGENT_ID = "44444444-4444-4444-4444-444444444444"

# A small file we want the agent to remember. Realistic but compact.
SAMPLE_PY = '''
import os
from typing import List

class OrderService(BaseService):
    """Books, ships, and refunds orders."""

    def place(self, user_id: str, items: list) -> str:
        order_id = self._mint_id()
        self._charge(user_id, items)
        return order_id

    def refund(self, order_id: str) -> None:
        self._charge(order_id, refund=True)


def main():
    svc = OrderService()
    svc.place("u-1", ["sku-a"])
    svc.refund("o-1")
'''


def _ingest_text(base_url: str, api_key: str, *, text: str, filename: str) -> str:
    """Call POST /v1/ingest with kind='text' + a filename hint so the loader
    recognises the language. Returns the ingest job_id."""
    response = httpx.post(
        f"{base_url}/v1/ingest",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json={
            "kind": "text",
            "agent_id": AGENT_ID,
            "text": text,
            "filename": filename,           # filename drives language detection
            "content_type": "text/x-python",
        },
        timeout=30.0,
    )
    response.raise_for_status()
    return str(response.json()["job_id"])


def _wait_for_ingest(
    base_url: str, api_key: str, job_id: str, *, timeout_s: int = 30
) -> dict[str, object]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = httpx.get(
            f"{base_url}/v1/ingest/{job_id}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        r.raise_for_status()
        body = r.json()
        if body.get("status") in ("completed", "failed"):
            return body  # type: ignore[no-any-return]
        time.sleep(1.0)
    raise TimeoutError(f"ingest job {job_id} did not finish within {timeout_s}s")


def main() -> None:
    base_url = os.environ.get("Z3RNO_BASE_URL", "http://localhost:8000")
    api_key = os.environ.get("Z3RNO_API_KEY", "z3rno_sk_test_localdev")

    print("Ingesting sample Python source...")
    job_id = _ingest_text(base_url, api_key, text=SAMPLE_PY, filename="orders.py")
    print(f"  job_id={job_id}")
    summary = _wait_for_ingest(base_url, api_key, job_id)
    print(
        f"  status={summary['status']}  "
        f"memos_written={summary.get('codegraph_memos_written', '?')}  "
        f"edges_written={summary.get('codegraph_edges_written', '?')}"
    )

    if summary["status"] != "completed":
        print(f"  error: {summary.get('error')}")
        return

    # Now query the call graph via the CODE strategy.
    client = Z3rnoClient(base_url=base_url, api_key=api_key)
    print("\nWho calls OrderService.place?")
    response = client.recall(
        agent_id=AGENT_ID,
        query="OrderService.place",
        strategy="CODE",
        top_k=5,
    )
    for r in response.results:
        meta = r.metadata or {}
        kind = meta.get("codegraph_kind", "?")
        qname = meta.get("qualified_name", "?")
        print(f"  [{kind:<8}] {qname}")

    print("\nThe CODE strategy returns the focal symbol plus its 1-hop neighbors — "
          "good for 'what calls X?' or 'what does X depend on?' navigation.")
    client.close()


if __name__ == "__main__":
    main()
