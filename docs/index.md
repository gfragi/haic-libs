# haic-libs

**haic-libs** is an open-source Python library for evaluating Human–AI Collaboration (HAIC) systems.

It provides two independent packages:

- `haic-logging` — instrument any human–AI application with 5 lines of code
- `haic-metrics` — compute HAIC evaluation metrics offline from interaction logs

---

## Install

```bash
pip install haic-logging haic-metrics
```

---

## Quickstart

```python
from haic_logging import HaicLogger
from haic_metrics import report

with HaicLogger(log_dir="./logs", pilot_tag="my-app") as hl:

    hl.log_decision(
        actor_type="human", action="query",
        object_id="turn_1", duration_s=8.2, correct=True,
    )
    hl.log_decision(
        actor_type="ai", action="respond",
        object_id="turn_1", latency_ms=1150,
    )

    artifact_path = hl.export_decisions_artifact()

print(report(artifact_path))
```

That's the full pipeline: instrument → export → evaluate → report.

---

## Why haic-libs?

Most AI evaluation focuses on model accuracy. In deployed systems, overall effectiveness depends on how humans and AI interact — reliance behaviour, cognitive effort, adaptation over time. haic-libs makes these dynamics measurable without modifying your AI system or running user studies.

| Without haic-libs | With haic-libs |
| --- | --- |
| Write your own logging schema | `HaicLogger` out of the box |
| Implement each metric manually | `compute_metrics()` covers 8 KPIs |
| Bespoke per-project scripts | Portable decisions artifact |
| Silent failures on missing data | Graceful degradation with warnings |
| No report | Markdown report in one call |

---

## Paper

> Fragiadakis et al. (2025). *Evaluating Human-AI Collaboration: A Review and Methodological Framework*. [arXiv:2407.19098](https://arxiv.org/abs/2407.19098)

---

## License

MIT — built under the [HumAIne](https://humaine-horizon.eu) Horizon Europe project (Grant No. 101120218).
