from pathlib import Path
from typing import Any, Dict, List

from .json import write_json


def write_decisions_json(path: Path, decisions: List[Dict[str, Any]]) -> None:
    write_json(path, {"decisions": decisions})
