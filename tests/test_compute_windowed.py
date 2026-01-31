from haic_metrics import compute_metrics

def test_compute_metrics_respects_window():
    artifact = {
        "meta": {"timestamps": {"start_time": 0.0}},
        "decisions": [
            {"t": 1.0, "actor_type": "human", "action": "accept", "duration_s": 2.0},
            {"t": 10.0, "actor_type": "human", "action": "modify", "duration_s": 3.0},
            {"t": 30.0, "actor_type": "human", "action": "accept", "duration_s": 1.0},
        ]
    }

    result = compute_metrics(
        artifact,
        window={"basis": "relative", "start": 0, "end": 15},
    )

    summary = result["window_summary"]
    metrics = result["metrics"]

    assert summary["counts"]["decisions_used"] == 2

    for k in ["F", "D", "HCL", "Tr", "A", "S", "EL", "EfficiencyScore"]:
        assert k in metrics

    assert metrics["F"] >= 0.0
    assert 0.0 <= metrics["HCL"] <= 1.0
    assert 0.0 <= metrics["EfficiencyScore"] <= 1.0


from haic_metrics import compute_metrics

def test_compute_metrics_window_changes_slice():
    artifact = {
        "meta": {"timestamps": {"start_time": 0.0}},
        "decisions": [
            {"t": 1.0, "actor_type": "human", "action": "accept", "duration_s": 2.0},
            {"t": 10.0, "actor_type": "human", "action": "modify", "duration_s": 3.0},
            {"t": 30.0, "actor_type": "human", "action": "accept", "duration_s": 1.0},
        ]
    }

    # Small window
    r_small = compute_metrics(
        artifact,
        window={"basis": "relative", "start": 0, "end": 15},
    )

    # Larger window
    r_large = compute_metrics(
        artifact,
        window={"basis": "relative", "start": 0, "end": 40},
    )

    assert r_small["window_summary"]["counts"]["decisions_used"] == 2
    assert r_large["window_summary"]["counts"]["decisions_used"] == 3

    # Sanity: metrics still exist
    for k in ["F", "D", "HCL", "Tr", "A", "S", "EL", "EfficiencyScore"]:
        assert k in r_small["metrics"]
        assert k in r_large["metrics"]