# Integration guide

## Step 1 — Install

```bash
pip install haic-logging haic-metrics
```

## Step 2 — Instrument your application

Wrap the part of your application that produces human and AI decisions in a `HaicLogger` context manager. The session is started on `__enter__` and closed (flushing all data to disk) on `__exit__`.

```python
from haic_logging import HaicLogger

with HaicLogger(
    log_dir="./logs",       # directory where output files are written
    pilot_tag="my-pilot",   # identifies the experiment or deployment
    app_name="my_app",      # optional: application name for the artifact metadata
    app_version="0.1.0",    # optional: application version
) as hl:
    # log decisions inside the block
    hl.log_decision(
        actor_type="human",      # "human" | "ai" | "system"
        action="confirm",        # controlled vocabulary, domain-specific
        object_id="case_42",     # the unit of work (image ID, document ID, …)
        duration_s=1.8,          # time the human spent on this decision (seconds)
        correct=True,            # optional: ground-truth label for the decision
    )
    hl.log_decision(
        actor_type="ai",
        action="suggest",
        object_id="case_42",
        latency_ms=80,           # AI inference time in milliseconds
    )
```

### `log_decision` field reference

| Field | Type | Required | Description |
|---|---|---|---|
| `actor_type` | `str` | yes | `"human"`, `"ai"`, or `"system"` |
| `action` | `str` | yes | Domain vocabulary (e.g. `"confirm"`, `"suggest"`, `"label_received"`) |
| `object_id` | `str` | yes | Identifier for the unit of work |
| `duration_s` | `float` | no | Human decision time in seconds; unlocks `D`, `HCL`, `EL` |
| `latency_ms` | `float` | no | AI inference latency in milliseconds; unlocks AI latency KPIs |
| `correct` | `bool` | no | Outcome label; unlocks `Tr` and adaptability metrics |
| `payload` | `dict` | no | Arbitrary extra data, stored but not used by the metrics engine |

## Step 3 — Export the decisions artifact

Call `export_decisions_artifact()` inside the `with` block (or the context manager does it on exit automatically if you prefer):

```python
artifact_path = hl.export_decisions_artifact()
# writes: ./logs/haic_decisions_<run_id>.json
```

The artifact is a self-describing JSON file and is the only file needed for evaluation.

## Step 4 — Compute metrics

```python
from haic_metrics import compute_metrics_from_file

result = compute_metrics_from_file(artifact_path, profile="core")

print(result["metrics"])
# {"F": 1.11, "D": 1.8, "HCL": 0.36, "Tr": 1.0, "EL": None, ...}

print(result.get("warnings", []))
# ["EL baseline unreliable: fewer than 3 human observations"]
```

Pass `profile="full"` to include outcome-based metrics if your decisions carry `correct` and/or `prediction` / `ground_truth` fields.

## Step 5 — Generate a report

```python
import haic_metrics

print(haic_metrics.report(artifact_path))
```

`report()` is a one-liner that loads the artifact, computes all core KPIs, and returns a ready-to-print Markdown report including metric summaries, diagnostics, and reproducibility metadata.

---

## Full example — RAG chatbot

This is a self-contained example showing the complete pipeline for a RAG chatbot with three simulated turns.

```python
"""
Minimal example: instrument any application with haic-libs.
Demonstrates the full pipeline in ~20 lines.
"""
from haic_logging import HaicLogger
from haic_metrics import report
import time

with HaicLogger(
    log_dir="./logs",
    pilot_tag="rag-demo",
    app_name="my_chatbot",
    app_version="0.1.0",
) as hl:

    # Simulate 3 turns
    for i in range(3):
        t0 = time.time()
        time.sleep(0.1)  # simulate user thinking

        hl.log_decision(
            actor_type="human",
            action="query",
            object_id=f"turn_{i}",
            duration_s=round(time.time() - t0, 3),
        )
        hl.log_decision(
            actor_type="ai",
            action="respond",
            object_id=f"turn_{i}",
            latency_ms=950,
            correct=True,
        )

    artifact_path = hl.export_decisions_artifact()

print(report(artifact_path))
```

Save this as `rag_demo.py` and run:

```bash
python rag_demo.py
```

The Markdown report is printed to stdout and can be redirected to a file or ingested by a benchmarking platform.
