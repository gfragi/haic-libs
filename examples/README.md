# Examples

Each example is self-contained and runnable from the repo root after installing both packages in editable mode:

```bash
pip install -e packages/haic_logging -e packages/haic_metrics
python examples/<script>.py
```

---

## rag_chatbot_integration.py

**What it shows:** the complete haic-libs pipeline in ~20 lines.

1. Opens a `HaicLogger` session (context manager handles session start/end and JSONL flushing).
2. Simulates three human→AI turns, logging each decision with `actor_type`, `action`, `duration_s` / `latency_ms`, and an optional `correct` label.
3. Exports a decisions artifact (a compact JSON snapshot used as the metrics input contract).
4. Calls `haic_metrics.report()` — the one-liner that loads the artifact, computes all KPIs, and returns a ready-to-print Markdown report.

**Good starting point for:** RAG chatbots, annotation tools, any application where a human and an AI take turns acting on shared objects.

---

## Full RAG chatbot (separate repository)

The complete RAG chatbot used in the paper's demonstration, with its evaluation
sessions and the scripts that recompute its results, lives in
[gfragi/haic-libs-rag-replication](https://github.com/gfragi/haic-libs-rag-replication).
It installs `haic-metrics` and `haic-logging` from PyPI, like any other application.
