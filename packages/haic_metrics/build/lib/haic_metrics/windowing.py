from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List, Optional, Tuple, Union, Literal

JsonDict = Dict[str, Any]


def _is_number(x: Any) -> bool:
    return isinstance(x, (int, float)) and not isinstance(x, bool)


def parse_time_value(v: Union[float, int, str], *, notes: Optional[List[str]] = None) -> float:
    """
    Parse epoch seconds (float/int) or ISO datetime string to epoch seconds (float).

    ISO supported:
      - '2026-01-31T12:00:00Z'
      - '2026-01-31T12:00:00+02:00'
      - '2026-01-31T12:00:00' (naive -> assumed UTC; note added)
    """
    if _is_number(v):
        return float(v)

    if not isinstance(v, str):
        raise ValueError(f"Unsupported time value type: {type(v)}")

    s = v.strip()

    # Normalize 'Z' to '+00:00' for fromisoformat
    if s.endswith("Z"):
        s = s[:-1] + "+00:00"

    try:
        dt = datetime.fromisoformat(s)
    except Exception as e:
        raise ValueError(f"Invalid ISO datetime: {v!r}") from e

    if dt.tzinfo is None:
        # assume UTC, but make it visible
        if notes is not None:
            notes.append("Naive ISO datetime provided; assuming UTC.")
        dt = dt.replace(tzinfo=timezone.utc)

    return dt.timestamp()


def _get_meta_start_end_epoch(artifact: Optional[JsonDict]) -> Tuple[Optional[float], Optional[float]]:
    if not artifact or not isinstance(artifact, dict):
        return None, None
    meta = artifact.get("meta")
    if not isinstance(meta, dict):
        return None, None
    ts = meta.get("timestamps")
    if not isinstance(ts, dict):
        return None, None

    start = ts.get("start_time")
    end = ts.get("end_time")
    start_epoch = float(start) if _is_number(start) else None
    end_epoch = float(end) if _is_number(end) else None
    return start_epoch, end_epoch


def _min_max_t_epoch(decisions: List[JsonDict]) -> Tuple[Optional[float], Optional[float]]:
    t_vals: List[float] = []
    for d in decisions:
        if isinstance(d, dict) and _is_number(d.get("t")):
            t_vals.append(float(d["t"]))
    if not t_vals:
        return None, None
    return min(t_vals), max(t_vals)


def get_session_start_epoch(
    artifact: Optional[JsonDict],
    decisions: List[JsonDict],
    notes: List[str],
) -> Optional[float]:
    """
    Prefer artifact meta.timestamps.start_time; fallback to min(decision['t']).
    """
    meta_start, _ = _get_meta_start_end_epoch(artifact)
    if meta_start is not None:
        return meta_start

    d_min, _ = _min_max_t_epoch(decisions)
    if d_min is not None:
        notes.append("Fallback: meta.timestamps.start_time missing; using min(decision.t) as session start.")
        return d_min

    notes.append("No usable timestamps found to establish session start.")
    return None


def resolve_window_bounds(
    artifact: Optional[JsonDict],
    decisions: List[JsonDict],
    window: Dict[str, Any],
) -> Tuple[Optional[float], Optional[float], Dict[str, Any], List[str]]:
    """
    Returns:
      (t_start_epoch, t_end_epoch, effective_meta, notes)

    effective_meta includes:
      - basis
      - requested (verbatim window)
      - effective (epoch + relative if basis=relative)
    """
    notes: List[str] = []

    if not isinstance(window, dict):
        raise ValueError("window must be a dict")

    basis = window.get("basis")
    if basis not in ("relative", "absolute"):
        raise ValueError("window['basis'] must be 'relative' or 'absolute'")

    requested = dict(window)

    # Validate mutually exclusive keys
    has_start = "start" in window
    has_end = "end" in window
    has_last = "last" in window

    if basis == "relative":
        if has_last and (has_start or has_end):
            raise ValueError("For relative windows, use either {'last': N} or {'start':..., 'end':...}, not both.")
        if has_last:
            if not _is_number(window["last"]):
                raise ValueError("window['last'] must be a number (seconds) for relative windows.")
        else:
            if not (has_start and has_end):
                raise ValueError("Relative window requires both 'start' and 'end' (seconds) unless using 'last'.")
            if not (_is_number(window["start"]) and _is_number(window["end"])):
                raise ValueError("Relative window 'start'/'end' must be numbers (seconds).")

        t0 = get_session_start_epoch(artifact, decisions, notes)
        if t0 is None:
            # Cannot resolve relative bounds without a reference start
            return None, None, {"basis": basis, "requested": requested, "effective": {}}, notes

        # Determine session end for 'last'
        meta_start, meta_end = _get_meta_start_end_epoch(artifact)
        d_min, d_max = _min_max_t_epoch(decisions)
        session_end = meta_end if meta_end is not None else d_max

        if has_last:
            if session_end is None:
                notes.append("Cannot resolve relative 'last' window end; missing session end time.")
                return None, None, {"basis": basis, "requested": requested, "effective": {}}, notes
            last_s = float(window["last"])
            t_end = float(session_end)
            t_start = max(float(t0), t_end - last_s)
            rel_start = t_start - float(t0)
            rel_end = t_end - float(t0)
        else:
            rel_start = float(window["start"])
            rel_end = float(window["end"])
            if rel_end < rel_start:
                raise ValueError("Relative window 'end' must be >= 'start'.")
            t_start = float(t0) + rel_start
            t_end = float(t0) + rel_end

        effective = {
            "t_start_epoch": t_start,
            "t_end_epoch": t_end,
            "t_start_rel_s": rel_start,
            "t_end_rel_s": rel_end,
            "session_start_epoch": float(t0),
        }

        return t_start, t_end, {"basis": basis, "requested": requested, "effective": effective}, notes

    # basis == "absolute"
    if not (has_start and has_end):
        raise ValueError("Absolute window requires both 'start' and 'end' (epoch seconds or ISO strings).")

    t_start = parse_time_value(window["start"], notes=notes)
    t_end = parse_time_value(window["end"], notes=notes)

    if t_end < t_start:
        raise ValueError("Absolute window 'end' must be >= 'start'.")

    effective = {
        "t_start_epoch": float(t_start),
        "t_end_epoch": float(t_end),
    }
    return float(t_start), float(t_end), {"basis": basis, "requested": requested, "effective": effective}, notes


