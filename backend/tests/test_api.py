"""Phase 3 gate: the full HTTP pipeline (offline engine, models disabled)."""
import io
import wave

import numpy as np
import pytest
from fastapi.testclient import TestClient

from backend.app import main
from backend.app.services import conversation, offline_engine, safety_filter


@pytest.fixture(scope="module")
def client():
    with TestClient(main.app) as c:
        yield c


def _session(client, mode="text"):
    r = client.post("/api/session", json={"mode": mode})
    assert r.status_code == 200
    return r.json()["session_id"]


def test_health(client):
    r = client.get("/api/health").json()
    assert r["status"] == "ok"
    assert r["llm"]["offline"] is True
    assert any(h["number"] == "14416" for h in r["helplines"])


def test_demo_data_seeded(client):
    d = client.get("/api/dashboard").json()
    assert d["mood_series"], "demo history should exist on first run"
    assert d["kpis"]["avg_mood_7d"] is not None
    assert d["insights"]


def test_normal_turn_gets_supportive_reply(client):
    sid = _session(client)
    r = client.post("/api/chat", json={"session_id": sid, "text": "I'm really stressed about my exams next week"})
    body = r.json()
    assert r.status_code == 200
    assert body["tier"] == "LOW"
    assert body["provider"] == "offline-engine"
    assert len(body["reply"]) > 20
    assert body["fusion"]["weights"]["text"] == 1.0


def test_face_signal_changes_fusion(client):
    sid = _session(client, "video")
    face = {"probs": {"sad": 0.9, "neutral": 0.1}, "reliability": 0.95}
    r = client.post("/api/chat", json={"session_id": sid, "text": "I am okay I guess", "face": face}).json()
    assert set(r["fusion"]["weights"]) == {"text", "face"}
    live = client.post(f"/api/session/{sid}/face", json={"probs": {"happy": 1.0}, "reliability": 0.02}).json()
    assert live["fusion"]["weights"].get("face", 0) < 0.1     # unreliable face barely counts


def test_crisis_turn_triggers_protocol_and_alert(client):
    sid = _session(client)
    r = client.post("/api/chat", json={"session_id": sid, "text": "I don't want to live anymore"}).json()
    assert r["tier"] == "HIGH"
    assert r["provider"] == "crisis-protocol"
    assert "14416" in r["reply"]
    assert {"type": "crisis_card"} in r["actions"]
    assert r["alert_id"]
    alerts = client.get("/api/alerts").json()
    mine = [a for a in alerts if a["id"] == r["alert_id"]][0]
    assert mine["status"] == "new" and mine["reasons"]
    # session stays in safety mode until a counselor resolves it
    r2 = client.post("/api/chat", json={"session_id": sid, "text": "ok"}).json()
    assert r2["tier"] == "HIGH"
    client.post(f"/api/alerts/{r['alert_id']}", json={"status": "resolved", "note": "called student"})
    r3 = client.post("/api/chat", json={"session_id": sid, "text": "thanks for checking on me"}).json()
    assert r3["tier"] != "HIGH"


def test_hindi_crisis_reply_in_hinglish(client):
    sid = _session(client)
    r = client.post("/api/chat", json={"session_id": sid, "text": "main marna chahta hoon yaar"}).json()
    assert r["tier"] == "HIGH" and "14416" in r["reply"] and r["language"] == "hinglish"


def test_trusted_contact_and_counselor_request(client):
    sid = _session(client)
    n = client.post("/api/trusted-contact/notify", json={"session_id": sid}).json()
    assert n["ok"] and "No conversation details" in n["message"]
    c = client.post("/api/counselor/request", json={"session_id": sid}).json()
    assert c["ok"] and c["alert_id"]


