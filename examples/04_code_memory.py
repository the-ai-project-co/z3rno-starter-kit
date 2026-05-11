"""Example 04 — Code memory (Phase D).

Ingest a Python source file into Z3rno. The Phase D code-graph
extractor turns it into a function-level Memo graph (MODULE / CLASS /
FUNCTION / IMPORT nodes; DEFINES / IMPORTS / CALLS / INHERITS edges).
The ``CODE`` retrieval strategy walks the graph to surface a focal
symbol plus its 1-hop neighborhood.

Requires the server to have these flags on:

    INGEST_ENABLED=true
    CODEGRAPH_ENABLED=true

Run:
    uv run python examples/04_code_memory.py
"""

from __future__ import annotations

import os
import time
from typing import Any

from z3rno import IngestJobStatus, Z3rnoClient

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


def _wait_for_ingest(
    client: Z3rnoClient, job_id: str, *, timeout_s: int = 30
) -> IngestJobStatus:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = client.get_ingest_status(job_id)
        if status.status in ("completed", "failed"):
            return status
        time.sleep(1.0)
    raise TimeoutError(f"ingest job {job_id} did not finish within {timeout_s}s")


def main() -> None:
    client = Z3rnoClient(
        base_url=os.environ.get("Z3RNO_BASE_URL", "http://localhost:8000"),
        api_key=os.environ.get("Z3RNO_API_KEY", "z3rno_sk_test_localdev"),
    )

    print("Ingesting sample Python source...")
    job = client.ingest_text(agent_id=AGENT_ID, text=SAMPLE_PY)
    print(f"  job_id={job.job_id}")

    status = _wait_for_ingest(client, job.job_id)
    print(
        f"  status={status.status}  "
        f"codegraph_memos_written={status.codegraph_memos_written}  "
        f"codegraph_edges_written={status.codegraph_edges_written}"
    )

    if status.status != "completed":
        print(f"  error: {status.error}")
        client.close()
        return

    print("\nWho calls OrderService.place?")
    response = client.recall(
        agent_id=AGENT_ID,
        query="OrderService.place",
        strategy="CODE",
        top_k=5,
    )
    for r in response.results:
        meta: dict[str, Any] = r.metadata or {}
        kind = meta.get("codegraph_kind", "?")
        qname = meta.get("qualified_name", "?")
        print(f"  [{kind:<8}] {qname}")

    print(
        "\nThe CODE strategy returns the focal symbol plus its 1-hop neighbors — "
        "good for 'what calls X?' or 'what does X depend on?' navigation."
    )
    client.close()


if __name__ == "__main__":
    main()
