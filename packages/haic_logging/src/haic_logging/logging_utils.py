

import json
import time
import threading
import psutil
import platform
import uuid
import logging
from typing import Dict, Optional, Any
from pathlib import Path
import pynvml

logger = logging.getLogger(__name__)

# -------------------------
# HAIC schema constants
# -------------------------
HAIC_SCHEMA_VERSION = "haic.run.v1"
DEFAULT_PILOT_TAG = "radiology-toy"
DEFAULT_APP_NAME = "annotation_tool"
DEFAULT_APP_VERSION = "0.1.0"


def _to_float_or_none(x):
    """Convert x to float if possible, else None (for DB-safe numeric fields)."""
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


def _to_str_or_none(x):
    """Convert x to str if meaningful, else None (for DB-safe text fields)."""
    if x is None:
        return None
    if isinstance(x, str):
        return x
    if isinstance(x, (list, dict)):
        return None
    return str(x)


def get_session_id() -> str:
    """Generate a unique session ID."""
    return str(uuid.uuid4())


def get_run_id() -> str:
    """Generate a unique HAIC run ID (separate from session_id)."""
    return str(uuid.uuid4())


def get_event_id() -> str:
    """Generate a unique event ID."""
    return str(uuid.uuid4())


def get_gpu_usage():
    try:
        pynvml.nvmlInit()
        handle = pynvml.nvmlDeviceGetHandleByIndex(0)
        util = pynvml.nvmlDeviceGetUtilizationRates(handle)
        pynvml.nvmlShutdown()
        return util.gpu
    except:
        return 0.0


def get_machine_metrics() -> Dict[str, Any]:
    """Get comprehensive machine metrics."""
    try:
        gpu_usage = get_gpu_usage()

        metrics = {
            "hostname": platform.node(),
            "os": f"{platform.system()} {platform.release()}",
            "cpu_model": psutil.cpu_freq().current if psutil.cpu_freq() else 0,  # MHz
            "cpu_count": psutil.cpu_count(),
            "ram_total": psutil.virtual_memory().total >> 30,  # GB
            "disk_total": psutil.disk_usage("/").total >> 30,  # GB
        }

        if gpu_usage is not None:
            metrics["gpu_usage_percent"] = gpu_usage

        return metrics

    except Exception as e:
        logger.warning(f"Failed to get machine metrics: {e}")
        return {
            "hostname": "unknown",
            "os": "unknown",
            "cpu_model": 0,
            "ram_total": 0,
        }


def track_resources(session_data: Dict, interval: int = 10):
    """Track system resources in a separate thread."""
    while not getattr(threading.current_thread(), "stop", False):
        try:
            cpu_usage = psutil.cpu_percent()
            ram_usage = psutil.virtual_memory().percent
            disk_usage = psutil.disk_usage("/").percent
            gpu_usage = get_gpu_usage()

            resource_metrics = {
                "time": time.time(),
                "cpu_usage_percent": cpu_usage,
                "ram_usage_percent": ram_usage,
                "disk_usage_percent": disk_usage,
            }

            if gpu_usage is not None:
                resource_metrics["gpu_usage_percent"] = gpu_usage

            session_data["machine_metrics"].setdefault("resource_usage", []).append(resource_metrics)

            # OPTIONAL: emit periodic resource events (kept off by default to reduce noise)
            # log_event(session_data, "resource_sample", actor="system", payload=resource_metrics)

            time.sleep(interval)

        except Exception as e:
            logger.error(f"Error tracking resources: {e}")
            time.sleep(interval)


# -------------------------
# HAIC event logging
# -------------------------
def _ensure_event_structures(session_data: Dict):
    """Ensure required event structures exist in session_data."""
    session_data.setdefault("events", [])
    session_data.setdefault("event_seq", 0)

    # Where we write event streams (JSONL) per run
    if "run_metadata" in session_data:
        run_id = session_data["run_metadata"]["run_id"]
        session_data.setdefault("events_file", str(LOG_DIR / f"run_{run_id}.jsonl"))


