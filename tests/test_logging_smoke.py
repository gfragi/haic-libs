import time
from haic_metrics import compute_metrics

def test_minimal_decisions_artifact_compatible_with_metrics():
    now = time.time()

    artifact = {
        "meta": {
            "timestamps": {
                "start_time": now,
                "end_time": now + 20,
            }
        },
        "decisions": [
            {
                "t": now + 1,
                "actor_type": "human",
                "action": "accept",
                "duration_s": 2.0,
            },
            {
                "t": now + 5,
                "actor_type": "human",
                "action": "modify",
                "duration_s": 3.0,
            },
            {
                "t": now + 15,
                "actor_type": "ai",
                "action": "suggest",
                "duration_s": 0.2,
            },
        ]
    }

    result = compute_metrics(artifact)

    # Structural contract
    assert "metrics" in result
    assert "window_summary" in result

    # Metrics contract
    for k in ["F", "D", "HCL", "Tr", "A", "S", "EL", "EfficiencyScore"]:
        assert k in result["metrics"]

    # Default (no window) → all decisions used
    counts = result["window_summary"]["counts"]
    assert counts["decisions_used"] == 3
    assert counts["decisions_total"] == 3
