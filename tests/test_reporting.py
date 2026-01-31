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