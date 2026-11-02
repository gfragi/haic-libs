from .compute import compute_metrics
from .io import load_decisions_artifact, compute_metrics_from_file
from .reporting.md import render_markdown_report
from .reporting.json_report import render_json_report

try:
    import haic_logging as _hl
    _logging_version = _hl.__version__
except Exception:
    _logging_version = "unknown"

try:
    from importlib.metadata import version as _v
    __version__ = _v("haic-metrics")
except Exception:
    # Not installed (e.g. run from a source checkout): report that honestly
    # rather than a hard-coded release number that drifts out of date.
    __version__ = "unknown"


def report(
    artifact_path,
    *,
    profile="core",
    rt_max_s=60.0,
    baseline_s=None,
    window=None,
    fmt="md",
) -> str:
    """
    One-call convenience: load artifact → compute metrics → render a report.

    fmt="md" (default) returns a Markdown report; fmt="json" returns the same
    content as a JSON string (metrics, window summary, warnings, schema and
    library versions).

    Usage:
        import haic_metrics
        print(haic_metrics.report("haic_decisions_xxx.json"))
        print(haic_metrics.report("haic_decisions_xxx.json", fmt="json"))
    """
    if fmt not in ("md", "json"):
        raise ValueError(f"Unknown fmt: {fmt!r} (expected 'md' or 'json')")
    artifact = load_decisions_artifact(artifact_path)
    result = compute_metrics(
        artifact,
        profile=profile,
        rt_max_s=rt_max_s,
        baseline_s=baseline_s,
        window=window,
    )
    if fmt == "json":
        return render_json_report(
            result=result,
            artifact=artifact,
            artifact_path=str(artifact_path),
            version_metrics=__version__,
            version_logging=_logging_version,
            profile=profile,
            baseline_s=baseline_s,
        )
    return render_markdown_report(
        result=result,
        artifact=artifact,
        artifact_path=str(artifact_path),
        version_metrics=__version__,
        version_logging=_logging_version,
    )


__all__ = [
    "compute_metrics",
    "compute_metrics_from_file",
    "load_decisions_artifact",
    "render_markdown_report",
    "render_json_report",
    "report",
]
