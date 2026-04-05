from datetime import datetime, timezone
from haic_metrics.reporting.templates import REPORT_MD_TEMPLATE


def render_markdown_report(
    *,
    result: dict,
    artifact: dict,
    artifact_path: str,
    version_metrics: str,
    version_logging: str,
) -> str:
    window = result.get("window_summary", {})
    metrics = result.get("metrics", {})
    warnings = result.get("warnings", [])

    meta = artifact.get("meta", {})
    ts = meta.get("timestamps", {})

    # Simple replacements (no templating engine needed yet)
    md = REPORT_MD_TEMPLATE

    def repl(key, value):
        nonlocal md
        md = md.replace(key, str(value))

    repl("{{ run_id }}", meta.get("run_id", "n/a"))
    repl("{{ session_id }}", meta.get("session_id", "n/a"))
    repl("{{ pilot_tag }}", meta.get("pilot_tag", "n/a"))
    repl("{{ app_mode }}", meta.get("application", {}).get("mode", "n/a"))
    repl("{{ model_name }}", meta.get("ai_system", {}).get("name", "n/a"))
    repl("{{ model_version }}", meta.get("ai_system", {}).get("version", "n/a"))

    repl("{{ window.basis }}", window.get("basis", "n/a"))
    repl("{{ window.requested }}", window.get("requested", {}))
    repl("{{ window.effective }}", window.get("effective", {}))
    repl("{{ window.duration_s }}", window.get("duration_s", 0.0))
    repl("{{ window.counts.events_used }}", window.get("counts", {}).get("events_used", 0))
    repl("{{ window.counts.events_total }}", window.get("counts", {}).get("events_total", 0))
    repl("{{ window.counts.decisions_used }}", window.get("counts", {}).get("decisions_used", 0))
    repl("{{ window.counts.decisions_total }}", window.get("counts", {}).get("decisions_total", 0))

    for k, v in metrics.items():
        repl(f"{{{{ metrics.{k} }}}}", v)

    repl("{{ artifact_path }}", artifact_path)
    repl("{{ version_metrics }}", version_metrics)
    repl("{{ version_logging }}", version_logging)
    repl(
    "{{ generated_at }}",
    datetime.now(timezone.utc).isoformat()
)

    # Warnings block (simple)
    if warnings:
        md = md.replace("{{#if warnings}}", "").replace("{{/if}}", "")
        md = md.replace("{{#each warnings}}", "").replace("{{/each}}", "")
        md = md.replace("{{ this }}", "\n".join(f"- {w}" for w in warnings))
    else:
        md = md.replace("{{#if warnings}}", "").replace("{{/if}}", "")
        md = md.replace("{{else}}", "").replace("- None", "- None")

    return md
