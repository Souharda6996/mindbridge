"""Phase 1 gate: crisis detector + escalation engine."""
import json

import pytest

from backend.app import config
from backend.app.services import crisis, escalation

CASES = json.loads(config.CASES_FILE.read_text(encoding="utf-8"))


@pytest.mark.parametrize("case", CASES, ids=[c["text"][:40] for c in CASES])
def test_case_tier(case):
    result = crisis.analyze(case["text"])
    assert result.tier == case["expected"], (
        f'{case["text"]!r} -> {result.tier} (expected {case["expected"]}); reasons={result.reasons}'
    )


def test_high_risk_recall_is_100_percent():
    high = [c for c in CASES if c["expected"] == "HIGH"]
    caught = [c for c in high if crisis.analyze(c["text"]).tier == "HIGH"]
    assert len(caught) == len(high)
    assert len(high) >= 30


def test_reasons_are_explainable():
    r = crisis.analyze("I have been saving up all my sleeping pills")
    assert r.level == 4
    assert r.reasons and r.reasons[0]["matched"]
    assert crisis.explain(r)[0].startswith("Stockpiling")


def test_idioms_are_reported():
    r = crisis.analyze("This exam is killing me")
    assert r.tier == "LOW"
    assert r.idioms_ignored


def test_timeframe_escalates_to_imminent():
    r = crisis.analyze("I want to kill myself tomorrow")
    assert r.level == 4
    assert any(x["category"] == "timeframe" for x in r.reasons)


def test_empty_text():
    assert crisis.analyze("").tier == "LOW"


# ---------------- escalation engine -----------------------------------------
def _risk(text):
    return crisis.analyze(text).to_dict()


def test_escalation_high_from_language():
    d = escalation.decide(_risk("I want to die"), None, elevated_streak=0)
    assert d.tier == "HIGH" and d.create_alert
    assert {"type": "crisis_card"} in d.actions


def test_escalation_distress_alone_never_high():
    fusion = {"smoothed": 0.95, "confidence": 0.9, "explanations": []}
    d = escalation.decide(_risk("I feel bad"), fusion, elevated_streak=5)
    assert d.tier == "MEDIUM"


def test_escalation_low_confidence_distress_ignored():
    fusion = {"smoothed": 0.95, "confidence": 0.1, "explanations": []}
    d = escalation.decide(_risk("hello"), fusion, elevated_streak=5)
    assert d.tier == "LOW"


def test_escalation_sustained_distress_medium_with_alert():
    fusion = {"smoothed": 0.7, "confidence": 0.8, "explanations": ["voice: long pauses"]}
    d = escalation.decide(_risk("I don't know"), fusion, elevated_streak=3)
    assert d.tier == "MEDIUM" and d.create_alert
    assert any("Sustained" in r for r in d.reasons)


def test_escalation_sticky_high():
    d = escalation.decide(_risk("ok thanks"), None, elevated_streak=0, session_peak="HIGH")
    assert d.tier == "HIGH"


def test_escalation_cross_session_trajectory():
    d = escalation.decide(_risk("hi"), None, elevated_streak=0, prior_sessions_high=2)
    assert d.tier == "MEDIUM"
