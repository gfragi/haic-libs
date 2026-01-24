from __future__ import annotations
from typing import Any, Dict, List, Union

from .io import extract_decisions
from .validators import validate_decisions_minimal

from .interaction_metrics import compute_interaction_metrics
from .human_rt import compute_human_rt_metrics
from .latency import compute_latency_metrics
from .outcome_metrics import compute_outcome_metrics

JsonDict = Dict[str, Any]

def compute_metrics(
    decisions_or_artifact: Union[JsonDict, List[JsonDict]],
    *,
    profile: str = "core",
    rt_max_s: float = 5.0,
    baseline_s: float | None = None,
    include_warnings: bool = True,
) -> JsonDict:
    """
    Profiles:
      - core: HAIC interaction KPIs + human RT + AI latency
      - full: core + outcome catalogue (precision/recall/etc) when available
    """
    decisions = extract_decisions(decisions_or_artifact)

    ok, warnings = validate_decisions_minimal(decisions)
    if not ok:
        raise ValueError("Invalid decisions input: " + "; ".join(warnings))

    metrics: JsonDict = {}

    # Core HAIC interaction KPIs
    metrics.update(
        compute_interaction_metrics(
            decisions,
            baseline_s=baseline_s,
            rt_max=rt_max_s,
        )
    )

    # Auxiliary summaries
    metrics.update(compute_human_rt_metrics(decisions))
    metrics.update(compute_latency_metrics(decisions))

    # Extended catalogue
    if profile == "full":
        metrics.update(compute_outcome_metrics(decisions, profile="core_outcomes"))
    elif profile != "core":
        raise ValueError(f"Unknown profile: {profile}")

    out: JsonDict = {"metrics": metrics}
    if include_warnings:
        out["warnings"] = warnings
    return out
