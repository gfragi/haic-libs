# HAIC Libraries

This repository contains the core, reusable libraries that underpin
the HAIC (Human–AI Collaboration) benchmarking and evaluation framework.

The goal is to provide **portable, pilot-agnostic building blocks**
that can be reused independently of any specific platform or UI.

---

## Repository Structure

```
haic-libs/
  packages/
    haic_logging/
    haic_metrics/
```

---

## Conceptual Architecture

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

---

## Design Rationale

- **Decoupling**  
  Logging, evaluation, and platform concerns are strictly separated.

- **Incremental adoption**  
  Pilots can start with minimal decision logs and progressively enrich them.

- **Reproducibility**  
  Decisions artifacts are immutable, portable, and suitable for offline analysis.

- **Framework alignment**  
  The core metrics operationalize the HAIC evaluation framework
  (interaction dynamics, effort, trust, adaptability).

---

## Typical Integration

1. A pilot integrates `haic-logging`
2. Decisions artifacts are exported (locally or via object storage)
3. `haic-metrics` computes KPIs offline
4. Results are visualized or imported into a benchmarking platform

---

## Relation to the HAIC Benchmarking Platform

The HAIC Benchmarking Platform is a **consumer** of these libraries.
It adds:
- storage
- orchestration
- visualization
- cross-run comparisons

The libraries themselves remain platform-independent.

---

## Status

- APIs are intentionally minimal and stable
- Backward compatibility is prioritized
- Extended tooling (e.g., onboarding wizards) builds on top of these libraries

---

## Quick start — one-liner report

```python
import haic_metrics

print(haic_metrics.report("haic_decisions_xxx.json"))
```

`report()` loads the artifact, computes all core KPIs, and returns a
ready-to-print Markdown evaluation report.

---

## Onboarding example — full pipeline

```python
from haic_logging import HaicLogger
import haic_metrics

with HaicLogger(log_dir="./logs", pilot_tag="pilot-x", app_name="my_app", app_version="0.1.0") as hl:
    hl.log_decision(actor_type="human", action="label_received", object_id="item_1", duration_s=2.1, correct=True)
    hl.log_decision(actor_type="ai", action="ai_evaluated", object_id="item_1", latency_ms=95)
    artifact_path = hl.export_decisions_artifact()

# One-liner: load → compute → render
print(haic_metrics.report(artifact_path))
```

To get raw metrics instead of a report:

```python
from haic_metrics import compute_metrics_from_file

result = compute_metrics_from_file(artifact_path, profile="core")
print(result["metrics"])
```

## Minimal onboarding example (decisions-only logging)

```python
from haic_logging import HaicLogger
import haic_metrics

with HaicLogger(log_dir="./logs", pilot_tag="pilot-minimal") as hl:
    hl.log_decision(
        actor_type="human",
        action="confirm",
        object_id="case_42",
        duration_s=1.8,
        correct=True,
    )
    hl.log_decision(
        actor_type="ai",
        action="suggest",
        object_id="case_42",
        latency_ms=80,
    )
    artifact_path = hl.export_decisions_artifact()

print(haic_metrics.report(artifact_path))
```

---

## haic-metrics API reference (top-level)

| Function | Description |
| --- | --- |
| `haic_metrics.report(path, *, profile, **kw)` | Full pipeline: load → compute → render Markdown report |
| `haic_metrics.compute_metrics(artifact, *, profile, baseline_s, window)` | Compute KPIs from a loaded artifact dict or decisions list |
| `haic_metrics.compute_metrics_from_file(path, *, profile, baseline_s, window)` | Load artifact from file and compute KPIs |
| `haic_metrics.render_markdown_report(*, result, artifact, ...)` | Render a Markdown report from a pre-computed result dict |

Key `compute_metrics` behaviours:

- **EL baseline**: auto-derived as P95 of human `duration_s` when `baseline_s=None`;
  a warning is added if fewer than 3 observations are available.
- **Tr**: returns `None` (not `1.0`) when no decisions carry a `correct` label,
  making the metric's absence explicit. A `Tr_note` key explains the status.
- **Windowing**: pass `window={"basis": "relative", "last": 120}` to restrict
  evaluation to the last 120 seconds of a session.

---

## References for the packages & more information

- [haic-logging README](packages/haic_logging/README.md)
- [haic-metrics README](packages/haic_metrics/README.md)
- [HAIC Metrics Catalog](packages/haic_metrics/docs/metrics_catalog.md)


## License

MIT

---

## Citation

This library is built on the framework described in:

```bibtex
@misc{fragiadakis2025evaluatinghumanaicollaborationreview,
      title={Evaluating Human-AI Collaboration: A Review and Methodological Framework},
      author={George Fragiadakis and Christos Diou and George Kousiouris and Mara Nikolaidou},
      year={2025},
      eprint={2407.19098},
      archivePrefix={arXiv},
      primaryClass={cs.HC},
      url={https://arxiv.org/abs/2407.19098},
}
```

For more details about the theoretical foundation and evaluation framework, please refer to the [arXiv paper](https://arxiv.org/abs/2407.19098).
