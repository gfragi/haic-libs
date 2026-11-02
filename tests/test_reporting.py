from haic_metrics.reporting.templates import REPORT_MD_TEMPLATE
import time
from haic_metrics import compute_metrics
from haic_metrics.reporting.md import render_markdown_report


def test_report_template_exists():
    assert "Evaluation window" in REPORT_MD_TEMPLATE
    assert "Metrics summary" in REPORT_MD_TEMPLATE





def test_markdown_report_golden_structure():
    now = time.time()

    artifact = {
        "meta": {
            "timestamps": {
                "start_time": now,
                "end_time": now + 30,
            }
        },
        "decisions": [
            {"t": now + 1, "actor_type": "human", "action": "accept", "duration_s": 2.0},
            {"t": now + 5, "actor_type": "human", "action": "modify", "duration_s": 3.0},
            {"t": now + 15, "actor_type": "ai", "action": "suggest", "duration_s": 0.2},
        ],
    }

    result = compute_metrics(
        artifact,
        window={"basis": "relative", "start": 0, "end": 20},
    )

    md = render_markdown_report(
        result=result,
        artifact=artifact,
        artifact_path="dummy.json",
        version_metrics="0.1.1",
        version_logging="0.1.0",
    )

    # ---- Golden structure assertions ----

    # Header
    assert "# HAIC Evaluation Report" in md

    # Window disclosure (non-negotiable)
    assert "## Evaluation window" in md
    assert "basis:" in md.lower()
    assert "duration:" in md.lower()

    # Metrics section
    assert "## Metrics summary" in md
    assert "| Interaction | F" in md or "F (frequency)" in md

    # Diagnostics
    assert "## Diagnostics" in md
    assert "Warnings" in md

    # Reproducibility
    assert "## Reproducibility" in md
    assert "artifact:" in md.lower()
    assert "haic-metrics" in md.lower()

# ---- v0.3.0: report(rt_max_s=..., fmt=...), schema version line ----

import json

import pytest

import haic_metrics


def _write_artifact(tmp_path):
    t0 = 1_700_000_000
    artifact = {
        "artifact_schema": "haic.decisions_artifact.v1",
        "schema_version": "haic.decisions.v1",
        "run_id": "run-test",
        "session_id": "sess-test",
        "meta": {"pilot_tag": "unit", "ai_system": {"model_name": "toy-llm"}},
        "decisions": [
            {"timestamp": t0, "actor_type": "human", "action": "query", "duration_s": 20.0, "correct": True},
            {"timestamp": t0 + 5, "actor_type": "ai", "action": "respond", "latency_ms": 900, "correct": True},
            {"timestamp": t0 + 30, "actor_type": "human", "action": "query", "duration_s": 40.0, "correct": False},
            {"timestamp": t0 + 35, "actor_type": "ai", "action": "respond", "latency_ms": 1100, "correct": False},
        ],
    }
    path = tmp_path / "haic_decisions_test.json"
    path.write_text(json.dumps(artifact))
    return path


def test_markdown_report_states_schema_version_and_metadata(tmp_path):
    md = haic_metrics.report(_write_artifact(tmp_path))
    assert "decisions schema:** haic.decisions_artifact.v1 (schema_version: haic.decisions.v1)" in md
    assert "**run_id:** run-test" in md
    assert "**model:** toy-llm" in md


def test_report_rt_max_s_is_passed_through(tmp_path):
    path = _write_artifact(tmp_path)
    j60 = json.loads(haic_metrics.report(path, fmt="json"))
    j30 = json.loads(haic_metrics.report(path, fmt="json", rt_max_s=30.0))
    assert j60["parameters"]["rt_max_s"] == 60.0
    assert j30["parameters"]["rt_max_s"] == 30.0
    direct = haic_metrics.compute_metrics(haic_metrics.load_decisions_artifact(path), rt_max_s=30.0)
    assert j30["metrics"]["HCL"] == pytest.approx(direct["metrics"]["HCL"])
    assert j30["metrics"]["HCL"] != pytest.approx(j60["metrics"]["HCL"])
    assert "rt_max=30.0s" in haic_metrics.report(path, rt_max_s=30.0)


def test_json_report_structure(tmp_path):
    j = json.loads(haic_metrics.report(_write_artifact(tmp_path), fmt="json", profile="full"))
    assert j["run_id"] == "run-test"
    assert j["parameters"]["profile"] == "full"
    assert j["reproducibility"]["artifact_schema"] == "haic.decisions_artifact.v1"
    assert j["reproducibility"]["schema_version"] == "haic.decisions.v1"
    assert j["reproducibility"]["haic_metrics_version"] == haic_metrics.__version__
    assert j["metrics"]["Tr"] == pytest.approx(0.5)
    assert j["metrics"]["outcome_f1"] is None
    assert isinstance(j["warnings"], list)


def test_report_rejects_unknown_fmt(tmp_path):
    with pytest.raises(ValueError):
        haic_metrics.report(_write_artifact(tmp_path), fmt="html")


def test_version_fallback_when_not_installed(monkeypatch):
    import importlib
    import importlib.metadata

    def _missing(name):
        raise importlib.metadata.PackageNotFoundError(name)

    monkeypatch.setattr(importlib.metadata, "version", _missing)
    try:
        assert importlib.reload(haic_metrics).__version__ == "unknown"
    finally:
        monkeypatch.undo()
        importlib.reload(haic_metrics)
    assert haic_metrics.__version__ not in ("unknown", "0.1.1")


def test_markdown_report_has_no_unrendered_template_markup(tmp_path):
    md = haic_metrics.report(_write_artifact(tmp_path))
    assert "{{" not in md and "}}" not in md
    warnings_section = md.split("### Warnings", 1)[1].split("## Reproducibility", 1)[0]
    assert "- EL not computed" in warnings_section
    assert "- - " not in md
    assert "- None" not in warnings_section


def test_markdown_report_renders_window_notes():
    result = {"metrics": {}, "window_summary": {"notes": ["start_time missing; used first decision"]}, "warnings": []}
    md = render_markdown_report(
        result=result, artifact={"decisions": []}, artifact_path="x.json",
        version_metrics="0.3.0", version_logging="0.1.0",
    )
    assert "**window notes**\n- start_time missing; used first decision\n" in md
    assert md.split("### Warnings", 1)[1].split("## Reproducibility", 1)[0].strip() == "- None"
    assert "{{#" not in md and "{{/" not in md
