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
## Short onboarding example

```python
from haic_logging import HaicLogger
from haic_metrics import compute_metrics
from haic_metrics.io import load_decisions_artifact

with HaicLogger(log_dir="./logs", pilot_tag="pilot-x", app_name="my_app", app_version="0.1.0") as hl:
    hl.log_decision(actor_type="human", action="label_received", object_id="item_1", duration_s=2.1, correct=True)
    hl.log_decision(actor_type="ai", action="ai_evaluated", object_id="item_1", latency_ms=95)
    artifact_path = hl.export_decisions_artifact()

artifact = load_decisions_artifact(artifact_path)
report = compute_metrics(artifact, profile="core")
print(report["metrics"])

```

## Minimal onboarding example (decisions-only logging)


```python
from haic_logging import HaicLogger
from haic_metrics import compute_metrics

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

report = compute_metrics(artifact_path, profile="core")
print(report["metrics"])


```

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
