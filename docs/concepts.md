# Concepts

## The two packages

**`haic-logging`** is the instrumentation layer. It wraps a session in a context manager, records every human and AI decision as a timestamped entry, and writes two outputs when the session closes:

- `run_<id>.jsonl` — an append-only event stream for traceability and debugging.
- `haic_decisions_<id>.json` — a compact, portable decisions artifact that is the sole input to the evaluation engine.

The logger is intentionally decoupled from any UI, storage backend, or application domain. It captures *what happened* (who acted, on what, how long it took, whether it was correct) and nothing else.

**`haic-metrics`** is the offline evaluation engine. It reads a decisions artifact and computes interaction-level KPIs that go beyond model-centric accuracy: effort, trust, adaptability, and human–AI similarity. It does not need to connect to the running application; any environment with Python and the artifact file is sufficient.

```
Human–AI Application
│
▼
haic-logging
│
├── events.jsonl (traceability)
└── decisions.json (evaluation contract)
│
▼
haic-metrics
│
▼
HAIC KPI Report
```

## The decisions artifact

The decisions artifact is the formal interface between logging and evaluation. It is a JSON file with the following structure:

```json
{
  "schema_version": "haic.decisions.v1",
  "session_id": "...",
  "run_id": "...",
  "meta": { "pilot_tag": "...", "application": {}, "ai_system": {}, "task": {} },
  "decisions": [
    {
      "t": 1234567890.12,
      "actor_type": "human",
      "action": "label_received",
      "object_id": "img_001",
      "duration_s": 2.3,
      "correct": true
    }
  ]
}
```

Each decision record requires only four fields (`actor_type`, `action`, `object_id`, `t`). Additional fields (`duration_s`, `latency_ms`, `correct`) are optional and unlock progressively richer metrics.

### Why offline evaluation matters

Evaluating a human–AI system while it is running couples measurement to the live stack and makes reproducibility fragile. By separating the logging contract from the evaluation engine, haic-libs lets teams run evaluation pipelines independently — in CI, on exported data from production, or during retrospective analysis — without touching the original application. Artifacts are immutable and self-describing, so any result can be reproduced from the file alone.
