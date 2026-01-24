from __future__ import annotations
from typing import List, Dict, Any, Optional, Callable
import math
import datetime as dt

DEFAULT_RT_MAX = 5.0   # seconds
DEFAULT_BASELINE_S = None

# Soft weights for composite EfficiencyScore shaping
_OFFROLE_PENALTY_WEIGHT = 0.35   # 0..1 penalty multiplier
_PROGRESS_BONUS_WEIGHT = 0.10    # 0..1 bonus multiplier

# -------------------- NEW: schema flexibility helpers --------------------
_ALIASES = {
    "agent":        ["agent", "actor_type", "actor", "role"],
    "timestamp":    ["timestamp", "time", "created_at", "event_time", "date"],
    "t":            ["t"],
    "action":       ["action", "event_type", "type", "name"],
    "interaction":  ["interaction_id", "case_id", "ticket_id", "job_id", "image_id"],
    "duration_s":   ["duration_s", "human_duration_s", "duration"],
    "latency_ms":   ["latency_ms", "inference_ms", "latency"],
    "correct":      ["correct", "agreement", "is_correct"],
}

_AGENT_MAP = {"human": "HUMAN", "ai": "AI", "system": "SYS"}

def _get(d: Dict[str, Any], keys) -> Any:
    for k in keys:
        if k in d and d[k] not in (None, "", [], {}):
            return d[k]
    return None

def _canon_str(x: Optional[str]) -> Optional[str]:
    if x is None:
        return None
    s = str(x).strip().lower().replace("&", "and")
    while "  " in s:
        s = s.replace("  ", " ")
    return s

def _parse_ts(ts: Any) -> Optional[dt.datetime]:
    if ts is None:
        return None
    if isinstance(ts, (int, float)):
        # guess ms vs s
        if ts > 1e12:
            ts = ts / 1000.0
        try:
            return dt.datetime.fromtimestamp(ts, tz=dt.timezone.utc)
        except Exception:
            return None
    try:
        s = str(ts).replace("Z", "+00:00")
        return dt.datetime.fromisoformat(s)
    except Exception:
        return None

def _sec(a: dt.datetime, b: dt.datetime) -> float:
    return (b - a).total_seconds()

