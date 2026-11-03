# Metrics

`haic-metrics` computes KPIs at two levels of detail controlled by the `profile` argument. The **core** profile is always available from minimal decision logs. The **full** profile adds outcome-based measures that require explicit labels or ground-truth fields.

=== "Core profile"

    ## Interaction Dynamics

    | Metric | Symbol | Formula | High value | Low value |
    |---|---|---|---|---|
    | Interaction Frequency | F | total decisions / session duration (s) | Dense, active collaboration | Sparse or stalled session |
    | Mean Action Duration | D | mean(`duration_s`) across all decisions | Slow, effortful actions | Fast, fluent interactions |
    | Human-Centeredness | HCL | 1 − (mean human RT / rt_max_s) | High = low cognitive load (fast reaction → low load) | Low = high cognitive load (slow reaction → high load) |
    | Trust / Quality Proxy | Tr | mean(`correct`) where `correct` is present; `None` if no labels | High accuracy / acceptance rate | Frequent corrections or rejections |
    | Efficiency / Effort Loss | EL | max(0, (session duration T − baseline) / baseline); `None` without an explicit baseline | Session slower than the no-AI baseline (EL > 0) | Session at or faster than baseline (EL = 0) |
    | Efficiency Score | — | composite of EL and penalty terms | Efficient, low-overhead session | High effort relative to outcome |


    !!! warning "HCL direction is inverted"
        **High HCL = low cognitive load = good.**  
        **Low HCL = high cognitive load = bad.**  
        HCL=1.0 means the human reacted instantly (minimal load). HCL=0.0 means they
        took the maximum expected time (maximum load). HCL is `None` when no human
        decision carries timing (`duration_s` or `latency_ms`). See the
        [Interpretation guide](interpretation.md#hcl--human-centeredness) for details.

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

    All core metrics plus the following, computed when the required fields are present:

    ## Outcome & Quality

    | Metric | Symbol | Formula | High value | Low value |
    |---|---|---|---|---|
    | Prediction Accuracy | — | (TP + TN) / labeled decisions | Model is accurate | Model makes many errors |
    | Precision | — | TP / (TP + FP) | Few false positives | Many false positives |
    | Recall | — | TP / (TP + FN) | Few missed positives | Many missed positives |
    | F1-Score | — | 2 · Precision · Recall / (Precision + Recall) | Strong precision–recall balance | Imbalanced or poor overall quality |
    | Human–AI Agreement Rate | — | proportion of matching decisions | High alignment between human and AI | Frequent disagreement |

    ## Trust

    | Metric | Symbol | Description | High value | Low value |
    |---|---|---|---|---|
    | Trust Score | — | 100 · Σ `trust_rating` / Σ `trust_scale_maximum` (self-reported ratings) | Users report high trust | Users report low trust |

    Required fields: `prediction` and `ground_truth` (or a `result` label such as `true_positive`) for accuracy, precision, recall, F1 and agreement; `trust_rating` and `trust_scale_maximum` for the trust score.

    !!! note
        Extended metrics require domain-specific logging. Since 0.3.0, a metric whose required fields are absent, or that is undefined (e.g. precision with no positive predictions), is `None` rather than `0.0`, and a warning names it. Decisions without labels are excluded from accuracy rather than counted as errors.

## EL baseline

`EL` compares the session duration `T` against `baseline_s`, the expected duration of the same task without AI assistance. `baseline_s` must be supplied explicitly; when it is `None` (the default), `EL` and `EfficiencyScore` are `None` and a warning is added. Earlier versions (≤ 0.2.1) auto-derived the baseline as the P95 of human `duration_s`; that fallback was removed in 0.3.0 because a single-step percentile is not a counterfactual reference for a whole session.

## Windowed evaluation

All metrics can be computed over a temporal sub-window of a session:

```python
result = compute_metrics(
    artifact,
    window={"basis": "relative", "start": 0, "end": 120},
)
```

Two modes are supported: `"relative"` (seconds from session start) and `"absolute"` (ISO 8601 UTC timestamps). The evaluation report always discloses the effective window used.

---

## Going deeper

For full derivations, intuition, quadrant diagnostics, and common error patterns, see
the **[Metric Interpretation Guide](interpretation.md)**.
