from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("haic-metrics")
except PackageNotFoundError:
    __version__ = "unknown"

from .compute import compute_metrics
from .io import compute_metrics_from_file
from .reporting.md import render_markdown_report


def report(artifact_path, *, profile="core", **kw):
    from haic_metrics.io import load_decisions_artifact
    from haic_metrics.reporting.md import render_markdown_report as _render

    try:
        from importlib.metadata import version as _version, PackageNotFoundError as _PNF
        _v_logging = _version("haic-logging")
    except (ImportError, _PNF):
        _v_logging = "unknown"

    artifact = load_decisions_artifact(artifact_path)
    result = compute_metrics(artifact, profile=profile, **kw)
    return _render(
        result=result,
        artifact=artifact,
        artifact_path=str(artifact_path),
        version_metrics=__version__,
        version_logging=_v_logging,
    )


__all__ = ["compute_metrics", "compute_metrics_from_file", "render_markdown_report", "report"]
