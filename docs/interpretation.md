# Metric Interpretation Guide

This page explains **why** each HAIC metric is defined the way it is, how to interpret
values in practice, and how to use the five quadrant diagnostic plots to diagnose
collaboration quality. It is the companion to the [Metrics reference](metrics.md).

---

## Before you interpret: three things you must set

Every metric interpretation depends on two global parameters you define per session.
Getting these wrong is the most common source of misleading results.

### `baseline_s` — the EL anchor

EL measures overhead *relative to something*. That something is `baseline_s`: the
expected task duration without AI assistance (or with a previous, simpler system).

| How to set it | When to use |
|---|---|
| Measure directly (time users on the task pre-deployment) | You have a pre-AI baseline |
| Let haic-metrics auto-derive as P95 of `duration_s` | You have ≥ 10 human observations and no external baseline |

Always state which approach you used. The two methods can produce different EL values
for the same data.

### `rt_max_s` — the HCL ceiling

HCL normalises reaction time against a maximum. `rt_max_s` defines what "fully loaded"
looks like for your task type.

| Task type | Typical `rt_max_s` |
|---|---|
| Real-time operator dashboard | 2–5 s |
| Document Q&A chatbot | 20–30 s |
| Clinical decision support | 5–10 s |
| Grid / energy management | 10–30 s |

!!! warning "The 60-second trap"
    The default `rt_max_s=60` is almost always **too high** for deployed systems. A
    value that is too high produces artificially high HCL scores, making a cognitively
    demanding system appear comfortable. Always set this explicitly and justify the
    choice.

### `actor_type="system"` — what to exclude

Events logged with `actor_type="system"` (automated pipeline steps, background
processes, database queries) are **excluded from all metric computations**. Including
them inflates F, distorts HCL with non-human latency values, and pollutes Tr with
non-decision events. This exclusion happens automatically — log them freely for
traceability, but do not expect them to appear in metric results.

---

## Metric-by-metric derivations

### EL — Effort Loss

**The question:** Does the AI add overhead, or does it save time?

```
EL = (t_actual − t_baseline) / t_baseline

t_actual   = mean human task duration in this session (seconds)
t_baseline = expected task duration without AI (seconds)

Range: [0, ∞)    EL cannot be negative (see note below)
```

**Why this formula?**
The ratio `(t_actual - t_baseline) / t_baseline` is a standard *relative change*
calculation — the same form as percentage overhead. Normalising by `t_baseline` makes
EL comparable across tasks with different natural durations (a 5-minute task and a
5-second task are now on the same scale).

**Why EL cannot be negative:**
The formula can mathematically produce a negative result when `t_actual < t_baseline`
(the AI genuinely saves time). In the HumAIne framework EL is defined as an *overhead*
metric, not a benefit metric — negative overhead is clamped to zero. The time-saving
benefit is captured by `EfficiencyScore` instead. This keeps the metric unambiguous: EL
always means *cost*, never *gain*.

**Reference values:**

| EL | Interpretation |
|---|---|
| 0.0 | No overhead — AI does not slow the human down at all |
| 0.1–0.2 | Acceptable overhead for most deployed systems |
| 0.3–0.5 | Elevated — investigate AI latency and workflow friction |
| > 0.5 | High — AI is adding significant time cost |

---

### D — Mean Decision Duration

**The question:** On average, how much time does each decision take?

```
D = Σ(duration_s) / N

duration_s = time spent on each logged decision event
N          = total number of decision events

Range: [0, ∞)    Unit: seconds per decision
```

D is a raw speed metric with no baseline comparison. Its main use is **comparing
pipeline versions** (v1 vs v2) or **comparing interface conditions** (2D vs XR). On its
own D is ambiguous: fast decisions can mean clear AI output (good) or that the human
has given up engaging (bad). Always read D alongside Tr.

---

### F — Interaction Frequency

**The question:** How dense is the collaboration?

```
F = N / (T_session / 60)

N         = total interaction events in the session
T_session = total session duration in seconds

Range: [0, ∞)    Unit: interactions per minute
```

