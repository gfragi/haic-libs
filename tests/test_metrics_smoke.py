from haic_metrics import compute_metrics

def test_core_profile_smoke():
    decisions = [
        {"actor_type": "human", "event_type": "label_received", "duration_s": 2.0, "timestamp": 1, "correct": True},
        {"actor_type": "ai", "event_type": "ai_evaluated", "latency_ms": 120, "timestamp": 2},
        {"actor_type": "human", "event_type": "label_received", "duration_s": 5.0, "timestamp": 3, "correct": False},
    ]
    out = compute_metrics(decisions, profile="core")
    assert "metrics" in out
    assert "F" in out["metrics"]  # from interaction KPIs

def test_full_profile_smoke():
    decisions = [
        {"prediction": "pos", "ground_truth": "pos", "actor_type": "ai", "event_type": "ai_evaluated", "latency_ms": 50, "timestamp": 1},
        {"prediction": "neg", "ground_truth": "pos", "actor_type": "ai", "event_type": "ai_evaluated", "latency_ms": 55, "timestamp": 2},
    ]
    out = compute_metrics(decisions, profile="full")
    assert "outcome_precision" in out["metrics"]
