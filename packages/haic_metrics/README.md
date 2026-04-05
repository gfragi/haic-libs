# haic-metrics

`haic-metrics` is a standalone evaluation engine for
Human–AI Collaboration (HAIC) systems.

It consumes a **decisions artifact** (produced by `haic-logging` or compatible
instrumentation) and computes interaction-level KPIs that go beyond
model-centric accuracy.

---

## Design Principles

- **Decision-centric evaluation**  
  Metrics are computed from interaction decisions, not UI or backend logs.

- **Schema-tolerant by design**  
  Alias-aware normalization enables heterogeneous pilot adoption.

- **Profile-based evaluation**  
  Core metrics are always available; extended metrics are opt-in.

---

## Installation

```bash
pip install haic-metrics
```

## Input Contract

`haic-metrics` accepts either:
- a list of decision dictionaries, or
- a decisions artifact with key "decisions".

### Minimal decision fields:
- `actor_type`
- `action` or `event_type`
- `t` / `timestamp`
- `object_id`

### Optional fields unlock additional metrics:
- `duration_s`
- `latency_ms`
- `correct`
- `labels` / `predictions`

## Quickstart

```python
from haic_metrics import compute_metrics
from haic_metrics.io import load_decisions_artifact

artifact = load_decisions_artifact("haic_decisions_run123.json")

result = compute_metrics(artifact, profile="core")

print(result["metrics"])
```
---
## Time-windowed evaluation

HAIC metrics can be computed over a specific temporal window of a session.
This allows developers and researchers to evaluate only the relevant portion
of an interaction (e.g., after model warm-up, during adaptation phases, or
within fixed experimental intervals).

Two windowing modes are supported:

- **Relative window** (offset from session start, in seconds)
- **Absolute window** (ISO 8601 UTC timestamps)

If session-level timestamps are missing, the evaluator automatically falls
back to the earliest recorded event timestamp.

### Example

```python
from haic_metrics import compute_metrics

result = compute_metrics(
    artifact,
    window={
        "basis": "relative",
        "start": 0,
        "end": 120,
    }
)

print(result["metrics"])
print(result["window_summary"])
```

The evaluation report always discloses the requested and effective window used for metric computation. This is **high signal**, low maintenance.

---

## Reporting

The library includes a structured Markdown reporting module that generates
self-describing evaluation reports, including:

- Evaluation window disclosure
- Metric summaries
- Diagnostics and warnings
- Reproducibility metadata (versions, timestamps)

Reports are designed for both experimental analysis and pilot documentation.


## Evaluation Profiles

### profile="core" (default)

Always computable from minimal decision logs.

Includes:
- `F`: interaction frequency
- `D`: average action duration
- `HCL`: human-centeredness proxy
- `Tr`: trust / quality proxy
- `A`: adaptability
- `S`: human–AI similarity
- `EL`: effort / efficiency loss
- `EfficiencyScore`
- Human response-time summary (p50/p90/p95)
- AI latency summary (p50/p90/p95)

### profile="full"

Includes all core metrics plus outcome-based measures when sufficient labels are present:
- `accuracy`
- `precision` / `recall`
- `human–AI agreement`
- `trust score proxies`

## Output Format

```json
{
  "metrics": {
    "F": 0.42,
    "D": 1.8,
    "HCL": 0.63,
    "ai_latency_p90_ms": 180,
    ...
  },
  "warnings": [
    "decision[2] missing timestamp key"
  ]
}
```

Warnings are non-fatal and indicate partial data coverage.

## What This Library Does NOT Do

- It does not ingest raw application logs
- It does not perform online evaluation
- It does not assume any domain (radiology, energy, manufacturing)

## Intended Usage Pattern

```
decisions.json
     └── haic-metrics
            └── metrics report
```

## License

MIT


---

