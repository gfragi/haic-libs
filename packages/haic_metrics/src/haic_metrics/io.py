import json
from pathlib import Path
from typing import Any, Dict, List, Union, Iterable, Optional

JsonDict = Dict[str, Any]


def load_json(path: Union[str, Path]) -> JsonDict:
    path = Path(path)
    with path.open("r", encoding="utf-8") as f:
        return json.load(f)


def load_jsonl(path: Union[str, Path]) -> List[JsonDict]:
    path = Path(path)
    rows: List[JsonDict] = []
    with path.open("r", encoding="utf-8") as f:
        for i, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            try:
                rows.append(json.loads(line))
            except json.JSONDecodeError as e:
                raise ValueError(f"Invalid JSON on line {i} of {path}: {e}") from e
    return rows


def load_decisions_artifact(path: Union[str, Path]) -> JsonDict:
    """
    Loads a decisions artifact expected to contain at least:
      - decisions: List[dict]
    Optionally:
      - run_metadata
      - schema_version
    """
    obj = load_json(path)
    if "decisions" not in obj or not isinstance(obj["decisions"], list):
        raise ValueError(f"{path} is not a decisions artifact (missing 'decisions' list).")
    return obj


def extract_decisions(obj: Union[JsonDict, List[JsonDict]]) -> List[JsonDict]:
    """
    Accept either:
      - artifact dict with 'decisions'
      - list of decisions
    """
    if isinstance(obj, list):
        return obj
    if isinstance(obj, dict) and isinstance(obj.get("decisions"), list):
        return obj["decisions"]
    raise TypeError("Expected a decisions list or an artifact dict with key 'decisions'.")
