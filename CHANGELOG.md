# Changelog

All notable changes to the HAIC libraries will be documented in this file.

This project follows a versioning scheme compatible with Semantic Versioning
for libraries (`MAJOR.MINOR.PATCH`), with early versions focusing on API stability
and methodological clarity.

---
## [v0.1.1] – TBD

### Fixed
- (anticipated small fixes; populate when releasing)

### Changed
- (anticipated minor behavior/compat improvements; populate when releasing)

---
## [0.1.0] – 2026-01-24

### Added

#### haic-logging
- Initial standalone logging library for Human–AI Collaboration systems.
- Session-based `HaicLogger` API for structured interaction logging.
- Append-only JSONL event stream for traceability and debugging.
- Export of a compact **decisions artifact** as a stable evaluation contract.
- Support for minimal decision-only logging (no events required).
- Optional resource monitoring (CPU/RAM, GPU when available).
- Explicit schema versioning for runs, events, and decisions artifacts.
- Lightweight validation and tolerance to partial or heterogeneous logs.

#### haic-metrics
- Initial standalone evaluation engine for Human–AI Collaboration.
- Decision-centric evaluation pipeline decoupled from application logic.
- Core HAIC interaction metrics:
  - Interaction frequency (F)
  - Mean action duration (D)
  - Human-centeredness proxy (HCL)
  - Trust / quality proxy (Tr)
  - Adaptability (A)
  - Human–AI similarity (S)
  - Effort / efficiency loss (EL) and composite efficiency score
- Human response-time summaries (mean, p50/p90/p95).
- AI latency summaries (mean, p50/p90/p95).
- Profile-based evaluation:
  - `core`: interaction dynamics and effort metrics
  - `full`: extended outcome and quality metrics when labels exist
- Alias-aware normalization and non-blocking validation with warnings.

#### Documentation
- Package-level READMEs for `haic-logging` and `haic-metrics`.
- Unified metrics catalog documenting all supported metrics, profiles, and data requirements.
- Architecture diagram describing the logging → decisions → metrics pipeline.
- Pilot onboarding examples (minimal and full).

#### Testing & Packaging
- Explicit `pyproject.toml` for both libraries.
- Editable installs supported.
- End-to-end round-trip tests:
  logging → decisions artifact → metrics computation.

---

## [Unreleased]

### Planned
- Additional metric profiles and extensions.
- Optional adapters for external platforms and data pipelines.
- Improved documentation and examples based on pilot feedback.
- Visualization helpers (kept outside the core libraries).

[Unreleased]: https://github.com/gfragi/haic-libs.git/compare/v0.1.0...HEAD
[v0.1.1]: https://github.com/gfragi/haic-libs.git/releases/tag/v0.1.0...v0.1.1
[v0.1.0]: https://github.com/gfragi/haic-libs.git/releases/tag/v0.1.0