def filter_decisions_events_by_epoch(
    artifact: Optional[JsonDict],
    decisions: List[JsonDict],
    window: Optional[Dict[str, Any]],
) -> Tuple[List[JsonDict], List[JsonDict], Dict[str, Any]]:
    """
    Returns (decisions_filt, events_filt, window_summary)

    - If window is None: passthrough + summary that indicates full range.
    - If artifact contains 'events', filter them too; else events_filt=[].
    - Summary includes counts before/after and effective duration.
    """
    # Collect events (if present)
    events: List[JsonDict] = []
    if artifact and isinstance(artifact, dict):
        ev = artifact.get("events")
        if isinstance(ev, list):
            events = [e for e in ev if isinstance(e, dict)]

    decisions_total = len([d for d in decisions if isinstance(d, dict)])
    events_total = len(events)

    # No window -> passthrough with a minimal summary
    if window is None:
        d_min, d_max = _min_max_t_epoch(decisions)
        duration_s = 0.0
        if d_min is not None and d_max is not None:
            duration_s = max(0.0, d_max - d_min)
        window_summary = {
            "basis": "absolute",
            "requested": {"mode": "full"},
            "effective": {
                "t_start_epoch": d_min,
                "t_end_epoch": d_max,
            },
            "counts": {
                "decisions_total": decisions_total,
                "decisions_used": decisions_total,
                "events_total": events_total,
                "events_used": events_total,
            },
            "duration_s": duration_s,
            "notes": [],
        }
        return decisions, events, window_summary

    # Resolve bounds
    t_start, t_end, eff_meta, notes = resolve_window_bounds(artifact, decisions, window)

    if t_start is None or t_end is None:
        # can't filter reliably
        window_summary = {
            "basis": eff_meta.get("basis", "unknown"),
            "requested": eff_meta.get("requested", dict(window)),
            "effective": eff_meta.get("effective", {}),
            "counts": {
                "decisions_total": decisions_total,
                "decisions_used": 0,
                "events_total": events_total,
                "events_used": 0,
            },
            "duration_s": 0.0,
            "notes": notes + ["Window bounds could not be resolved; no items selected."],
        }
        return [], [], window_summary

    # Filter decisions/events
    missing_t_decisions = 0
    decisions_f: List[JsonDict] = []
    for d in decisions:
        if not isinstance(d, dict):
            continue
        if not _is_number(d.get("t")):
            missing_t_decisions += 1
            continue
        tt = float(d["t"])
        if t_start <= tt <= t_end:
            decisions_f.append(d)

    missing_t_events = 0
    events_f: List[JsonDict] = []
    for e in events:
        if not _is_number(e.get("t")):
            missing_t_events += 1
            continue
        tt = float(e["t"])
        if t_start <= tt <= t_end:
            events_f.append(e)

    if missing_t_decisions:
        notes.append(f"{missing_t_decisions} decisions missing numeric 't' were excluded from windowing.")
    if missing_t_events:
        notes.append(f"{missing_t_events} events missing numeric 't' were excluded from windowing.")

    duration_s = max(0.0, float(t_end) - float(t_start))

    window_summary = {
        "basis": eff_meta.get("basis", "unknown"),
        "requested": eff_meta.get("requested", dict(window)),
        "effective": eff_meta.get("effective", {}),
        "counts": {
            "decisions_total": decisions_total,
            "decisions_used": len(decisions_f),
            "events_total": events_total,
            "events_used": len(events_f),
        },
        "duration_s": duration_s,
        "notes": notes,
    }
    return decisions_f, events_f, window_summary
