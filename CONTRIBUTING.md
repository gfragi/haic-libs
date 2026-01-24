# Contributing

Thank you for considering a contribution to the HAIC libraries.

This repository contains reusable building blocks for decision-centric logging
and evaluation of Human–AI Collaboration (HAIC) systems. Contributions should
prioritize correctness, methodological transparency, and backward compatibility.

---

## Scope and Design Principles

1. **Library-first design**
   - No dependencies on UI frameworks, databases, or platform-specific services.
   - Application-specific logic should live in external adapters.

2. **Decision-centric contracts**
   - The primary evaluation contract is the **decisions artifact**.
   - Changes to decision fields and semantics must be documented and versioned.

3. **Incremental adoption**
   - The libraries should tolerate partial logs and heterogeneous schemas.
   - Prefer warnings over hard failures where scientifically reasonable.

4. **Reproducibility**
   - Outputs should be deterministic given the same artifact input.
   - Any randomness must be explicitly controlled.

---

## Repository Layout

- `packages/haic_logging`: instrumentation and artifact export
- `packages/haic_metrics`: evaluation engine and metric catalog
- `docs/`: architecture and documentation artifacts

---

## Development Setup

Create and activate a virtual environment, then install both packages in editable mode:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -U pip
pip install -e packages/haic_logging
pip install -e packages/haic_metrics
pip install -U pytest
```