def _append_event_to_jsonl(session_data: Dict, event: Dict):
    """Append an event to the run JSONL file."""
    events_file = session_data.get("events_file")
    if not events_file:
        return
    try:
        p = Path(events_file)
        p.parent.mkdir(parents=True, exist_ok=True)
        with open(p, "a", encoding="utf-8") as f:
            f.write(json.dumps(event, default=str) + "\n")
    except Exception as e:
        logger.error(f"Failed to append event to JSONL: {e}")


def log_event(
    session_data: Dict,
    event_type: str,
    actor: str = "system",
    payload: Optional[Dict[str, Any]] = None,
    context_overrides: Optional[Dict[str, Any]] = None,
    t: Optional[float] = None,
):
    """
    Pilot-agnostic event logger.

    Common envelope:
      - event_id, event_type, t, seq, actor
      - context: run_id, session_id, pilot_tag, app_version, model_version
      - payload: event-specific data
    """
    try:
        _ensure_event_structures(session_data)
        payload = payload or {}
        context_overrides = context_overrides or {}
        t = t if t is not None else time.time()

        session_data["event_seq"] += 1
        seq = session_data["event_seq"]

        rm = session_data.get("run_metadata", {})
        context = {
            "run_id": rm.get("run_id"),
            "session_id": session_data.get("session_id"),
            "pilot_tag": rm.get("pilot_tag", DEFAULT_PILOT_TAG),
            "app_version": rm.get("application", {}).get("version", DEFAULT_APP_VERSION),
            "app_mode": rm.get("application", {}).get("mode"),
            "model_name": rm.get("ai_system", {}).get("model_name"),
            "model_version": rm.get("ai_system", {}).get("model_version"),
        }
        context.update(context_overrides)

        event = {
            "event_id": get_event_id(),
            "event_type": event_type,
            "t": t,
            "seq": seq,
            "actor": actor,  # "human" | "ai" | "system"
            "context": context,
            "payload": payload,
        }

        session_data["events"].append(event)
        _append_event_to_jsonl(session_data, event)

    except Exception as e:
        logger.error(f"Failed to log event {event_type}: {e}")


def start_session_tracking(
    radiologist_id: Optional[str] = None,
    pilot_tag: str = DEFAULT_PILOT_TAG,
    app_mode: Optional[str] = None,
    model_name: str = "baseline_detector",
    model_type: str = "vision-detector",
    model_version: str = "v0",
    inference_config: Optional[Dict[str, Any]] = None,
    dataset: str = "ChestXray14",
) -> Dict:
    """
    Start tracking a new annotation session.

    Phase B: creates run_metadata and emits session_start event.
    """
    try:
        session_id = get_session_id()
        run_id = get_run_id()
        machine_metrics = get_machine_metrics()

        inference_config = inference_config or {}

        run_metadata = {
            "schema_version": HAIC_SCHEMA_VERSION,
            "run_id": run_id,
            "session_id": session_id,
            "pilot_tag": pilot_tag,
            "application": {
                "name": DEFAULT_APP_NAME,
                "version": DEFAULT_APP_VERSION,
                "mode": app_mode,  # labelling|feedback|active_learning (set by caller)
            },
            "ai_system": {
                "model_name": model_name,
                "model_type": model_type,
                "model_version": model_version,
                "inference_config": inference_config,
            },
            "task": {
                "name": "bbox_annotation",
                "domain": "radiology",
                "dataset": dataset,
                "unit_of_work": "image",
            },
            "human": {
                "actor_id": radiologist_id,
                "role": "radiologist",
                "expertise": "unknown",
            },
            "infrastructure": machine_metrics,
            "timestamps": {
                "start_time": time.time(),
                "end_time": None,
            },
        }

        session_data = {
            "session_id": session_id,
            "run_metadata": run_metadata,
            "session_start_time": run_metadata["timestamps"]["start_time"],
            "radiologist_id": radiologist_id,
            "machine_metrics": machine_metrics,
            "images": [],       # legacy / backward compatible
            "events": [],       # Phase B
            "event_seq": 0,     # Phase B
            "events_file": str(LOG_DIR / f"run_{run_id}.jsonl"),
        }

        # Start database session (summary-level persistence)
        db = get_database()
        db.start_session(session_id, radiologist_id, machine_metrics)

        # Start resource tracking thread
        metrics_thread = threading.Thread(target=track_resources, args=(session_data,))
        metrics_thread.daemon = True
        metrics_thread.start()
        session_data["_metrics_thread"] = metrics_thread

        logger.info(f"Started session tracking: {session_id}")

        # Phase B: emit session_start
        log_event(
            session_data,
            event_type="session_start",
            actor="system",
            payload={
                "radiologist_id": radiologist_id,
                "pilot_tag": pilot_tag,
                "app_mode": app_mode,
            },
        )

        return session_data

    except Exception as e:
        logger.error(f"Failed to start session tracking: {e}")
        raise


