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

from z3rno import RefineJobStatus, Z3rnoClient

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


def _wait_for_ingest(client: Z3rnoClient, job_id: str, *, timeout_s: int = 120) -> str | None:
    """Poll an ingest job to completion. Returns the distill_job_id if auto-distill chained."""
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = client.get_ingest_status(job_id)
        if status.status in ("completed", "failed"):
            distill_id: str | None = status.distill_job_id
            return distill_id
        time.sleep(2.0)
    raise TimeoutError(f"ingest {job_id} did not finish within {timeout_s}s")


def _wait_for_distill(client: Z3rnoClient, job_id: str, *, timeout_s: int = 120) -> None:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = client.get_distill_status(job_id)
        if status.status in ("completed", "failed"):
            return
        time.sleep(2.0)
    raise TimeoutError(f"distill {job_id} did not finish within {timeout_s}s")


def _wait_for_refine(
    client: Z3rnoClient, job_id: str, *, timeout_s: int = 120
) -> RefineJobStatus:
    deadline = time.time() + timeout_s
    while time.time() < deadline:
        status = client.get_refine_status(job_id)
        if status.status in ("completed", "failed"):
            return status
        time.sleep(2.0)
    raise TimeoutError(f"refine {job_id} did not finish within {timeout_s}s")


def main() -> None:
    client = Z3rnoClient(
        base_url=os.environ.get("Z3RNO_BASE_URL", "http://localhost:8000"),
        api_key=os.environ.get("Z3RNO_API_KEY", "z3rno_sk_test_localdev"),
    )

    # --- 1. Ingest the three notes. INGEST_AUTO_DISTILL chains into distill --
    print("Ingesting 3 research notes...")
    ingest_jobs = []
    for filename, body in NOTES:
        job = client.ingest_text(agent_id=AGENT_ID, text=body)
        ingest_jobs.append(job.job_id)
        print(f"  {filename} → ingest_job={job.job_id}")

    print("\nWaiting for ingest + auto-distill to settle...")
    for job_id in ingest_jobs:
        distill_id = _wait_for_ingest(client, job_id)
        marker = f" → distill={distill_id}" if distill_id else ""
        print(f"  ingest {job_id}: completed{marker}")
        if distill_id:
            _wait_for_distill(client, distill_id)

    # --- 2. Refine the graph: dedupe + reweight + prune --------------------
    print("\nKicking off a refine pass...")
    refine_job = client.refine()
    print(f"  refine={refine_job.job_id}")
    refine_done = _wait_for_refine(client, refine_job.job_id)
    print(
        f"  status={refine_done.status}  "
        f"deduped={refine_done.memos_deduped}  "
        f"reweighted={refine_done.edges_reweighted}"
    )

    # --- 3. Ask the graph who Ada Lovelace collaborated with ---------------
    print("\nQuerying the graph via the GRAPH strategy...")
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
