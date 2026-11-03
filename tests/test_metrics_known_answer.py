"""Known-answer tests for the core HAIC interaction metrics.

Each expected value is computed by hand from the fixture below, so these tests
check the metric definitions themselves, not only that computation runs.

Fixture: 10 turns, each a human query followed by an AI response
(20 decisions). Decisions are 5 s apart (session span T = 95 s).
Human duration_s alternates 4, 6 (mean 5 s); AI latency_ms = 1000 (1 s).
Turn-level acceptance labels are applied to both decisions of a turn,
as in the derive_correct mapping used in the paper.
"""
import math

import pytest

from haic_metrics import compute_metrics

T0 = 1_700_000_000
TURN_LABELS = [True, False, True, True, False, True, True, False, True, True]


def _fixture(labels=TURN_LABELS, extra=None):
    rows = []
    for turn, ok in enumerate(labels):
        h = {
            "actor_type": "human",
            "event_type": "query",
            "timestamp": T0 + 10 * turn,
            "duration_s": 4.0 if turn % 2 == 0 else 6.0,
        }
        a = {
            "actor_type": "ai",
            "event_type": "response",
            "timestamp": T0 + 10 * turn + 5,
            "latency_ms": 1000,
        }
        if ok is not None:
            h["correct"] = ok
            a["correct"] = ok
        if extra:
            h.update(extra(turn, "human"))
            a.update(extra(turn, "ai"))
        rows += [h, a]
    return rows


def _m(decisions, **kw):
    return compute_metrics(decisions, profile="core", **kw)


def test_frequency_duration_hcl():
    m = _m(_fixture(), rt_max_s=20.0, baseline_s=50.0)["metrics"]
    # F = N / (T/60) = 20 / (95/60)
    assert m["F"] == pytest.approx(20 / (95 / 60))
    # D = mean over all agent rows = (5*4 + 5*6 + 10*1) / 20
    assert m["D"] == pytest.approx(3.0)
    # HCL = clip(1 - mean_human_rt / rt_max) = 1 - 5/20
    assert m["HCL"] == pytest.approx(0.75)


def test_trust_proxy():
    m = _m(_fixture(), baseline_s=50.0)["metrics"]
    # 20 labeled rows, 6 rejections (3 rejected turns x 2 rows) -> 1 - 6/20
    assert m["Tr"] == pytest.approx(0.7)


def test_adaptability():
    m = _m(_fixture(), baseline_s=50.0)["metrics"]
    # k = int(0.2 * 20) = 4 rows -> early = turns 0-1 (acc 0.5), late = turns 8-9 (acc 1.0)
    # A = tanh((1.0 - 0.5) / 0.5) = tanh(1)
    assert m["A"] == pytest.approx(math.tanh(1.0))


def test_effort_loss_and_efficiency_score():
    m = _m(_fixture(), baseline_s=50.0)["metrics"]
    # EL = max(0, (T - T_base) / T_base) = (95 - 50) / 50
    assert m["EL"] == pytest.approx(0.9)
    # EfficiencyScore = 1 / (1 + EL), no off-role or progress events
    assert m["EfficiencyScore"] == pytest.approx(1 / 1.9)


def test_effort_loss_clamped_at_zero():
    m = _m(_fixture(), baseline_s=200.0)["metrics"]
    assert m["EL"] == 0.0
    assert m["EfficiencyScore"] == pytest.approx(1.0)


def test_effort_loss_requires_explicit_baseline():
    out = _m(_fixture())
    assert out["metrics"]["EL"] is None
    assert out["metrics"]["EfficiencyScore"] is None
    assert any("baseline" in w for w in out["warnings"])


def test_unlabeled_session_returns_none_not_default():
    m = _m(_fixture(labels=[None] * 10), baseline_s=50.0)["metrics"]
    assert m["Tr"] is None
    assert m["A"] is None
    assert "Tr_note" in m and "A_note" in m


def test_adaptability_undefined_when_early_acceptance_zero():
    labels = [False, False] + [True] * 8
    m = _m(_fixture(labels=labels), baseline_s=50.0)["metrics"]
    assert m["A"] is None


def test_similarity_none_without_surrogate_data():
    m = _m(_fixture(), baseline_s=50.0)["metrics"]
    assert m["S"] is None
    assert "S_note" in m


def test_similarity_action_agreement():
    # surrogate disagrees on 3 rows: turn 7 (human and ai) and turn 8 (human)
    mismatches = {(7, "human"), (7, "ai"), (8, "human")}

    def extra(turn, actor):
        action = "query" if actor == "human" else "response"
        return {"action": action,
                "surrogate_action": "other" if (turn, actor) in mismatches else action}

    m = _m(_fixture(extra=extra), baseline_s=50.0)["metrics"]
    # S = agreements / compared = 17 / 20
    assert m["S"] == pytest.approx(17 / 20)


def test_similarity_kl_identical_distributions():
    dist = {"accept": 0.7, "reject": 0.3}

    def extra(turn, actor):
        return {"probs": dist, "surrogate_probs": dist}

    m = _m(_fixture(extra=extra), baseline_s=50.0)["metrics"]
    # S = exp(-KL(P||P)) = 1
    assert m["S"] == pytest.approx(1.0)


def test_similarity_kl_known_value():
    p = {"accept": 0.5, "reject": 0.5}
    q = {"accept": 0.8, "reject": 0.2}

    def extra(turn, actor):
        return {"probs": p, "surrogate_probs": q}

    m = _m(_fixture(extra=extra), baseline_s=50.0)["metrics"]
    kl = 0.5 * math.log(0.5 / 0.8) + 0.5 * math.log(0.5 / 0.2)
    assert m["S"] == pytest.approx(math.exp(-kl))


def test_human_row_without_timing_does_not_crash():
    # haic-logging writes latency_ms=None when no latency is given; a human
    # decision with neither duration_s nor latency_ms must be skipped for HCL,
    # not raise TypeError (defect reported by a cross-domain study team).
    rows = _fixture()
    rows.append({"actor_type": "human", "event_type": "feedback",
                 "timestamp": T0 + 96, "duration_s": None, "latency_ms": None})
    m = _m(rows, rt_max_s=20.0, baseline_s=50.0)["metrics"]
    assert m["HCL"] == pytest.approx(0.75)


def test_hcl_none_without_human_timing():
    # No human row carries timing: HCL is not computable and must not fall
    # back to AI latencies (0.3.0 used them and reported 0.95 here).
    rows = _fixture()
    for r in rows:
        if r["actor_type"] == "human":
            r["duration_s"] = None
    m = _m(rows, rt_max_s=20.0, baseline_s=50.0)["metrics"]
    assert m["HCL"] is None
    assert "HCL not computable" in m["HCL_note"]
    assert m["Tr"] is not None  # other metrics are unaffected


def test_hcl_none_without_human_rows():
    rows = [r for r in _fixture() if r["actor_type"] == "ai"]
    m = _m(rows, rt_max_s=20.0, baseline_s=50.0)["metrics"]
    assert m["HCL"] is None


def test_hcl_zero_human_duration_is_timing():
    # duration_s = 0.0 is a logged (if implausible) timing, not missing timing
    rows = _fixture()
    for r in rows:
        if r["actor_type"] == "human":
            r["duration_s"] = 0.0
    m = _m(rows, rt_max_s=20.0, baseline_s=50.0)["metrics"]
    assert m["HCL"] == pytest.approx(1.0)
    assert "HCL_note" not in m
