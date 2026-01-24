from __future__ import annotations

import logging
import platform
import threading
import time
import uuid
from dataclasses import dataclass
from pathlib import Path
from typing import Any, Dict, Optional, List

import psutil

from .schema import (
    HAIC_SCHEMA_VERSION,
    DECISION_SCHEMA_VERSION,
    DEFAULT_PILOT_TAG,
    DEFAULT_APP_NAME,
    DEFAULT_APP_VERSION,
    EVENTS_SCHEMA_VERSION,
    DECISIONS_ARTIFACT_SCHEMA,
)
from .sinks import append_jsonl, write_json

logger = logging.getLogger(__name__)

JsonDict = Dict[str, Any]


def _to_float_or_none(x):
    if x is None:
        return None
    if isinstance(x, (int, float)):
        return float(x)
    if isinstance(x, str):
        try:
            return float(x)
        except ValueError:
            return None
    return None


def _optional_gpu_usage_percent() -> Optional[float]:
    # Make pynvml optional (no hard dependency)
    try:
        import pynvml  # type: ignore
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        pynvml.nvmlShutdown()
        return float(util.gpu)
    except Exception:
        return None


def get_machine_metrics() -> JsonDict:
    try:
        metrics: JsonDict = {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "cpu_model_mhz": psutil.cpu_freq().current if psutil.cpu_freq() else 0.0,
            "cpu_count": psutil.cpu_count(),
            "ram_total_gb": float(psutil.virtual_memory().total >> 30),
            "disk_total_gb": float(psutil.disk_usage("/").total >> 30),
        }
        gpu = _optional_gpu_usage_percent()
        if gpu is not None:
            metrics["gpu_usage_percent"] = gpu
        return metrics
    except Exception as e:
        logger.warning(f"Failed to get machine metrics: {e}")
        return {"hostname": "unknown", "os": "unknown"}


def _resource_tracker(stop_flag: threading.Event, dest: JsonDict, interval_s: int) -> None:
    while not stop_flag.is_set():
        try:
            sample: JsonDict = {
                "t": time.time(),
                "cpu_usage_percent": psutil.cpu_percent(),
                "ram_usage_percent": psutil.virtual_memory().percent,
                "disk_usage_percent": psutil.disk_usage("/").percent,
            }
            gpu = _optional_gpu_usage_percent()
            if gpu is not None:
                sample["gpu_usage_percent"] = gpu
            dest.setdefault("resource_usage", []).append(sample)
        except Exception as e:
            logger.debug(f"Resource tracking error: {e}")
        stop_flag.wait(interval_s)


