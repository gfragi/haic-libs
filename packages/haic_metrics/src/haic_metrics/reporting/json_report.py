import json
from datetime import datetime, timezone


def render_json_report(
    *,
    result: dict,
    artifact: dict,
    artifact_path: str,
    version_metrics: str,
    version_logging: str,
    profile: str = "core",
    baseline_s=None,
) -> str:
    """Machine-readable counterpart of render_markdown_report (same content, as JSON)."""
    report = {
        "run_id": artifact.get("run_id"),
        "session_id": artifact.get("session_id"),
        "pilot_tag": artifact.get("meta", {}).get("pilot_tag"),
        "parameters": {
            "profile": profile,
            "rt_max_s": result.get("rt_max_s", 60.0),
            "baseline_s": baseline_s,
        },
        "metrics": result.get("metrics", {}),
        "window_summary": result.get("window_summary", {}),
        "warnings": result.get("warnings", []),
        "reproducibility": {
            "artifact": artifact_path,
            "artifact_schema": artifact.get("artifact_schema"),
            "schema_version": artifact.get("schema_version"),
            "haic_metrics_version": version_metrics,
            "haic_logging_version": version_logging,
            "generated_at": datetime.now(timezone.utc).isoformat(),
        },
    }
    return json.dumps(report, indent=2, default=str)
