from pathlib import Path

from haic_logging import HaicLogger
from haic_metrics import compute_metrics
from haic_metrics.io import load_decisions_artifact


def test_logging_to_metrics_roundtrip(tmp_path: Path):
    with HaicLogger(
        log_dir=tmp_path,
        pilot_tag="radiology-toy",
        app_name="annotation_tool",
        app_version="0.1.0",
        app_mode="labelling",
        model_name="baseline_detector",
        model_type="vision-detector",
        model_version="v0",
        enable_resource_tracking=False,
    ) as hl:
        hl.log_decision(actor_type="human", action="label_received", object_id="img_1", duration_s=2.0, correct=True)
        hl.log_decision(actor_type="ai", action="ai_evaluated", object_id="img_1", latency_ms=120, correct=None)
        out_path = hl.export_decisions_artifact()

    artifact = load_decisions_artifact(out_path)
    out = compute_metrics(artifact, profile="core")
    assert "metrics" in out
    assert isinstance(out["metrics"], dict)
