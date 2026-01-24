from __future__ import annotations
from typing import Dict, List, Any, Iterable, Tuple
import math

def _pctl(xs: List[float], q: float) -> float | None:
    if not xs: return None
    xs = sorted(xs)
    i = (len(xs) - 1) * q
    lo, hi = int(math.floor(i)), int(math.ceil(i))
    if lo == hi: return xs[lo]
    f = i - lo
    return xs[lo] * (1 - f) + xs[hi] * f

def _latency_ms_from_decision(d: Dict[str, Any]) -> float | None:
    # Primary: latency_ms already in ms
    v = d.get("latency_ms")
    if isinstance(v, (int, float)): return float(v)
    # Fallbacks (try to be forgiving)
    s = d.get("duration_s")
    if isinstance(s, (int, float)): return 1000.0 * float(s)
    v = d.get("latency")  # might be sec or ms; assume sec if small
    if isinstance(v, (int, float)):
        v = float(v)
        return v * 1000.0 if v < 500 else v
    return None

def latency_percentiles_by(
    logs_root: Dict[str, Any],
    group_key: str = "ai_model_version",
    quantiles: Iterable[float] = (0.5, 0.9, 0.95),
) -> Dict[str, Any]:
    """
    Accepts a HAIC log root with {"logs":[{session...}]}
    Groups latencies from ai_evaluated decisions by `group_key` (default: ai_model_version).
    Returns Chart.js-friendly payload + SLA caps (if present).
    """
    logs = logs_root.get("logs", [])
    by_group: Dict[str, List[float]] = {}

    # read SLA caps if present
    rt_caps = (logs_root.get("extras", {}) or {}).get("rt_limits", {})
    sla_ai_ms = float(rt_caps.get("rt_max_ai_ms", 5000))

    for sess in logs:
        group = str(sess.get(group_key, "unknown"))
        for d in sess.get("decisions", []) or []:
            if str(d.get("action", "")).lower() in {"ai_evaluated", "classify", "forecast"}:
                v = _latency_ms_from_decision(d)
                if v is not None:
                    by_group.setdefault(group, []).append(v)

    labels = sorted(by_group.keys())
    q_list = list(quantiles)
    matrix = []
    for q in q_list:
        row = []
        for g in labels:
            row.append(_pctl(by_group.get(g, []), q))
        matrix.append(row)

    return {
        "labels": labels,                # x-axis: groups (models)
        "series": [f"p{int(q*100)}" for q in q_list],
        "data": matrix,                  # series-major: data[i_series][i_label]
        "counts": {g: len(xs) for g, xs in by_group.items()},
        "sla_ms": sla_ai_ms,
        "group_key": group_key,
    }


_AI_ACTIONS = {"ai_evaluated", "classify", "forecast", "ai_inference", "ai_decision"}

def compute_latency_metrics(
    decisions: List[Dict[str, Any]],
    *,
    quantiles: Tuple[float, float, float] = (0.5, 0.9, 0.95),
) -> Dict[str, float]:
    """
    AI latency summary from decisions.
    Returns p50/p90/p95/mean/count (milliseconds).
    """
    xs: List[float] = []
    for d in decisions:
        action = (d.get("action") or d.get("event_type") or d.get("type") or "").lower()
        agent = (d.get("actor_type") or d.get("agent") or d.get("actor") or "").lower()

        # permissive filter: either AI agent OR known AI action
        is_ai = agent in ("ai", "model") or (action in _AI_ACTIONS)
        if not is_ai:
            continue

        ms = _latency_ms_from_decision(d)
        if ms is not None:
            xs.append(ms)

    if not xs:
        return {
            "ai_latency_n": 0,
            "ai_latency_mean_ms": 0.0,
            "ai_latency_p50_ms": 0.0,
            "ai_latency_p90_ms": 0.0,
            "ai_latency_p95_ms": 0.0,
        }

    mean = sum(xs) / len(xs)
    q50, q90, q95 = quantiles
    return {
        "ai_latency_n": float(len(xs)),
        "ai_latency_mean_ms": float(mean),
        "ai_latency_p50_ms": float(_pctl(xs, q50) or 0.0),
        "ai_latency_p90_ms": float(_pctl(xs, q90) or 0.0),
        "ai_latency_p95_ms": float(_pctl(xs, q95) or 0.0),
    }