import re
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

    # Simple replacements (no templating engine needed yet)
    md = REPORT_MD_TEMPLATE

    # Conditional list blocks first, so their {{ this }} placeholders are not shared
    notes = window.get("notes") or []
    md = re.sub(
        r"\{\{#if window\.notes\}\}.*?\{\{/if\}\}\n",
        lambda _: ("**window notes**\n" + "".join(f"- {n}\n" for n in notes)) if notes else "",
        md,
        count=1,
        flags=re.S,
    )
    md = re.sub(
        r"\{\{#if warnings\}\}.*?\{\{/if\}\}",
        lambda _: "\n".join(f"- {w}" for w in warnings) if warnings else "- None",
        md,
        count=1,
        flags=re.S,
    )

    def repl(key, value):
        nonlocal md
        md = md.replace(key, "n/a" if value is None else str(value))

    # run_id / session_id are top-level in haic.decisions_artifact.v1; meta kept as fallback
    repl("{{ run_id }}", artifact.get("run_id") or meta.get("run_id", "n/a"))
    repl("{{ session_id }}", artifact.get("session_id") or meta.get("session_id", "n/a"))
    repl("{{ pilot_tag }}", meta.get("pilot_tag", "n/a"))
    repl("{{ app_mode }}", meta.get("application", {}).get("mode", "n/a"))
    ai_system = meta.get("ai_system", {})
    repl("{{ model_name }}", ai_system.get("model_name") or ai_system.get("name", "n/a"))
    repl("{{ model_version }}", ai_system.get("model_version") or ai_system.get("version", "n/a"))

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

    # Explicit fallback: Tr_note is absent when Tr is computable
    tr_note = metrics.get("Tr_note", "")
    repl("{{ metrics.Tr_note }}", tr_note if tr_note else "—")

    rt_max_s = result.get("rt_max_s", 60.0)
    repl("{{ rt_max_s }}", rt_max_s)

    decisions = artifact.get("decisions", [])
    has_timestamps = any(isinstance(d.get("t"), (int, float)) for d in decisions)
    has_durations = any(d.get("duration_s") is not None for d in decisions)
    n_human = sum(1 for d in decisions if d.get("actor_type") == "human")
    n_ai = sum(1 for d in decisions if d.get("actor_type") == "ai")

    repl("{{ diag.has_timestamps }}", has_timestamps)
    repl("{{ diag.has_durations }}", has_durations)
    repl("{{ diag.n_human }}", n_human)
    repl("{{ diag.n_ai }}", n_ai)

    repl("{{ artifact_path }}", artifact_path)
    repl("{{ artifact_schema }}", artifact.get("artifact_schema", "n/a"))
    repl("{{ schema_version }}", artifact.get("schema_version", "n/a"))
    repl("{{ version_metrics }}", version_metrics)
    repl("{{ version_logging }}", version_logging)
    repl(
    "{{ generated_at }}",
    datetime.now(timezone.utc).isoformat()
)

    return md
