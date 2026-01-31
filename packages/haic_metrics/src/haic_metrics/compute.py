from __future__ import annotations
from typing import Any, Dict, List, Union, Optional, Literal, TypedDict

from .io import extract_decisions
from .validators import validate_decisions_minimal

from .interaction_metrics import compute_interaction_metrics
from .human_rt import compute_human_rt_metrics
from .latency import compute_latency_metrics
from .outcome_metrics import compute_outcome_metrics
from .windowing import filter_decisions_events_by_epoch

JsonDict = Dict[str, Any]


class WindowSpec(TypedDict, total=False):
    # required if window is provided
    basis: Literal["relative", "absolute"]

    # choose one of:
    start: Union[float, str]   # relative seconds OR epoch seconds OR ISO datetime
    end: Union[float, str]     # relative seconds OR epoch seconds OR ISO datetime
    last: float                # last N seconds (relative only)


class WindowSummary(TypedDict, total=False):
    basis: str
    requested: Dict[str, Any]     # start/end/last as given
    effective: Dict[str, Any]     # computed epoch bounds + relative bounds
    counts: Dict[str, int]        # decisions_total/used, events_total/used
    duration_s: float
    notes: List[str]              # clamping, missing timestamps, etc.


def compute_metrics(
    decisions_or_artifact: Union[JsonDict, List[JsonDict]],
    *,
    profile: str = "core",
    rt_max_s: float = 5.0,
    baseline_s: float | None = None,
    include_warnings: bool = True,
    window: Optional[WindowSpec] = None,
) -> JsonDict:
    """
    Profiles:
      - core: HAIC interaction KPIs + human RT + AI latency
      - full: core + outcome catalogue (precision/recall/etc) when available

    Windowing:
      - window={"basis":"relative","start":10,"end":60}  -> seconds from session start
      - window={"basis":"relative","last":120}           -> last 120 seconds of session
      - window={"basis":"absolute","start":<epoch>,"end":<epoch>} -> epoch seconds
      - window={"basis":"absolute","start":<iso>,"end":<iso>}     -> ISO timestamps
    """
    decisions = extract_decisions(decisions_or_artifact)

    ok, warnings = validate_decisions_minimal(decisions)
    if not ok:
        raise ValueError("Invalid decisions input: " + "; ".join(warnings))

    # Window filtering + summary (v0.1.1)
    artifact = decisions_or_artifact if isinstance(decisions_or_artifact, dict) else None
    decisions_f, events_f, window_summary = filter_decisions_events_by_epoch(
        artifact=artifact,
        decisions=decisions,
        window=window,
    )
    # events_f currently not used by metric calculators; kept for reporting/diagnostics.

    metrics: JsonDict = {}

    # Core HAIC interaction KPIs
    metrics.update(
        compute_interaction_metrics(
            decisions_f,
            baseline_s=baseline_s,
            rt_max=rt_max_s,
        )
    )

    # Auxiliary summaries
    metrics.update(compute_human_rt_metrics(decisions_f))
    metrics.update(compute_latency_metrics(decisions_f))

    # Extended catalogue
    if profile == "full":
        metrics.update(compute_outcome_metrics(decisions_f, profile="core_outcomes"))
    elif profile != "core":
        raise ValueError(f"Unknown profile: {profile}")

    out: JsonDict = {
        "metrics": metrics,
        "window_summary": window_summary,
    }

    if include_warnings:
        out["warnings"] = warnings

    return out
