# HAIC Core Metrics Catalog

This document catalogs the core metrics available in the HAIC evaluation framework. These metrics are designed to assess various aspects of human-AI interaction, focusing on efficiency, trust, and human-centeredness.

## 1. Interaction Dynamics (Core)

| Metric                   | Symbol | Description                                                | Required Fields             | Profile |
| ------------------------ | ------ | ---------------------------------------------------------- | --------------------------- | ------- |
| Interaction Frequency    | F      | Rate of interaction events per unit time                   | `t`, `actor_type`, `action` | core    |
| Mean Action Duration     | D      | Average duration of human or system actions                | `duration_s`                | core    |
| Human-Centeredness       | HCL    | Normalized inverse human response time proxy               | `duration_s`                | core    |
| Trust / Quality Proxy    | Tr     | Proxy trust measure derived from error or abstention rates | `correct` or error flags    | core    |
| Efficiency / Effort Loss | EL     | Relative effort compared to baseline                       | `duration_s`, baseline      | core    |
| Efficiency Score         | —      | Composite score incorporating effort and penalties         | derived                     | core    |


Notes:
- These metrics are always computable when minimal decision logs exist.
- They form the core HAIC evaluation engine.

## 2. Human Effort & Responsiveness

| Metric                     | Symbol | Description               | Required Fields                  | Profile |
| -------------------------- | ------ | ------------------------- | -------------------------------- | ------- |
| Human Response Time (mean) | —      | Mean human reaction time  | `duration_s`, `actor_type=human` | core    |
| Human RT Percentiles       | —      | p50 / p90 / p95 human RT  | `duration_s`                     | core    |
| Human Action Count         | —      | Number of human decisions | `actor_type=human`               | core    |

Notes:
- Used to quantify cognitive/interactional workload.
- Independent of task domain.

## 3. AI Performance & Latency

| Metric                 | Symbol | Description                | Required Fields | Profile |
| ---------------------- | ------ | -------------------------- | --------------- | ------- |
| AI Latency (mean)      | —      | Mean AI inference latency  | `latency_ms`    | core    |
| AI Latency Percentiles | —      | p50 / p90 / p95 AI latency | `latency_ms`    | core    |
| AI Action Count        | —      | Number of AI decisions     | `actor_type=ai` | core    |


Notes:
- Evaluates system efficiency under interaction load.
- Does not require ground truth labels.

##  4 Collaboration & Adaptation

| Metric                  | Symbol | Description                                        | Required Fields        | Profile |
| ----------------------- | ------ | -------------------------------------------------- | ---------------------- | ------- |
| Adaptability            | A      | Relative improvement in performance over time      | `correct`, `t`         | core    |
| Human–AI Similarity     | S      | Behavioral similarity between human and AI actions | `actor_type`, `action` | core    |
| Human–AI Agreement Rate | —      | Proportion of matching decisions                   | predictions + labels   | full    |

Notes:
- These metrics capture collaboration dynamics, not standalone model quality.

## 5. Outcome & Quality Metrics (Extended)

| Metric              | Symbol | Description                       | Required Fields              | Profile |
| ------------------- | ------ | --------------------------------- | ---------------------------- | ------- |
| Prediction Accuracy | —      | Correct predictions over total    | `prediction`, `ground_truth` | full    |
| Precision           | —      | Positive predictive value         | confusion matrix             | full    |
| Recall              | —      | Sensitivity                       | confusion matrix             | full    |
| F1-Score            | —      | Harmonic mean of precision/recall | confusion matrix             | full    |

Notes:
- These are optional and only computed when explicit labels exist.
- They are not considered core HAIC metrics.

## 6. Trust, Safety & Robustness (Extended)
| Metric               | Symbol | Description                | Required Fields    | Profile |
| -------------------- | ------ | -------------------------- | ------------------ | ------- |
| Trust Score          | —      | Composite trust proxy      | agreement + errors | full    |
| Safety Incident Rate | —      | Frequency of unsafe events | safety flags       | full    |
| Abstention Rate      | —      | Rate of AI abstentions     | `action=abstain`   | full    |
| Error Recovery Time  | —      | Time to recover from error | timestamps         | full    |

Notes:
- Intended for regulated or safety-critical domains.
- Strongly dependent on domain-specific logging.