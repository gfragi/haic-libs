# Changelog

All notable changes to the HAIC libraries will be documented in this file.

This project follows a versioning scheme compatible with Semantic Versioning
for libraries (`MAJOR.MINOR.PATCH`), with early versions focusing on API stability
and methodological clarity.

## Release process

To cut a new release:

1. Move all items from `## [Unreleased] → ### Added / Changed / Fixed` into a new
   `## [vX.Y.Z] – YYYY-MM-DD` section above the previous release.
2. Bump `version` in `packages/haic_metrics/pyproject.toml`
   (and `packages/haic_logging/pyproject.toml` if `haic-logging` changed).
3. Update the footer reference links at the bottom of this file:
   - `[Unreleased]` → compare from the new tag to HEAD
   - Add `[vX.Y.Z]` → release tag URL
4. Commit: `git commit -m "chore: release vX.Y.Z"`
5. Tag and push: `git tag vX.Y.Z && git push origin main --tags`

---

## [Unreleased]

### Planned

- Additional metric profiles and extensions.
- Optional adapters for external platforms and data pipelines.
- Improved documentation and examples based on pilot feedback.
- Visualization helpers (kept outside the core libraries).

---

## [v0.2.1] – 2026-04-13

### Fixed

- `logging_utils.py`: top-level `import pynvml` replaced with a lazy optional import
  inside `get_gpu_usage()`; file now imports cleanly on machines without pynvml installed.
  Added legacy-module comment — file is retained for reference but is not part of the
  public API.
- `interaction_metrics.py`: `Tr_note` is now only included in the metrics output dict
  when `Tr` is not computable (`labeled == 0`). Previously it was always emitted, exposing
  an internal annotation string in normal (labeled) evaluation runs.
- `md.py`: added explicit `"—"` fallback for `{{ metrics.Tr_note }}` when `Tr_note` is
  absent from the metrics dict (i.e., when labels are present and Tr is computable).

### Changed

- `compute_metrics()` EL baseline guard raised from **n ≥ 3** to **n ≥ 10** human
  duration observations. Short sessions no longer produce an artificially low P95 baseline
  and inflated EL values. Updated warning message now includes the actual observation
  count: `"EL baseline not reliable: fewer than 10 human duration observations in
  session (n=X)."` Pass an explicit `baseline_s` to override the guard.
- `EL` is now `None` (not `0.0`) when the baseline cannot be derived, making the
  metric's absence explicit. `EfficiencyScore` treats a missing EL as neutral (0).
- `__init__.py` public API rebuilt:
  - `_logging_version` resolved at module level via `import haic_logging` (graceful
    fallback to `"unknown"`) instead of a deferred `importlib.metadata` call.
  - `report()` now has explicit `baseline_s=None` and `window=None` parameters instead
    of a catch-all `**kw`, making the signature self-documenting.
  - `load_decisions_artifact` added to public exports and `__all__`.
  - `__version__` fallback changed from `"unknown"` to `"0.1.1"` for offline environments.

---

## [0.2.0] – 2026-04-05

### Added

- `compute_metrics_from_file(path, *, profile, baseline_s, window)` in `io.py` — loads a
  decisions artifact and computes metrics in a single call.
- `report(artifact_path, *, profile, **kw)` convenience function in `__init__.py` — runs the
  full load → compute → render pipeline; returns a ready-to-print Markdown string.
- `render_markdown_report` exported from the top-level package (`haic_metrics`).
- `__version__` attribute derived at import time via `importlib.metadata`; falls back to
  `"unknown"` when the package is not installed from a distribution.
- `Tr_note` key added to the metrics output dict:
  - `"proxy based on available labels"` when labeled decisions exist.
  - `"no labeled decisions; Tr not computable"` when none exist (`Tr` is then `None`).
- `render_markdown_report()` now derives and substitutes decision-level diagnostic fields
  directly from the artifact's decisions list: `rt_max_s`, `diag.has_timestamps`,
  `diag.has_durations`, `diag.n_human`, `diag.n_ai`.

### Changed

- `compute_metrics()` auto-derives `baseline_s` as the **P95 of human `duration_s`** values
  within the evaluation window when `baseline_s=None` (previous behavior: EL was always 0).
  If fewer than 3 qualifying observations exist, `EL` stays `0` and a warning is emitted:
  `"EL baseline not computable: insufficient human duration observations (n<3)."`.
- `Tr` is now `None` (not `1.0`) when no decisions carry a `correct` label or `error` event,
  making the metric's absence explicit rather than silently optimistic.
- Markdown report template: metric D label updated from `"D (diversity)"` to
  `"D (mean action duration)"` to match the actual computation.
- Markdown report template: F notes column updated from `"interactions per time window"` to
  `"interactions per minute"` to match the unit used in the formula.
- Markdown report template: Tr notes column now renders `{{ metrics.Tr_note }}` dynamically
  instead of a static string.
- `repl()` in `md.py` now renders `None` values as `"n/a"` in all report fields.

---

## [v0.1.1] – 2026-02-01

### Added
- Time-windowed evaluation support for metrics computation.
  - Relative windows (offsets from session start).
  - Absolute windows (ISO 8601 UTC timestamps).
  - Automatic fallback to earliest event timestamp when session start metadata is missing.
- Window summary metadata included in all metric outputs (requested vs effective window, counts).
- Markdown reporting module with structured, self-describing evaluation reports.
- Golden-report tests ensuring reporting stability and reproducibility guarantees.
- Timezone-aware UTC timestamps in generated reports.

### Changed
- `compute_metrics` now accepts an optional `window` argument to restrict evaluation scope.
- Metrics are computed strictly on window-filtered decisions/events.
- Reporting output explicitly discloses evaluation window and versions used.
- Internal timestamp handling standardized to epoch seconds + ISO 8601 UTC.

### Fixed
- Clarified separation between logging artifacts and metric computation inputs.
- Improved robustness when session-level timestamps are partially missing.
- Removed reliance on naive UTC timestamps (`datetime.utcnow`).

---
## [v0.1.0] – 2026-01-24

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


[Unreleased]: https://github.com/gfragi/haic-libs.git/compare/v0.2.1...HEAD
[v0.2.1]: https://github.com/gfragi/haic-libs.git/compare/v0.2.0...v0.2.1
[0.2.0]: https://github.com/gfragi/haic-libs.git/compare/v0.1.2...v0.2.0
[0.1.2]: https://github.com/gfragi/haic-libs.git/compare/v0.1.0...v0.1.2
[v0.1.1]: https://github.com/gfragi/haic-libs.git/releases/tag/v0.1.1
[v0.1.0]: https://github.com/gfragi/haic-libs.git/releases/tag/v0.1.0