@dataclass
class HaicLogger:
    log_dir: Path
    pilot_tag: str = DEFAULT_PILOT_TAG
    app_name: str = DEFAULT_APP_NAME
    app_version: str = DEFAULT_APP_VERSION
    app_mode: Optional[str] = None

    model_name: Optional[str] = None
    model_type: Optional[str] = None
    model_version: Optional[str] = None
    inference_config: Optional[JsonDict] = None

    task: Optional[JsonDict] = None
    human: Optional[JsonDict] = None

    enable_resource_tracking: bool = False
    resource_interval_s: int = 10

    # Internals
    session_id: str = ""
    run_id: str = ""
    _event_seq: int = 0
    _decision_seq: int = 0
    _events: List[JsonDict] = None  # type: ignore
    _decisions: List[JsonDict] = None  # type: ignore
    _machine: JsonDict = None  # type: ignore
    _stop_evt: threading.Event = None  # type: ignore
    _tracker_thread: Optional[threading.Thread] = None
    _start_time: float = 0.0
    _end_time: Optional[float] = None

    def __post_init__(self) -> None:
        self.log_dir = Path(self.log_dir)
        self.session_id = str(uuid.uuid4())
        self.run_id = str(uuid.uuid4())
        self._event_seq = 0
        self._decision_seq = 0
        self._events = []
        self._decisions = []
        self._machine = get_machine_metrics()
        self._stop_evt = threading.Event()
        self._start_time = time.time()
        self._end_time = None

        if self.inference_config is None:
            self.inference_config = {}

        if self.task is None:
            self.task = {
                "name": "unknown_task",
                "domain": "unknown_domain",
                "unit_of_work": "item",
            }

        if self.human is None:
            self.human = {"actor_id": None, "role": "human", "expertise": "unknown"}

        # Optional resource tracking
        if self.enable_resource_tracking:
            self._tracker_thread = threading.Thread(
                target=_resource_tracker,
                args=(self._stop_evt, self._machine, self.resource_interval_s),
                daemon=True,
            )
            self._tracker_thread.start()

        # Emit session_start event (mirrors your pattern)
        self.log_event(
            event_type="session_start",
            actor="system",
            payload={"pilot_tag": self.pilot_tag, "app_mode": self.app_mode},
        )

    @property
    def events_path(self) -> Path:
        return self.log_dir / f"run_{self.run_id}.jsonl"

    @property
    def decisions_path(self) -> Path:
        return self.log_dir / f"haic_decisions_{self.run_id}.json"

    def run_metadata(self) -> JsonDict:
        return {
            "schema_version": HAIC_SCHEMA_VERSION,
            "run_id": self.run_id,
            "session_id": self.session_id,
            "pilot_tag": self.pilot_tag,
            "application": {
                "name": self.app_name,
                "version": self.app_version,
                "mode": self.app_mode,
            },
            "ai_system": {
                "model_name": self.model_name,
                "model_type": self.model_type,
                "model_version": self.model_version,
                "inference_config": self.inference_config or {},
            },
            "task": self.task,
            "human": self.human,
            "infrastructure": self._machine,
            "timestamps": {"start_time": self._start_time, "end_time": self._end_time},
        }

    def log_event(
        self,
        *,
        event_type: str,
        actor: str = "system",
        payload: Optional[JsonDict] = None,
        context_overrides: Optional[JsonDict] = None,
        t: Optional[float] = None,
    ) -> JsonDict:
        payload = payload or {}
        context_overrides = context_overrides or {}
        t = t if t is not None else time.time()

        self._event_seq += 1
        event: JsonDict = {
            "schema_version": EVENTS_SCHEMA_VERSION,
            "event_id": str(uuid.uuid4()),
            "event_type": event_type,
            "t": t,
            "seq": self._event_seq,
            "actor": actor,  # "human"|"ai"|"system"
            "context": {
                "run_id": self.run_id,
                "session_id": self.session_id,
                "pilot_tag": self.pilot_tag,
                "app_version": self.app_version,
                "app_mode": self.app_mode,
                "model_name": self.model_name,
                "model_version": self.model_version,
                **context_overrides,
            },
            "payload": payload,
        }

        self._events.append(event)
        append_jsonl(self.events_path, event)
        return event

    def log_decision(
        self,
        *,
        actor_type: str,   # "ai" | "human" | "system"
        action: str,       # controlled vocabulary
        object_id: str,    # image_id / item id
        payload: Optional[JsonDict] = None,
        duration_s: Optional[float] = None,
        latency_ms: Optional[float] = None,
        correct: Optional[bool] = None,
        t: Optional[float] = None,
    ) -> JsonDict:
        payload = payload or {}
        t = t if t is not None else time.time()

        self._decision_seq += 1
        entry: JsonDict = {
            "schema_version": DECISION_SCHEMA_VERSION,
            "seq": self._decision_seq,
            "t": t,
            "actor_type": actor_type,
            "action": action,
            "object_id": object_id,
            "duration_s": _to_float_or_none(duration_s),
            "latency_ms": _to_float_or_none(latency_ms),
            "correct": correct,
            "payload": payload,
        }

        self._decisions.append(entry)
        return entry

    def export_decisions_artifact(self, filename: Optional[str] = None) -> Path:
        rm = self.run_metadata()
        artifact: JsonDict = {
            "artifact_schema": DECISIONS_ARTIFACT_SCHEMA,
            "schema_version": DECISION_SCHEMA_VERSION,
            "session_id": self.session_id,
            "run_id": self.run_id,
            "meta": {
                "pilot_tag": self.pilot_tag,
                "application": rm.get("application", {}),
                "ai_system": rm.get("ai_system", {}),
                "task": rm.get("task", {}),
                "human": rm.get("human", {}),
                "infrastructure": self._machine,
                "timestamps": rm.get("timestamps", {}),
            },
            "decisions": list(self._decisions),
            # optional raw events for debugging
            "events": list(self._events),
        }

        out = Path(filename) if filename else self.decisions_path
        write_json(out, artifact)
        return out

    def close(self) -> None:
        if self._end_time is None:
            self._end_time = time.time()

        # session_end event
        self.log_event(event_type="session_end", actor="system", payload={"session_end_time": self._end_time})

        # stop resource tracking
        if self.enable_resource_tracking and self._tracker_thread:
            self._stop_evt.set()
            self._tracker_thread.join(timeout=5)

    def __enter__(self) -> "HaicLogger":
        return self

    def __exit__(self, exc_type, exc, tb) -> None:
        self.close()
