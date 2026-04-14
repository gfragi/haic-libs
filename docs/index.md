# haic-libs

`haic-libs` is a pair of portable Python packages for instrumenting and evaluating Human–AI Collaboration (HAIC) systems. `haic-logging` provides a lightweight context-manager-based logger that captures interaction decisions during a live session and exports them as a structured artifact. `haic-metrics` consumes that artifact offline and computes a standardized set of KPIs — interaction frequency, effort loss, trust proxy, adaptability, and more — without requiring access to the original application, database, or UI.

## Install

```bash
pip install haic-logging haic-metrics
```

## Quickstart

```python
from haic_logging import HaicLogger
import haic_metrics

with HaicLogger(log_dir="./logs", pilot_tag="pilot-x") as hl:
    hl.log_decision(actor_type="human", action="confirm", object_id="item_1", duration_s=2.1, correct=True)
    hl.log_decision(actor_type="ai",    action="suggest", object_id="item_1", latency_ms=95)
    artifact_path = hl.export_decisions_artifact()

print(haic_metrics.report(artifact_path))
```

See the [Integration guide](integration.md) for a step-by-step walkthrough and a full RAG chatbot example.
