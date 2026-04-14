# Metrics

`haic-metrics` computes KPIs at two levels of detail controlled by the `profile` argument. The **core** profile is always available from minimal decision logs. The **full** profile adds outcome-based measures that require explicit labels or ground-truth fields.

=== "Core profile"

    ## Interaction Dynamics

    | Metric | Symbol | Formula | High value | Low value |
    |---|---|---|---|---|
    | Interaction Frequency | F | total decisions / session duration (s) | Dense, active collaboration | Sparse or stalled session |
    | Mean Action Duration | D | mean(`duration_s`) across all decisions | Slow, effortful actions | Fast, fluent interactions |
    | Human-Centeredness | HCL | 1 / (1 + mean human `duration_s`) | Human responses are fast | Human responses are slow or absent |
    | Trust / Quality Proxy | Tr | mean(`correct`) where `correct` is present; `None` if no labels | High accuracy / acceptance rate | Frequent corrections or rejections |
    | Efficiency / Effort Loss | EL | (mean human `duration_s` − baseline) / baseline | Human is slower than baseline | Human matches or beats baseline |
    | Efficiency Score | — | composite of EL and penalty terms | Efficient, low-overhead session | High effort relative to outcome |

    ## Human Effort & Responsiveness

    | Metric | Symbol | Formula | High value | Low value |
    |---|---|---|---|---|
    | Human Response Time (mean) | — | mean(`duration_s`) for `actor_type=human` | Slow decisions (high cognitive load) | Fast decisions (low load or over-reliance) |
    | Human RT Percentiles | — | p50 / p90 / p95 of human `duration_s` | Long tail of slow responses | Tight, consistent response times |
    | Human Action Count | — | count of `actor_type=human` decisions | Many human interventions | Few interventions |

    ## AI Performance & Latency

    | Metric | Symbol | Formula | High value | Low value |
    |---|---|---|---|---|
    | AI Latency (mean) | — | mean(`latency_ms`) for `actor_type=ai` | Slow inference | Fast inference |
    | AI Latency Percentiles | — | p50 / p90 / p95 of `latency_ms` | Long-tail latency spikes | Consistent, fast responses |
    | AI Action Count | — | count of `actor_type=ai` decisions | AI drives the interaction | Human drives the interaction |

    ## Collaboration & Adaptation

    | Metric | Symbol | Formula | High value | Low value |
    |---|---|---|---|---|
    | Adaptability | A | relative improvement in `correct` rate over time | System or human is learning | No improvement over session |
    | Human–AI Similarity | S | overlap between human and AI action distributions | Actions mirror each other | Divergent behaviors |

=== "Extended profile (full)"

    All core metrics plus the following, computed when sufficient labels are present:

    ## Outcome & Quality

    | Metric | Symbol | Formula | High value | Low value |
    |---|---|---|---|---|
    | Prediction Accuracy | — | correct predictions / total | Model is accurate | Model makes many errors |
    | Precision | — | TP / (TP + FP) | Few false positives | Many false positives |
    | Recall | — | TP / (TP + FN) | Few missed positives | Many missed positives |
    | F1-Score | — | 2 · Precision · Recall / (Precision + Recall) | Strong precision–recall balance | Imbalanced or poor overall quality |
    | Human–AI Agreement Rate | — | proportion of matching decisions | High alignment between human and AI | Frequent disagreement |

    ## Trust, Safety & Robustness

    | Metric | Symbol | Description | High value | Low value |
    |---|---|---|---|---|
    | Trust Score | — | composite of agreement rate and error rate | System is trusted and accurate | Frequent errors erode trust |
    | Safety Incident Rate | — | frequency of decisions flagged as unsafe | Many safety events (bad) | No safety incidents (good) |
    | Abstention Rate | — | proportion of `action=abstain` AI decisions | AI withholds often (cautious/uncertain) | AI always provides an answer |
    | Error Recovery Time | — | mean time from error to correction | Slow recovery | Fast recovery |

    !!! note
        Extended metrics require domain-specific logging. `profile="full"` silently skips metrics whose required fields are absent.

## EL baseline

`EL` compares mean human `duration_s` against a baseline. When `baseline_s=None` (the default), the baseline is auto-derived as the **P95 of human `duration_s`** within the artifact. A warning is added to the report if fewer than 3 human observations are present.

## Windowed evaluation

All metrics can be computed over a temporal sub-window of a session:

```python
result = compute_metrics(
    artifact,
    window={"basis": "relative", "start": 0, "end": 120},
)
```

Two modes are supported: `"relative"` (seconds from session start) and `"absolute"` (ISO 8601 UTC timestamps). The evaluation report always discloses the effective window used.