**F has no universal "good" direction** — it is task-relative. High F is healthy in a
real-time control room; the same F in a document Q&A session may signal that users are
confused and rephrasing repeatedly. F only becomes interpretable in combination with HCL
(see [quadrant HCL×F](#hcl-x-f--cognitive-load-x-frequency) below).

Typical ranges by task type:

| Task | Typical F |
|---|---|
| Conversational chatbot | 1–5 / min |
| Operator dashboard | 5–20 / min |
| Image annotation | 3–10 / min |

---

### HCL — Human-Centeredness

**The question:** How much cognitive load does the AI place on the human?

```
HCL = 1 − (RT / RT_max)

RT     = mean human reaction time to AI output (seconds)
RT_max = maximum expected reaction time for this task (= rt_max_s)

Range: [0, 1]

HCL = 1.0  →  RT = 0       → human reacted instantly → minimal cognitive load
HCL = 0.5  →  RT = RT_max/2  → moderate load
HCL = 0.0  →  RT = RT_max  → human took maximum time → maximum load
```

**Why `1 − (RT / RT_max)` and not just RT?**

Three reasons:

1. **Inversion**: Raw RT is higher-is-worse. HAIC metrics use higher-is-better
   conventions for readability. Subtracting from 1 inverts the direction.
2. **Normalisation**: Dividing by `RT_max` removes task-specific scale — a 2-second RT
   means something different for a chatbot vs a control room. After normalisation,
   HCL=0.8 means the same thing across both.
3. **Linearity**: The `1 - x` transform keeps interpretation simple. HCL=0.8 literally
   means "the human uses 20% of their available reaction budget." This is easy to
   communicate.

!!! warning "HCL is inverted — this confuses everyone"
    **High HCL = LOW cognitive load = good.**
    **Low HCL = HIGH cognitive load = bad.**
    HCL=1 does not mean "maximum cognitive load." It means the human reacted instantly,
    which implies minimal load. Always label axes with directional arrows when presenting
    quadrant plots.

**Why is this called a "proxy"?**
Cognitive load cannot be measured from interaction logs alone — that would require EEG
or physiological sensors. Reaction time *correlates* with cognitive load (longer RT →
more processing difficulty), grounded in cognitive psychology research (Kahneman 2011;
Wickens & Hollands 2000). HCL is therefore an inference, not a direct measurement.

---

### Tr — Trust Proxy

**The question:** Do humans accept AI suggestions, or do they override them?

```
Tr = n_accepted / n_total

n_accepted = AI suggestions the human accepted (correct=True)
n_total    = total AI suggestions

Range: [0, 1]

Tr = 1.0  →  human accepted every suggestion
Tr = 0.5  →  accepted half
Tr = 0.0  →  rejected every suggestion
Tr = None →  correct field was not logged (cannot compute)
```

**Why "behavioral proxy" and not "trust"?**
Trust is a psychological construct that cannot be read from logs. What is observable is
*acceptance behavior* — the downstream consequence of trust. The relationship is not
1:1: high Tr with poor AI quality indicates automation bias (over-trust). Low Tr with
high AI quality indicates a trust deficit (under-trust). Tr must always be interpreted
alongside accuracy metrics (RAGAS Faithfulness, ground-truth correctness rates).

**Operationalising acceptance:**
In a chatbot, you must define what counts as "accepted." Common definitions:

- User did not rephrase the query within N seconds
- User clicked a positive feedback button
- User moved to the next task without modifying the answer

The definition must be stated in any evaluation report — different definitions produce
different Tr values from identical sessions.

---

### A — Adaptability

**The question:** Is trust growing or eroding over the course of a session?

```
A = tanh( (Acc_late − Acc_early) / Acc_early )

Acc_early = acceptance rate in the first 20% of session decisions
Acc_late  = acceptance rate in the last 20% of session decisions

Range: [-1, +1]

A > 0  →  trust improving
A = 0  →  no change
A < 0  →  trust eroding
```

**Why 20% windows instead of halves?**
Comparing the first half to the second half includes noisy mid-session behaviour.
Taking the first 20% (when users are most uncertain) and last 20% (when patterns have
stabilised) captures the full arc of adaptation while avoiding mid-session noise. With
20 decisions: Acc_early covers decisions 1–4, Acc_late covers decisions 17–20.

**Why `tanh`?**
The raw ratio `(Acc_late − Acc_early) / Acc_early` is unbounded — if Acc_early is 0.05
and Acc_late is 0.30, the ratio is 5.0. `tanh` compresses any real number to `(-1, +1)`
smoothly and differentiably, preserving sign and relative magnitude without a hard clip.
It is a standard choice when you need a bounded output that scales gracefully with
extreme inputs.

**When A is unreliable:**
A requires enough decisions to form meaningful 20% windows. With fewer than 10 decisions
per session, a single override can produce a dramatically negative A. Flag A as
potentially unreliable when `n < 10` decisions per session.

---

### S — Surrogate Similarity

**The question:** When using a synthetic agent, how faithfully does it replicate real human behavior?

!!! info "Simulation contexts only"
    S is only meaningful when you have replaced real human participants with a surrogate
    (synthetic) agent. Do not compute or report S in real-user studies.

```
Discrete variant:
  S = n_matching / n_total
  (proportion of events where surrogate action == real human action)

Probabilistic variant:
  S = 1 − JSD(p_surrogate ∥ p_human)
  (JSD = Jensen-Shannon Divergence, bounded [0, 1])

Range: [0, 1]   S = 1.0 → perfect match   S = 0.0 → completely divergent
```

**Why JSD and not KL-divergence?**
KL-divergence is asymmetric: `KL(p‖q) ≠ KL(q‖p)`. There is no natural "reference
distribution" — neither human nor surrogate is inherently the ground truth for the
purpose of the comparison. JSD is symmetric by construction, making it appropriate
for comparing two distributions without privileging one.

**S as a validity gate:**
When S is low, no other metric computed from that simulation should be trusted. S must
pass a minimum threshold (typically S ≥ 0.6) before interpreting A, EL, Tr, HCL, or F
from surrogate-generated data.

---

## EfficiencyScore — the composite

```
EfficiencyScore = clip(
    base × (1 − 0.35 × off_role_rate) × (1 + 0.10 × progress_rate),
    0, 1
)

base          = 1 / (1 + EL)
off_role_rate = fraction of events where actor acted outside their expected role
progress_rate = fraction of tasks completed successfully
```

**Component breakdown:**

| Component | Effect | Rationale |
|---|---|---|
| `base = 1/(1+EL)` | [0,1], decreasing in EL | Converts unbounded EL to bounded efficiency |
| `1 - 0.35×off_role_rate` | Up to −35% penalty | Captures role integrity violations |
| `1 + 0.10×progress_rate` | Up to +10% bonus | Small bonus for task completion |
| `clip(·, 0, 1)` | Keeps result in [0,1] | Prevents artefacts from edge cases |

The 0.35 and 0.10 coefficients reflect that role integrity has a larger impact on
collaboration quality than raw task completion rate — a system that completes tasks by
violating role boundaries is more problematic than one that completes fewer tasks
correctly.

---

## Quadrant diagnostics

A quadrant plot places two metrics on X and Y axes, divides the space at threshold
values, and reveals which collaboration regime a system occupies. The five standard
quadrant combinations are described below.

Each combination answers a different diagnostic question. Use
[haic_quadrant_plots_v3.html](https://gfragi.github.io/haic-libs/quadrant-plots) for
interactive exploration.

---

### EL × Tr — Efficiency × Trust

**Thresholds:** EL ≤ 0.3 (low overhead), Tr ≥ 0.5 (moderate acceptance).
**Good corner:** lower-left (low EL, high Tr).

| Zone | EL | Tr | Label | Implication |
|---|---|---|---|---|
| Lower-left ⭐ | Low | High | **Ideal** | AI saves time and is trusted. Monitor for automation bias if Tr → 1.0 with low AI accuracy. |
| Upper-left | Low | Low | **Automation bias risk** | Efficient but not trusted. Humans may be ignoring AI despite its speed. Investigate AI quality and user familiarity. |
| Lower-right | High | High | **Costly trust** | Trusted but slow. Good model, poor deployment. Fix inference latency and workflow integration. |
| Upper-right | High | Low | **Breakdown** | High overhead AND low trust. AI adds friction without value. Redesign or remove. |

This is the first quadrant to examine for any RAG or assistant system.

---

### HCL × F — Cognitive Load × Frequency

**Thresholds:** HCL ≥ 0.5 (comfortable), F ≥ 5/min (active).
**Good area:** right side (high HCL); optimal F is task-dependent.

!!! warning "Axis direction"
    The X-axis runs: **← high cognitive load  ·  HCL  ·  low cognitive load →**
    Always label with directional arrows. High HCL is on the RIGHT.

| Zone | HCL | F | Label | Implication |
|---|---|---|---|---|
| Right, moderate F | High | Moderate | **Comfortable & active** | Low load with natural pace. Ideal for most systems. |
| Right, low F | High | Low | **Disengaged** | Comfortable but barely interacting. Check for automation bias or sessions too simple to require interaction. |
| Left, high F | Low | High | **Overloaded** | Rapid interactions with high cognitive strain. Reduce interaction density immediately. |
| Left, low F | Low | Low | **Struggling silently** | High load, low interaction. Users may have abandoned the task. Most dangerous zone. |

---

### A × Tr — Adaptability × Trust

**Thresholds:** A ≥ 0 (improving), Tr ≥ 0.5 (moderate trust).
**Good corner:** right side (positive A), high Tr.

| Zone | A | Tr | Label | Implication |
|---|---|---|---|---|
| Positive, high Tr ⭐ | Positive | High | **Growing trust** | Trust is building and currently strong. Ideal trajectory. |
| Positive, low Tr | Positive | Low | **Rising from low** | Trust improving but currently insufficient. Monitor over time. |
| Negative, high Tr | Negative | High | **Eroding trust** | High current trust but declining. Investigate AI consistency and quality under load. |
| Negative, low Tr | Negative | Low | **Abandonment** | Low trust that is declining further. Most urgent action needed. |

Note: high Tr is not always correct. If Tr=0.95 but ground-truth accuracy is 0.60,
users are over-trusting a bad AI. Always cross-reference with accuracy metrics.

---

### EL × HCL — Overhead × Cognitive Load

**Thresholds:** EL ≤ 0.3 (low overhead), HCL ≥ 0.5 (comfortable).
**Good corner:** lower-left (low EL, high HCL).

This quadrant catches **false efficiency** — a failure mode invisible to EL × Tr.
A system can appear efficient (low EL) while achieving that speed by overloading
the human (low HCL). EL × HCL separates genuine efficiency from human-costly speed.

| Zone | EL | HCL | Label | Implication |
|---|---|---|---|---|
| Lower-left ⭐ | Low | High | **Genuine efficiency** | AI reduces overhead without burdening the human. Sustainable. |
| Upper-left | Low | Low | **False efficiency** | Speed gained at the cost of human strain. Unsustainable. Improve output clarity. |
| Lower-right | High | High | **Wasted capacity** | Human is comfortable but AI is slow or unnecessary. Optimise latency. |
| Upper-right | High | Low | **Burden** | High overhead AND high cognitive load. Immediate redesign warranted. |

---

### S × A — Surrogate Similarity × Adaptability

!!! info "Simulation contexts only"
    This quadrant only applies when using surrogate agents. It validates whether
    simulation results can be trusted before interpreting any other metrics.

**Thresholds:** S ≥ 0.6 (valid simulation), A ≥ 0 (improving).
**Good corner:** right side (high S), positive A.

| Zone | S | A | Label | Implication |
|---|---|---|---|---|
| High S, positive A ⭐ | High | Positive | **Valid & improving** | Surrogate is faithful and trust is growing. Results are trustworthy. |
| High S, negative A | High | Negative | **Valid, eroding trust** | Simulation is valid but AI trust is declining. Investigate AI quality. |
| Low S, any A | Low | Any | **Invalid simulation** | Surrogate does not match real humans. All other metrics from this run are suspect. |

When S is below threshold, do not interpret F, EL, HCL, Tr, or A from that simulation.
S is the validity gate that must pass before trusting any other metric.


## Live Quadrant Diagnostic Tool

Adjust the sliders to explore how metric pairs map to the four interpretive zones.

<div style="border: 1px solid #e2e6ea; border-radius: 10px; overflow: hidden; margin: 24px 0;">
  <iframe 
    src="assets/haic_quadrant_plots_v3.html"
    width="100%" 
    height="780"
    style="border: none; display: block;"
    title="HAIC Quadrant Diagnostic Plots">
  </iframe>
</div>
---

## Common errors and fixes

| Situation | Symptom | Cause | Fix |
|---|---|---|---|
| `EL < 0` | Negative EL | AI saved time (`t_actual < t_baseline`) | Clamp to 0; note time saving separately |
| `Tr = None` | Tr not computed | `correct` field missing from human events | Add `correct=True/False` to `log_decision` for human events |
| `HCL > 1` | HCL exceeds 1.0 | `rt_max_s` too low; some RT > ceiling | Increase `rt_max_s` to cover ≥ P95 of observed RTs |
| `HCL ≈ 1` always | Suspiciously perfect HCL | `rt_max_s` too high | Lower `rt_max_s` to a realistic task ceiling |
| `A = None` | A not computed | Fewer than 2 decisions in early/late window | Ensure ≥ 10 decisions per session; flag A as unreliable otherwise |
| F very high | Hundreds of events/min | System events included | Filter `actor_type="system"` — excluded automatically by haic-metrics |
| S computed, real users | S reported in real-user study | Misapplication | S is simulation-only; remove from results |

---

## Reference

Fragiadakis et al. (2025). *Evaluating Human-AI Collaboration: A Review and
Methodological Framework*. [arXiv:2407.19098](https://arxiv.org/abs/2407.19098)

HumAIne Horizon Europe project, Grant No. 101120218.
