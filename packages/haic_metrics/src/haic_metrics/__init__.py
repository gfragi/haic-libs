from .compute import compute_metrics
from .io import load_decisions_artifact, compute_metrics_from_file
from .reporting.md import render_markdown_report

try:
    import haic_logging as _hl
    _logging_version = _hl.__version__
except Exception:
    _logging_version = "unknown"

try:
    from importlib.metadata import version as _v
    __version__ = _v("haic-metrics")
except Exception:
    __version__ = "0.1.1"


def report(
    artifact_path,
    *,
    profile="core",
    baseline_s=None,
    window=None,
) -> str:
    """
    One-call convenience: load artifact → compute metrics → render Markdown report.

    Usage:
        import haic_metrics
        print(haic_metrics.report("haic_decisions_xxx.json"))
    """
    artifact = load_decisions_artifact(artifact_path)
    result = compute_metrics(
        artifact,
        profile=profile,
        baseline_s=baseline_s,
        window=window,
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
    "report",
]
