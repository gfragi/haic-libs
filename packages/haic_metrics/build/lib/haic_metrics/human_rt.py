from __future__ import annotations
from typing import Dict, List, Any, Iterable
import math

def _pctl(xs: List[float], q: float) -> float | None:
    if not xs: return None
    xs = sorted(xs)
    i = (len(xs) - 1) * q
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    if lo == hi: return xs[lo]
    f = i - lo
    return xs[lo] * (1 - f) + xs[hi] * f

def _rt_seconds_from_decision(d: Dict[str, Any]) -> float | None:
    # Prefer explicit seconds if present
    v = d.get("duration_s")
    if isinstance(v, (int, float)): return float(v)
    # Fallback to latency_ms -> seconds
    ms = d.get("latency_ms")
    if isinstance(ms, (int, float)): return float(ms) / 1000.0
    return None

def human_response_percentiles_by(
    logs_root: Dict[str, Any],
    group_key: str = "pilot_tag",
    quantiles: Iterable[float] = (0.5, 0.9, 0.95),
) -> Dict[str, Any]:
    """
    Groups human response times (duration_s or latency_ms) by `group_key`.
    Returns Chart.js-friendly payload + human SLA from extras.rt_limits.rt_max_human_s.
    """
    logs = logs_root.get("logs", [])
    by_group: Dict[str, List[float]] = {}

    # Read SLA cap if present
    rt_caps = (logs_root.get("extras", {}) or {}).get("rt_limits", {})
    sla_human_s = float(rt_caps.get("rt_max_human_s", 30))

    for sess in logs:
        group = str(sess.get(group_key, "unknown"))
        for d in (sess.get("decisions") or []):
            if str(d.get("actor_type", "")).lower() == "human":
                val = _rt_seconds_from_decision(d)
                if val is not None:
                    by_group.setdefault(group, []).append(val)

    labels = sorted(by_group.keys())
    qs = list(quantiles)
    matrix = []
    for q in qs:
        row = []
        for g in labels:
            row.append(_pctl(by_group.get(g, []), q))
        matrix.append(row)

    return {
        "labels": labels,
        "series": [f"p{int(q*100)}" for q in qs],
        "data": matrix,                   # series-major
        "counts": {g: len(xs) for g, xs in by_group.items()},
        "sla_s": sla_human_s,            # seconds
        "group_key": group_key,
    }


def compute_human_rt_metrics(
    decisions: List[Dict[str, Any]],
    *,
    quantiles: Tuple[float, float, float] = (0.5, 0.9, 0.95),
) -> Dict[str, float]:
    """
    Human response-time summary from decisions.
    Returns p50/p90/p95/mean/count (seconds).
    """
    xs: List[float] = []
    for d in decisions:
        # conservative filter: only human decisions
        agent = (d.get("actor_type") or d.get("agent") or d.get("actor") or "").lower()
        if agent and agent not in ("human", "operator", "radiologist"):
            continue
        rt = _rt_seconds_from_decision(d)
        if rt is not None:
            xs.append(rt)

    if not xs:
        return {
            "human_rt_n": 0,
            "human_rt_mean_s": 0.0,
            "human_rt_p50_s": 0.0,
            "human_rt_p90_s": 0.0,
            "human_rt_p95_s": 0.0,
        }

    mean = sum(xs) / len(xs)
    q50, q90, q95 = quantiles
    return {
        "human_rt_n": float(len(xs)),
        "human_rt_mean_s": float(mean),
        "human_rt_p50_s": float(_pctl(xs, q50) or 0.0),
        "human_rt_p90_s": float(_pctl(xs, q90) or 0.0),
        "human_rt_p95_s": float(_pctl(xs, q95) or 0.0),
    }