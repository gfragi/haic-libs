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

Run tests with:

```bash
pytest -q
```

## How to Propose Changes

### Bug fixes

- Include a minimal reproduction (artifact or decision list).
- Add or update a test demonstrating the failure and the fix.
- Keep changes minimal and backward compatible when possible.

### New metrics

Before adding a metric, ensure:

1. It is defined in packages/haic_metrics/docs/metrics_catalog.md
2. The required fields are explicit and realistic for pilots
3. The metric is assigned to a profile:
    - core if computable from minimal decision logs
    - full if it requires outcome labels or richer context

4. It includes:

    - a docstring stating intent and assumptions
    - a unit test (or property-based test if appropriate)


### Schema changes

Schema changes are high-impact. Please:

- Open an issue describing motivation and compatibility impact
- Propose a schema version bump strategy
- Provide migration guidance or alias support where feasible

---

## Coding Conventions

- Prefer small, readable functions and explicit names
- Use type hints where practical
- Keep dependencies minimal
- Avoid heavy frameworks (e.g., pandas) unless justified
- Prefer warnings over exceptions for incomplete pilot data, unless correctness is compromised

---

## Documentation Requirements

Any user-facing change should update at least one of:

- package README (packages/*/README.md)
- metrics catalog (packages/haic_metrics/docs/metrics_catalog.md)
- architecture docs (docs/architecture/*)
- changelog (CHANGELOG.md)

---

## Release Process (Maintainers)

1. Update CHANGELOG.md
2. Bump version in each package pyproject.toml
3. Run pytest

4. Tag and create release:
    - git tag vX.Y.Z
    - git push --tags
5. Create GitHub Release notes based on the changelog section

---

## Code of Conduct

Be respectful and constructive. This is a research-oriented codebase and discussions
should remain evidence-based and technically grounded.


This is “research-grade”: it emphasizes methodological transparency and contracts, not just coding style.