def log_image_data(
    session_data: Dict,
    image_id: str,
    load_time: Optional[float] = None,
    annotation_time: Optional[float] = None,
    feedback_time: Optional[float] = None,
    initial_predictions: Optional[list] = None,
    radiologist_decision: Optional[str] = None,
    modifications: Optional[list] = None,
    uncertainty_score: Optional[float] = None,
    radiologist_id: Optional[str] = None,
    selection_strategy: Optional[str] = None,  # e.g., "random" | "uncertainty"
):
    """
    Log data for a specific image interaction.

    Keeps legacy `images[]` plus emits Phase B events:
      - task_item_loaded (if load_time provided)
      - ai_suggestion_presented (if initial_predictions provided)
      - human_decision (if decision provided)
      - human_modification_saved (if modifications provided)
    """
    try:
        # ---- sanitize for DB (but keep rich data in JSON log) ----
        db_uncertainty = _to_float_or_none(uncertainty_score)
        db_decision = _to_str_or_none(radiologist_decision)
        db_load = _to_float_or_none(load_time)
        db_annot = _to_float_or_none(annotation_time)
        db_feedback = _to_float_or_none(feedback_time)

        rid = radiologist_id or session_data.get("radiologist_id")

        image_data = {
            "image_id": image_id,
            "load_time": load_time,
            "annotation_time": annotation_time,
            "feedback_time": feedback_time,
            "initial_predictions": initial_predictions or [],
            "radiologist_decision": radiologist_decision,
            "modifications": modifications or [],
            "uncertainty_score": uncertainty_score,
            "selection_strategy": selection_strategy,
            "save_time": time.time(),
            "radiologist_id": rid,
        }
        session_data["images"].append(image_data)

        # ---- Phase B: emit events (lightweight, idempotent-ish) ----
        if load_time is not None:
            log_event(
                session_data,
                event_type="task_item_loaded",
                actor="system",
                payload={
                    "task_item_id": image_id,
                    "unit": "image",
                    "load_time_s": db_load,
                    "selection_strategy": selection_strategy,
                },
            )

        if initial_predictions:
            log_event(
                session_data,
                event_type="ai_suggestion_presented",
                actor="ai",
                payload={
                    "task_item_id": image_id,
                    "initial_predictions": initial_predictions,
                    "uncertainty_score": db_uncertainty,
                },
            )

        if radiologist_decision is not None:
            log_event(
                session_data,
                event_type="human_decision",
                actor="human",
                payload={
                    "task_item_id": image_id,
                    "decision": db_decision,
                    "feedback_time_s": db_feedback,
                    "radiologist_id": rid,
                },
            )

        if modifications:
            log_event(
                session_data,
                event_type="human_modification_saved",
                actor="human",
                payload={
                    "task_item_id": image_id,
                    "modifications": modifications,
                    "annotation_time_s": db_annot,
                    "radiologist_id": rid,
                },
            )

        # ---- DB summary logging (scalars only) ----
        db = get_database()
        db.log_image_interaction(
            session_id=session_data["session_id"],
            image_path=image_id,
            load_time=db_load,
            annotation_time=db_annot,
            feedback_time=db_feedback,
            decision=db_decision,
            uncertainty_score=db_uncertainty,
        )

        logger.debug(f"Logged image data for: {image_id}")

    except Exception as e:
        logger.error(f"Failed to log image data: {e}")


