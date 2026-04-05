from typing import Any, Dict, List, Tuple

JsonDict = Dict[str, Any]

def validate_decisions_minimal(decisions: List[JsonDict]) -> Tuple[bool, List[str]]:
    warnings: List[str] = []
    if not isinstance(decisions, list):
        return False, ["decisions is not a list"]
    for i, d in enumerate(decisions[:10]):
        if not isinstance(d, dict):
            return False, [f"decision[{i}] is not a dict"]
        if "actor_type" not in d:
            warnings.append(f"decision[{i}] missing actor_type")
        if "action" not in d and "event_type" not in d:
            warnings.append(f"decision[{i}] missing action/event_type")
        if "t" not in d and "timestamp" not in d and "ts" not in d:
            warnings.append(f"decision[{i}] missing time key (t/timestamp/ts)")
    return True, warnings
