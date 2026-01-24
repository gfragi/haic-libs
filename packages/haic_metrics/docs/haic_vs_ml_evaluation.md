
# Standard ML Evaluation vs HAIC Evaluation

## What is being evaluated?

Standard ML evaluation primarily evaluates an **AI model** as a predictive function:
inputs → outputs, assessed against ground truth labels.

HAIC evaluation evaluates a **socio-technical system** where outcomes emerge from
interaction between humans and AI:
human decisions ⇄ AI suggestions ⇄ feedback loops ⇄ workflow constraints.

## Unit of analysis

Standard ML: a dataset of independent samples (x, y), often IID.

HAIC: an interaction trace (session/run) composed of atomic **decisions** and
supporting **events**; temporal order and roles matter.

## Primary questions

Standard ML asks:
- How accurate is the model?
- How does it generalize across data distributions?
- How does it compare to baselines?

HAIC asks:
- How does collaboration behave over time?
- What is the human effort and responsiveness cost?
- Does the system support human agency (human-centeredness)?
- Does performance improve through interaction (adaptability)?
- Do human and AI policies align or diverge (similarity / agreement)?
- What are the efficiency constraints (latency, workload, effort loss)?

## Metrics

Standard ML (typical):
- accuracy, precision, recall, F1
- AUC / calibration
- robustness to perturbations
- fairness across groups

HAIC (interaction-centric, decision-based):
- Interaction frequency (F)
- Mean action duration (D)
- Human-centeredness proxy (HCL)
- Trust/quality proxies (Tr)
- Effort / efficiency loss (EL) and composite scores
- Adaptability (A) via temporal performance change
- Human–AI similarity (S) and agreement measures
- Human RT and AI latency distributions (p50/p90/p95)

Outcome metrics (accuracy/precision/recall) remain useful but are treated as
**optional extensions** that require ground truth and do not capture the full
collaboration process.

## Data requirements

Standard ML requires labeled datasets and evaluation splits.

HAIC requires logging of decision-centric interaction records:
- who acted (human/AI/system)
- what action occurred
- timestamps
- optional duration/latency
- optional correctness/labels

Richness of logging determines which metrics are available; therefore evaluation
should be profile-based (core vs full), with explicit warnings for missing data.

## Why this matters

A model can improve accuracy while making a workflow worse (higher human burden,
latency, cognitive load, or reduced agency). HAIC evaluation makes these effects
measurable and transparent by treating interaction as a first-class object.