def log_retraining(session_data: Dict, timestamp: float, num_images: int, model_update: Optional[Dict] = None):
    """Log retraining event."""
    try:
        if model_update is None:
            model_update = {
                "accuracy": 0.85,
                "f1_score": 0.80,
                "model_version": "unknown",
            }

        session_data["retraining"] = {
            "timestamp": timestamp,
            "num_images": num_images,
            "model_update": model_update,
        }

        # Phase B events
        log_event(
            session_data,
            event_type="retrain_end",
            actor="system",
            payload={
                "timestamp": timestamp,
                "num_images": num_images,
                "model_update": model_update,
            },
        )

        # DB logging
        db = get_database()
        db.log_retraining(
            num_images=num_images,
            accuracy=model_update.get("accuracy", 0),
            f1_score=model_update.get("f1_score", 0),
            model_version=model_update.get("model_version", "unknown"),
            duration=model_update.get("duration", 0),
            machine_specs=session_data.get("machine_metrics", {}),
            machine_usage=model_update.get("machine_usage", {}),
            success=model_update.get("success", True),
        )

        logger.info(f"Logged retraining event with {num_images} images")

    except Exception as e:
        logger.error(f"Failed to log retraining: {e}")


def end_session_tracking(session_data: Dict):
    """End session tracking and save data."""
    try:
        session_data["session_end_time"] = time.time()
        if "run_metadata" in session_data:
            session_data["run_metadata"]["timestamps"]["end_time"] = session_data["session_end_time"]

        # Phase B: emit session_end
        log_event(
            session_data,
            event_type="session_end",
            actor="system",
            payload={"session_end_time": session_data["session_end_time"]},
        )

        # Stop resource tracking thread
        metrics_thread = session_data.get("_metrics_thread")
        if metrics_thread and metrics_thread.is_alive():
            setattr(metrics_thread, "stop", True)
            metrics_thread.join(timeout=5)

        # Update database session
        db = get_database()
        db.end_session(session_data["session_id"])

        logger.info(f"Ended session tracking: {session_data['session_id']}")

    except Exception as e:
        logger.error(f"Failed to end session tracking: {e}")


def save_logs(session_data: Dict, filename: Optional[str] = None):
    """Save session logs (legacy function for backward compatibility)."""
    try:
        if filename is None:
            log_file = LOG_DIR / f"session_{session_data['session_id']}.json"
        else:
            log_file = Path(filename)

        log_file.parent.mkdir(parents=True, exist_ok=True)

        # JSON-safe copy
        safe = dict(session_data)
        safe.pop("_metrics_thread", None)

        def default(o):
            return str(o)

        with open(log_file, "w", encoding="utf-8") as f:
            json.dump(safe, f, indent=4, default=default)

        logger.info(f"Saved session logs to: {log_file}")

    except Exception as e:
        logger.error(f"Failed to save logs: {e}")

DECISION_SCHEMA_VERSION = "manufacturing.decisions.v1"  # keep name; reuse across pilots

def _ensure_decisions(session_data: Dict):
    session_data.setdefault("decisions", [])
    session_data.setdefault("decision_seq", 0)

def log_decision(
    session_data: Dict,
    actor_type: str,              # "ai" | "human" | "system"
    action: str,                  # controlled vocabulary
    object_id: str,               # image_id (XRAY)
    payload: Optional[Dict[str, Any]] = None,
    duration_s: Optional[float] = None,
    latency_ms: Optional[float] = None,
    correct: Optional[bool] = None,
    t: Optional[float] = None,
):
    """
    Append a manufacturing-style decision entry.

    This is the canonical structure we will import to HAIC:
      {t, actor_type, action, object_id, duration_s/latency_ms, payload, correct}
    """
    try:
        _ensure_decisions(session_data)
        payload = payload or {}
        t = t if t is not None else time.time()

        session_data["decision_seq"] += 1
        seq = session_data["decision_seq"]

        entry = {
            "schema_version": DECISION_SCHEMA_VERSION,
            "seq": seq,
            "t": t,
            "actor_type": actor_type,
            "action": action,
            "object_id": object_id,
            "duration_s": _to_float_or_none(duration_s),
            "latency_ms": _to_float_or_none(latency_ms),
            "correct": correct,
            "payload": payload,
        }

        session_data["decisions"].append(entry)

    except Exception as e:
        logger.error(f"Failed to log decision {action}: {e}")


