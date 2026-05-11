"""Example 05 — Research notebook (full Forge loop).

Walks the entire Forge pipeline: ingest several notes → distill
(extract entities + relationships into the graph) → refine (dedupe +
reweight) → recall via the GRAPH strategy.

This is the most ambitious example — it touches every Phase A/B/D
verb. Requires the server flags:

    INGEST_ENABLED=true
    DISTILL_ENABLED=true
    REFINE_ENABLED=true
    OPENAI_API_KEY=sk-...    # the Forge needs an LLM for extraction

Run:
    uv run python examples/05_research_notebook.py
"""

from __future__ import annotations

import os
import time

import httpx
from z3rno import Z3rnoClient

AGENT_ID = "55555555-5555-5555-5555-555555555555"

# Three short research notes — small enough to keep distill cost low,
# big enough to produce a graph with multiple connected entities.
NOTES = [
    (
        "ada-bio.md",
        (
            "Ada Lovelace (1815-1852) was an English mathematician. She worked with "
            "Charles Babbage on the Analytical Engine and is widely credited with "
            "writing the first computer program. Her mentor was Mary Somerville."
        ),
    ),
    (
        "babbage-bio.md",
        (
            "Charles Babbage designed the Analytical Engine, a mechanical general-purpose "
            "computer. He collaborated extensively with Ada Lovelace, whose translation "
            "of Menabrea's paper included a method for computing Bernoulli numbers."
        ),
    ),
    (
        "somerville-bio.md",
        (
            "Mary Somerville was a Scottish scientist and writer. She tutored Ada Lovelace "
            "in mathematics and championed women's education. She corresponded with "
            "Charles Babbage about scientific computation."
        ),
    ),
]


def _post(
    path: str, base_url: str, api_key: str, body: dict[str, object]
) -> dict[str, object]:
    r = httpx.post(
        f"{base_url}{path}",
        headers={"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"},
        json=body,
        timeout=60.0,
    )
    r.raise_for_status()
    return r.json()  # type: ignore[no-any-return]


def _wait_for_job(
    base_url: str, api_key: str, *, path: str, timeout_s: int = 120
) -> dict[str, object]:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        r = httpx.get(
            f"{base_url}{path}",
            headers={"Authorization": f"Bearer {api_key}"},
            timeout=10.0,
        )
        r.raise_for_status()
        body = r.json()
        if body.get("status") in ("completed", "failed", "rejected"):
            return body  # type: ignore[no-any-return]
        time.sleep(2.0)
    raise TimeoutError(f"job at {path} did not finish within {timeout_s}s")


def main() -> None:
    base_url = os.environ.get("Z3RNO_BASE_URL", "http://localhost:8000")
    api_key = os.environ.get("Z3RNO_API_KEY", "z3rno_sk_test_localdev")

    # --- 1. Ingest the three notes. INGEST_AUTO_DISTILL chains into distill ----
    print("Ingesting 3 research notes...")
    ingest_jobs = []
    for filename, body in NOTES:
        result = _post(
            "/v1/ingest",
            base_url,
            api_key,
            {
                "kind": "text",
                "agent_id": AGENT_ID,
                "text": body,
                "filename": filename,
                "content_type": "text/markdown",
            },
        )
        ingest_jobs.append(result["job_id"])
        print(f"  {filename} → ingest_job={result['job_id']}")

    print("\nWaiting for ingest + auto-distill to settle...")
    for job_id in ingest_jobs:
        summary = _wait_for_job(base_url, api_key, path=f"/v1/ingest/{job_id}")
        distill_id = summary.get("distill_job_id")
        marker = f" → distill={distill_id}" if distill_id else ""
        print(f"  ingest {job_id}: {summary['status']}{marker}")
        if distill_id:
            _wait_for_job(base_url, api_key, path=f"/v1/distill/{distill_id}")

    # --- 2. Refine the graph: dedupe + reweight + prune --------------------
    print("\nKicking off a refine pass...")
    refine_result = _post("/v1/refine", base_url, api_key, {})
    refine_job = refine_result["job_id"]
    refine_done = _wait_for_job(base_url, api_key, path=f"/v1/refine/{refine_job}")
    print(
        f"  refine {refine_job}: {refine_done['status']}  "
        f"deduped={refine_done.get('memos_deduped', 0)}  "
        f"reweighted={refine_done.get('edges_reweighted', 0)}"
    )

    # --- 3. Ask the graph who Ada Lovelace collaborated with ---------------
    print("\nQuerying the graph via the GRAPH strategy...")
    client = Z3rnoClient(base_url=base_url, api_key=api_key)
    response = client.recall(
        agent_id=AGENT_ID,
        query="Who did Ada Lovelace work with?",
        strategy="GRAPH",
        top_k=5,
    )
    print(f"  {len(response.results)} hit(s) (strategy_used={response.strategy_used}):")
    for r in response.results:
        snippet = r.content[:140] + ("…" if len(r.content) > 140 else "")
        print(f"  - {snippet}")

    print(
        "\nThe Forge has turned three plain-text notes into a navigable knowledge "
        "graph. From here a research agent can answer questions, propose follow-up "
        "edges via refine.infer, or hand back a viewer URL (see z3rno-mcp's "
        "z3rno.visualize_url tool)."
    )
    client.close()


if __name__ == "__main__":
    main()
