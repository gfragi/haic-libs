# haic_metrics/reporting/templates.py

REPORT_MD_TEMPLATE = """# HAIC Evaluation Report

## Run metadata
- **run_id:** {{ run_id }}
- **session_id:** {{ session_id }}
- **pilot_tag:** {{ pilot_tag }}
- **application mode:** {{ app_mode }}
- **model:** {{ model_name }} ({{ model_version }})

## Evaluation window
- **basis:** {{ window.basis }}  (relative = seconds since session start; absolute = epoch/ISO)
- **requested:** {{ window.requested }}
- **effective:** {{ window.effective }}
- **duration:** {{ window.duration_s }} s
- **events used:** {{ window.counts.events_used }} / {{ window.counts.events_total }}
- **decisions used:** {{ window.counts.decisions_used }} / {{ window.counts.decisions_total }}

{{#if window.notes}}
**window notes**
{{#each window.notes}}
- {{ this }}
{{/each}}
{{/if}}

## Metrics summary
| Category | Metric | Value | Notes |
|---|---:|---:|---|
| Interaction | F (frequency) | {{ metrics.F }} | interactions per time window |
| Interaction | D (diversity) | {{ metrics.D }} | action variety proxy |
| Human-centeredness | HCL | {{ metrics.HCL }} | normalized (rt_max={{ rt_max_s }}s) |
| Trust | Tr | {{ metrics.Tr }} | proxy based on available labels |
| Adaptability | A | {{ metrics.A }} | trend-based proxy |
| Similarity | S | {{ metrics.S }} | policy/behavior similarity |
| Efficiency | EL | {{ metrics.EL }} | latency/effort composite |

## Diagnostics
### Data coverage
- **has timestamps:** {{ diag.has_timestamps }}
- **has durations:** {{ diag.has_durations }}
- **human decisions:** {{ diag.n_human }}
- **ai decisions:** {{ diag.n_ai }}

### Warnings
{{#if warnings}}
{{#each warnings}}
- {{ this }}
{{/each}}
{{else}}
- None
{{/if}}

## Reproducibility
- **artifact:** {{ artifact_path }}
- **library versions:** haic-metrics {{ version_metrics }}, haic-logging {{ version_logging }}
- **generated at:** {{ generated_at }}
"""
