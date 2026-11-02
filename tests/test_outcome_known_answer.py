"""Known-answer tests for the extended (profile="full") outcome metrics.

Fixture: 10 AI decisions with prediction / ground_truth labels giving
TP = 4, FP = 1, FN = 2, TN = 3, and three decisions carrying a trust rating
(4, 3, 5 on a 5-point scale). Hand-computed values:

    accuracy  = (TP + TN) / N        = 7 / 10   = 0.7
    precision = TP / (TP + FP)       = 4 / 5    = 0.8
    recall    = TP / (TP + FN)       = 4 / 6
    F1        = 2PR / (P + R)        = 8 / 11
    agreement = matching labels / N  = 7 / 10   = 0.7
    trust     = 100 * (4+3+5) / 15   = 80.0

When the required fields are absent, every outcome metric must be None.
"""
import pytest

from haic_metrics import compute_metrics

T0 = 1_700_000_000
OUTCOME_KEYS = [
    "outcome_prediction_accuracy",
    "outcome_precision",
    "outcome_recall",
    "outcome_f1",
    "outcome_human_ai_agreement_rate",
    "outcome_trust_score",
]

# (prediction, ground_truth): 4 TP, 1 FP, 2 FN, 3 TN
PAIRS = [("pos", "pos")] * 4 + [("pos", "neg")] + [("neg", "pos")] * 2 + [("neg", "neg")] * 3
TRUST = {0: 4, 1: 3, 2: 5}


def _decision(i, **fields):
    d = {"actor_type": "ai", "event_type": "ai_evaluated", "timestamp": T0 + 5 * i, "latency_ms": 100}
    d.update(fields)
    return d


def _labeled(pairs=PAIRS, trust=TRUST):
    rows = []
    for i, (pred, gt) in enumerate(pairs):
        d = _decision(i, prediction=pred, ground_truth=gt)
        if i in trust:
            d.update(trust_rating=trust[i], trust_scale_maximum=5)
        rows.append(d)
    return rows


def _full(decisions):
    return compute_metrics(decisions, profile="full")


# --- required fields present -------------------------------------------------

def test_accuracy_known_answer():
    assert _full(_labeled())["metrics"]["outcome_prediction_accuracy"] == pytest.approx(0.7)


def test_precision_known_answer():
    assert _full(_labeled())["metrics"]["outcome_precision"] == pytest.approx(0.8)


def test_recall_known_answer():
    assert _full(_labeled())["metrics"]["outcome_recall"] == pytest.approx(4 / 6)


def test_f1_known_answer():
    assert _full(_labeled())["metrics"]["outcome_f1"] == pytest.approx(8 / 11)


def test_agreement_known_answer():
    assert _full(_labeled())["metrics"]["outcome_human_ai_agreement_rate"] == pytest.approx(0.7)


def test_trust_score_known_answer():
    assert _full(_labeled())["metrics"]["outcome_trust_score"] == pytest.approx(80.0)


def test_unlabeled_decisions_do_not_dilute_accuracy():
    # 5 extra decisions without labels: accuracy is over the 10 labeled ones only
    rows = _labeled() + [_decision(100 + i) for i in range(5)]
    m = _full(rows)["metrics"]
    assert m["outcome_prediction_accuracy"] == pytest.approx(0.7)
    assert m["outcome_human_ai_agreement_rate"] == pytest.approx(0.7)


def test_f1_zero_when_precision_and_recall_zero():
    # TP = 0, FP = 1, FN = 1 -> P = R = 0 -> F1 = 0.0 (defined, not None)
    m = _full(_labeled(pairs=[("pos", "neg"), ("neg", "pos")], trust={}))["metrics"]
    assert m["outcome_precision"] == 0.0
    assert m["outcome_recall"] == 0.0
    assert m["outcome_f1"] == 0.0


# --- required fields absent --------------------------------------------------

def test_all_outcome_metrics_none_without_fields():
    rows = [_decision(i) for i in range(10)]
    out = _full(rows)
    for k in OUTCOME_KEYS:
        assert out["metrics"][k] is None, k
    assert any("Outcome metrics not computed" in w for w in out["warnings"])


def test_correct_alone_does_not_produce_outcome_metrics():
    # `correct` feeds Tr (core), not the prediction/ground-truth catalogue
    rows = [_decision(i, correct=(i % 2 == 0)) for i in range(10)]
    m = _full(rows)["metrics"]
    for k in OUTCOME_KEYS:
        assert m[k] is None, k
    assert m["Tr"] == pytest.approx(0.5)


def test_trust_score_none_without_ratings():
    m = _full(_labeled(trust={}))["metrics"]
    assert m["outcome_trust_score"] is None
    assert m["outcome_prediction_accuracy"] == pytest.approx(0.7)


def test_precision_recall_f1_none_when_undefined():
    # only true negatives: accuracy and agreement defined, P / R / F1 undefined
    m = _full(_labeled(pairs=[("neg", "neg")] * 4, trust={}))["metrics"]
    assert m["outcome_prediction_accuracy"] == pytest.approx(1.0)
    assert m["outcome_human_ai_agreement_rate"] == pytest.approx(1.0)
    assert m["outcome_precision"] is None
    assert m["outcome_recall"] is None
    assert m["outcome_f1"] is None


def test_outcome_metrics_absent_from_core_profile():
    m = compute_metrics(_labeled(), profile="core")["metrics"]
    assert not any(k in m for k in OUTCOME_KEYS)