def _normalize_decisions(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Make keys consistent:
      - ensure 'agent' exists (copied/mapped from actor_type/actor/role when needed)
      - ensure numeric 't' exists (derived from timestamps or sequence order)
      - keep existing duration_s / latency_ms; accept alias names
    """
    if not decisions:
        return []

    # First pass: copy and harvest timestamps
    norm_rows: List[Dict[str, Any]] = []
    all_ts: List[dt.datetime] = []

    for e in decisions:
        if not isinstance(e, dict):
            continue
        row = dict(e)  # shallow copy

        # Agent
        if "agent" not in row:
            raw_agent = _get(row, _ALIASES["agent"])
            can = _canon_str(raw_agent)
            mapped = _AGENT_MAP.get(can, raw_agent)
            if mapped is not None:
                row["agent"] = mapped
            # also mirror actor_type to keep existing HCL logic working
            if "actor_type" not in row and raw_agent is not None:
                row["actor_type"] = str(raw_agent).lower()

        # Timestamp
        ts = _get(row, _ALIASES["timestamp"])
        ts_dt = _parse_ts(ts)
        if ts_dt is not None:
            all_ts.append(ts_dt)
            row.setdefault("_timestamp_dt", ts_dt)  # internal helper

        # t (seconds)
        if "t" not in row or row["t"] is None:
            row["t"] = None  # will fill later

        # duration_s
        if "duration_s" not in row or row["duration_s"] is None:
            dur = _get(row, _ALIASES["duration_s"])
            if dur is not None:
                try:
                    row["duration_s"] = float(dur)
                except Exception:
                    pass

        # latency_ms
        if "latency_ms" not in row or row["latency_ms"] is None:
            lat = _get(row, _ALIASES["latency_ms"])
            if lat is not None:
                try:
                    row["latency_ms"] = float(lat)
                except Exception:
                    pass

        norm_rows.append(row)

    # Derive t from timestamps (or from order) if missing
    s_start = min(all_ts) if all_ts else None
    monotonic = 0.0
    for r in norm_rows:
        if r.get("t") is None:
            if s_start and r.get("_timestamp_dt") is not None:
                r["t"] = max(0.0, _sec(s_start, r["_timestamp_dt"]))
            else:
                r["t"] = monotonic
                monotonic += 1.0

    return norm_rows

# -------------------- existing helpers (some made more flexible) --------------------
def _only_agent_rows(decisions: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """Filter to rows that represent agent actions."""
    return [
        e for e in decisions
        if isinstance(e, dict) and ("agent" in e or "actor_type" in e)
    ]

def _total_time(decisions: List[Dict[str, Any]], explicit_T: Optional[float]) -> float:
    """
    Prefer explicit_T; else use t-range; else fallback to timestamp range (if present).
    """
    if explicit_T is not None:
        return float(explicit_T)
    if not decisions:
        return 0.0
    # Try t-range
    try:
        t0 = float(min(e.get("t", 0.0) for e in decisions))
        tN = float(max(e.get("t", 0.0) for e in decisions))
        span = max(0.0, tN - t0)
        if span > 0:
            return span
    except Exception:
        pass
    # Fallback: timestamp range (if normalization left _timestamp_dt)
    ts_vals = [e.get("_timestamp_dt") for e in decisions if e.get("_timestamp_dt") is not None]
    if ts_vals:
        return max(0.0, _sec(min(ts_vals), max(ts_vals)))
    return 0.0

def _durations(decisions: List[Dict[str, Any]]) -> List[float]:
    # Prefer explicit duration_s, fallback to latency_ms (sec)
    durs: List[float] = []
    for e in decisions:
        if e.get("duration_s") is not None:
            try:
                durs.append(max(0.0, float(e["duration_s"])))
            except Exception:
                durs.append(0.0)
        elif e.get("latency_ms") is not None:
            try:
                durs.append(max(0.0, float(e["latency_ms"]) / 1000.0))
            except Exception:
                durs.append(0.0)
    return durs

def _mean(xs: List[float]) -> float:
    return sum(xs) / len(xs) if xs else 0.0

def _clip01(x: float) -> float:
    return max(0.0, min(1.0, x))

def _safe_prob_dist(p: Dict[str, float]) -> Dict[str, float]:
    total = sum(max(0.0, float(v)) for v in p.values())
    if total <= 0:
        return {k: 0.0 for k in p.keys()}
    return {k: max(0.0, float(v)) / total for k, v in p.items()}

def _aggregate_probs(decisions: List[Dict[str, Any]], key: str) -> Dict[str, float]:
    """
    Average probability vectors over all decisions that have `key` (e.g., 'probs' or 'surrogate_probs'),
    then re-normalize. This yields P_human or P_surrogate for S.
    """
    accum: Dict[str, float] = {}
    count = 0
    for e in decisions:
        if key in e and isinstance(e[key], dict) and e[key]:
            dist = _safe_prob_dist(e[key])
            for a, p in dist.items():
                accum[a] = accum.get(a, 0.0) + p
            count += 1
    if count == 0 or not accum:
        return {}
    # average and renormalize
    avg = {k: v / count for k, v in accum.items()}
    return _safe_prob_dist(avg)

def _kl_divergence(p: Dict[str, float], q: Dict[str, float], eps: float = 1e-12) -> float:
    """
    KL(P||Q) over the union of keys. Both are probabilities over actions.
    """
    keys = set(p.keys()) | set(q.keys())
    kl = 0.0
    for k in keys:
        pk = max(eps, p.get(k, 0.0))
        qk = max(eps, q.get(k, 0.0))
        kl += pk * math.log(pk / qk)
    return kl

def _count(decisions: List[Dict[str, Any]], pred: Callable[[Dict[str, Any]], bool]) -> int:
    return sum(1 for e in decisions if pred(e))

# -------------------- main API (with normalization step) --------------------
def compute_metrics(
    *,
    decisions: List[Dict[str, Any]],
    T: Optional[float] = None,
    baseline_s: Optional[float] = DEFAULT_BASELINE_S,
    rt_max: float = DEFAULT_RT_MAX,
) -> Dict[str, float]:
    """
    Returns dict with keys: F, D, HCL, Tr, A, S, EL, EfficiencyScore
    Assumes decisions are sorted by 't' ascending.
    Now robust to alias keys and missing 't' via normalization.
    """
    # NEW: normalize decisions to tolerate aliases/missing fields
    decisions = _normalize_decisions(decisions)

    # keep original ordering intent: sort by t (now guaranteed numeric)
    decisions = sorted(decisions, key=lambda e: float(e.get("t", float("inf"))))
    agent_rows = _only_agent_rows(decisions)
    N_agents = len(agent_rows)

    # --- Time window over agent rows only (now uses t or timestamp fallback) ---
    total_time = _total_time(agent_rows, T)

    # 1) F: interactions per minute (agent-only)
    F = (N_agents / (total_time / 60.0)) if total_time > 0 else 0.0

    # 2) D: mean atomic action duration (agent-only)
    durs = _durations(agent_rows)
    D = _mean(durs)

    # 3) HCL: prefer human agent rows; fallback to agent rows
    human_rts = [
        (float(e["duration_s"]) if e.get("duration_s") is not None
         else float(e.get("latency_ms", 0.0)) / 1000.0)
        for e in agent_rows
        if str(e.get("actor_type", "")).lower() == "human" or str(e.get("agent", "")).upper().startswith("H")
    ]
    latencies_s = [
        float(e.get("latency_ms", 0.0)) / 1000.0
        for e in agent_rows
        if e.get("latency_ms") is not None
    ]
    if human_rts:
        mean_rt = _mean(human_rts)
    elif durs:
        mean_rt = _mean(durs)
    elif latencies_s:
        mean_rt = _mean(latencies_s)
    else:
        mean_rt = rt_max if rt_max > 0 else 1.0
    HCL = _clip01(1.0 - (mean_rt / rt_max if rt_max > 0 else 1.0))

    # 4) Tr: only score rows that are explicitly labeled OR explicit error events
    labeled = 0
    errors = 0
    for e in agent_rows:
        if e.get("correct") is not None:
            labeled += 1
            if e.get("correct") is False:
                errors += 1
    for e in decisions:
        if str(e.get("event_type", "")).lower() == "error":
            labeled += 1
            errors += 1
    Tr = _clip01(1.0 - (errors / labeled if labeled > 0 else 0.0))

    # 5) A: adaptability on agent rows; clamp to [-1, 1] via tanh
    if N_agents > 0:
        k = max(1, int(0.2 * N_agents))
        early = agent_rows[:k]
        late = agent_rows[-k:]

        def acc(arr):
            have = [e for e in arr if e.get("correct") is not None]
            if not have:
                return 1.0  # neutral if unlabeled
            return sum(1 for e in have if e.get("correct") is True) / len(have)

        acc_early = acc(early)
        acc_late = acc(late)
        denom = max(1e-9, acc_early)
        raw_A = (acc_late - acc_early) / denom
        A = math.tanh(raw_A)  # bounded [-1, 1]
    else:
        A = 0.0

    # 6) S: surrogate similarity (use agent rows)
    P_h = _aggregate_probs(agent_rows, "probs")
    P_s = _aggregate_probs(agent_rows, "surrogate_probs")
    if P_h and P_s:
        D_kl = _kl_divergence(P_h, P_s)
        S = math.exp(-D_kl)
    else:
        matches, compared = 0, 0
        for e in agent_rows:
            if "surrogate_action" in e:
                compared += 1
                if e.get("action") == e.get("surrogate_action"):
                    matches += 1
        S = (matches / compared) if compared > 0 else 0.0
    S = _clip01(S)

    # 7) EL: effort/efficiency loss vs baseline (use agent-window time)
    if baseline_s is not None and baseline_s > 0 and total_time > 0:
        EL = max(0.0, (total_time - baseline_s) / baseline_s)
    else:
        EL = 0.0

    # Base efficiency from EL only
    EfficiencyScore = 1.0 / (1.0 + float(EL)) if EL >= 0 else 1.0

    # ---- Gentle shaping with off-role and progress signals (if present) ----
    def _count_pred(rows: List[Dict[str, Any]], pred: Callable[[Dict[str, Any]], bool]) -> int:
        return sum(1 for e in rows if pred(e))

    offrole_count = _count_pred(agent_rows, lambda e: bool(e.get("off_role_action")))
    offrole_rate = (offrole_count / N_agents) if N_agents > 0 else 0.0

    progress_count = _count(decisions, lambda e: str(e.get("event_type", "")).lower() in {"checklist_progress", "progress"})
    progress_rate = (progress_count / max(1.0, total_time)) if total_time > 0 else 0.0  # events/sec

    EfficiencyScore *= (1.0 - _OFFROLE_PENALTY_WEIGHT * _clip01(offrole_rate))
    EfficiencyScore *= (1.0 + _PROGRESS_BONUS_WEIGHT * _clip01(progress_rate))
    EfficiencyScore = _clip01(EfficiencyScore)

    return {
        "F": float(F),
        "D": float(D),
        "HCL": float(HCL),
        "Tr": float(Tr),
        "A": float(A),
        "S": float(S),
        "EL": float(EL),
        "EfficiencyScore": float(EfficiencyScore),
    }

def compute_metrics_by_agent(decisions: List[Dict[str, Any]], **kw) -> Dict[str, Dict[str, float]]:
    out: Dict[str, Dict[str, float]] = {}
    decs = _normalize_decisions(decisions)  # NEW: normalize before bucketing
    by_agent: Dict[str, List[Dict[str, Any]]] = {}
    for d in decs:
        by_agent.setdefault(str(d.get("agent")), []).append(d)
    for agent, arr in by_agent.items():
        out[agent] = compute_metrics(decisions=arr, **kw)
    return out


def compute_interaction_metrics(
    decisions,
    *,
    T=None,
    baseline_s=DEFAULT_BASELINE_S,
    rt_max=DEFAULT_RT_MAX,
):
    """
    Core HAIC interaction KPIs:
    F, D, HCL, Tr, A, S, EL, EfficiencyScore
    """
    return compute_metrics(decisions=decisions, T=T, baseline_s=baseline_s, rt_max=rt_max)