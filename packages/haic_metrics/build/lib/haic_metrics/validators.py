from typing import Any, Dict, List, Tuple, Optional

JsonDict = Dict[str, Any]


def validate_decisions_minimal(decisions: List[JsonDict]) -> Tuple[bool, List[str]]:
    """
    Minimal checks to prevent silent nonsense.
    Returns (ok, warnings).
    """
    warnings: List[str] = []
    if not isinstance(decisions, list):
        return False, ["decisions is not a list"]

    if len(decisions) == 0:
        warnings.append("decisions list is empty")
        return True, warnings  # not fatal

    # Check a few rows
    sample = decisions[:10]
    for idx, d in enumerate(sample):
        if not isinstance(d, dict):
            return False, [f"decision[{idx}] is not a dict"]

        # Not enforcing a strict schema; just sanity hints
        has_any_time = any(k in d for k in ("timestamp", "ts", "t", "time"))
        if not has_any_time:
            warnings.append(f"decision[{idx}] has no timestamp key (timestamp/ts/t/time).")

        has_any_type = any(k in d for k in ("event_type", "action", "type"))
        if not has_any_type:
            warnings.append(f"decision[{idx}] has no type key (event_type/action/type).")

    return True, warnings