def _wav(seconds=2.0):
    t = np.arange(int(16000 * seconds)) / 16000
    x = 0.3 * np.sin(2 * np.pi * (150 + 30 * np.sin(2 * np.pi * t)) * t)
    pad = np.zeros(int(16000 * 0.5))
    x = np.concatenate([pad, x, pad]) + 0.002 * np.random.default_rng(1).standard_normal(len(x) + 2 * len(pad))
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes((x * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def test_voice_turn(client):
    sid = _session(client, "video")
    r = client.post("/api/voice", data={"session_id": sid, "transcript": "I have been feeling low lately"},
                    files={"audio": ("clip.wav", _wav(), "audio/wav")})
    body = r.json()
    assert r.status_code == 200, body
    assert body["voice"]["engine"] in {"prosody-only", "wav2vec2 + prosody"}
    assert "voice" in body["fusion"]["weights"]


def test_checkin_and_journal_risk(client):
    r = client.post("/api/checkins", json={"mood": 7, "sleep_hours": 7.5, "energy": 6, "anxiety": 3,
                                           "tags": ["friends"], "note": "Good day with friends"}).json()
    assert r["risk"]["tier"] == "LOW"
    rows = client.get("/api/checkins").json()
    assert rows[0]["note"] == "Good day with friends"     # decrypted correctly
    r2 = client.post("/api/checkins", json={"mood": 2, "note": "I wish I was dead", "day": "2020-01-01"}).json()
    assert r2["risk"]["tier"] == "HIGH" and r2["alert_id"]


def test_fusion_simulator(client):
    good = client.post("/api/fusion/simulate", json={"face": {"distress": 0.9, "reliability": 1},
                                                     "text": {"distress": 0.2, "reliability": 1}}).json()
    dark = client.post("/api/fusion/simulate", json={"face": {"distress": 0.9, "reliability": 0.05},
                                                     "text": {"distress": 0.2, "reliability": 1}}).json()
    assert dark["weights"]["face"] < good["weights"]["face"]


def test_risk_language_overrides_surface_sentiment(client):
    r = client.post("/api/analyze/text", json={"text": "everyone would be better off without me"}).json()
    assert r["risk"]["tier"] == "HIGH"
    assert r["emotion"]["distress"] >= 0.7
    assert max(r["emotion"]["emotions"], key=r["emotion"]["emotions"].get) == "sadness"


def test_live_evaluation_endpoint(client):
    e = client.get("/api/eval").json()
    assert e["crisis"]["high_recall"] == 1.0
    assert e["crisis"]["accuracy"] == 1.0
    assert e["safety_filter"]["correct"] == e["safety_filter"]["total"]


def test_settings_roundtrip(client):
    client.put("/api/settings/profile", json={"name": "Meera"})
    assert client.get("/api/settings").json()["profile"]["name"] == "Meera"


def test_report(client):
    r = client.get("/api/report").json()
    assert "disclaimer" in r and r["dashboard"]["kpis"]


def test_delete_all_data(client):
    r = client.delete("/api/data").json()
    assert r["ok"]
    assert client.get("/api/alerts").json() == []
    assert client.get("/api/checkins").json() == []


# ------------------------------------------------- unit: offline + safety ---
def test_offline_engine_offers_breathing_for_panic():
    out = offline_engine.respond("my heart is racing and I can't breathe", "fear", 0.7, "LOW", {})
    assert out["exercise"] == "box_breathing"


def test_offline_engine_reflects_feeling():
    out = offline_engine.respond("I feel so left out in my hostel", "sadness", 0.5, "LOW", {})
    assert "left out" in out["reply"]


def test_offline_engine_medium_offers_counselor():
    out = offline_engine.respond("everything is too much", "sadness", 0.7, "MEDIUM", {})
    assert "counsellor" in out["reply"]


def test_safety_filter_blocks_medication_and_diagnosis():
    assert safety_filter.check("You probably have depression")[1]
    assert safety_filter.check("Take 20 mg of escitalopram")[1]
    assert not safety_filter.check("That sounds hard. Want to tell me more?")[1]


def test_language_detection():
    assert conversation.detect_language("मैं ठीक नहीं हूँ") == "hi"
    assert conversation.detect_language("ನಾನು ಚೆನ್ನಾಗಿಲ್ಲ") == "kn"
    assert conversation.detect_language("yaar mujhe kuch accha nahi lag raha") == "hinglish"
    assert conversation.detect_language("I am fine") == "en"