def export_haic_decisions_artifact(session_data: Dict, filename: Optional[str] = None) -> Path:
    """
    Export a single JSON artifact in the Manufacturing-style contract:
      {session_id, meta, decisions[]}

    This is the file you upload to MinIO and register in HAIC.
    """
    run_md = session_data.get("run_metadata", {})
    run_id = run_md.get("run_id", session_data.get("session_id"))
    pilot_tag = run_md.get("pilot_tag", "radiology-toy")

    _ensure_decisions(session_data)

    artifact = {
        "schema_version": DECISION_SCHEMA_VERSION,
        "session_id": session_data.get("session_id"),
        "run_id": run_id,
        "meta": {
            "pilot_tag": pilot_tag,
            "application": run_md.get("application", {}),
            "ai_system": run_md.get("ai_system", {}),
            "task": run_md.get("task", {}),
            "human": run_md.get("human", {}),
            "infrastructure": session_data.get("machine_metrics"),
            "timestamps": run_md.get("timestamps", {}),
        },
        "decisions": session_data.get("decisions", []),
        # keep raw events too (optional, but handy for debugging)
        "events": session_data.get("events", []),
    }

    if filename is None:
        out = LOG_DIR / f"haic_decisions_{run_id}.json"
    else:
        out = Path(filename)

    out.parent.mkdir(parents=True, exist_ok=True)
    with open(out, "w", encoding="utf-8") as f:
        json.dump(artifact, f, indent=2, default=str)

    logger.info(f"Exported HAIC decisions artifact to: {out}")
    return out

def export_haic_artifact(session_data: Dict, filename: Optional[str] = None) -> Path:
    """
    Export a single HAIC-ready artifact JSON for import into the HAIC platform.

    Output includes:
      - run_metadata
      - events (ordered)
      - images (legacy / optional)
      - retraining (optional)
      - machine_metrics (optional)

    Returns the path of the exported artifact.
    """
    try:
        run_md = session_data.get("run_metadata", {})
        run_id = run_md.get("run_id") or "unknown_run"
        session_id = session_data.get("session_id")

        # Collect events:
        # Prefer in-memory session_data["events"], else read JSONL if present
        events = session_data.get("events")
        if not events:
            events = []
            events_file = session_data.get("events_file")
            if events_file and Path(events_file).exists():
                with open(events_file, "r", encoding="utf-8") as f:
                    for line in f:
                        line = line.strip()
                        if not line:
                            continue
                        try:
                            events.append(json.loads(line))
                        except Exception:
                            # tolerate partially written lines
                            continue

        # Build artifact
        artifact = {
            "artifact_schema": "haic.artifact.v1",
            "exported_at": time.time(),
            "run_id": run_id,
            "session_id": session_id,
            "pilot_tag": run_md.get("pilot_tag"),
            "run_metadata": run_md,
            "events": events,
            # keep backward-compat info (handy for debugging / legacy imports)
            "images": session_data.get("images", []),
            "retraining": session_data.get("retraining"),
            "machine_metrics": session_data.get("machine_metrics"),
        }

        # Choose output path
        if filename is None:
            out_path = LOG_DIR / f"haic_artifact_{run_id}.json"
        else:
            out_path = Path(filename)

        out_path.parent.mkdir(parents=True, exist_ok=True)

        # Make JSON-safe copy
        safe = dict(artifact)
        def default(o):
            return str(o)

        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(safe, f, indent=2, default=default)

        logger.info(f"Exported HAIC artifact to: {out_path}")
        return out_path

    except Exception as e:
        logger.error(f"Failed to export HAIC artifact: {e}")
        raise


def export_session_logs(output_dir: Path = LOG_DIR):
    """Export all session logs from database to JSON files."""
    try:
        db = get_database()
        logger.info("Session log export feature available - implement as needed")
    except Exception as e:
        logger.error(f"Failed to export session logs: {e}")