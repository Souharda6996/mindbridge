"""Phase 2 gate (part 1): fusion maths + prosody features on synthetic audio."""
import io
import wave

import numpy as np
import pytest

from backend.app.services import fusion, prosody
from backend.app.services.fusion import Signal

SR = 16000


# ---------------------------------------------------------------- fusion ---
def test_weights_follow_reliability():
    sig = {
        "face": Signal(0.9, 1.0), "voice": Signal(0.9, 1.0), "text": Signal(0.1, 1.0),
    }
    good = fusion.fuse(sig)
    sig["face"] = Signal(0.9, 0.05)          # camera covered / dark
    dark = fusion.fuse(sig)
    assert dark["weights"]["face"] < good["weights"]["face"] / 5
    assert dark["fused"] < good["fused"]     # unreliable face pulls less
    assert dark["confidence"] < good["confidence"]


def test_missing_modality_handled():
    out = fusion.fuse({"face": None, "voice": None, "text": Signal(0.7, 0.9)})
    assert out["fused"] == pytest.approx(0.7)
    assert set(out["weights"]) == {"text"}


def test_no_signal_returns_zero_confidence():
    out = fusion.fuse({"face": None, "voice": None, "text": None})
    assert out["confidence"] == 0.0


def test_fused_is_weighted_average_and_bounded():
    out = fusion.fuse({"face": Signal(1.0, 1.0), "voice": Signal(0.0, 1.0), "text": Signal(0.5, 1.0)})
    expected = (0.7 * 1.0 + 0.8 * 0.0 + 1.0 * 0.5) / (0.7 + 0.8 + 1.0)
    assert out["fused"] == pytest.approx(expected, abs=1e-3)
    assert 0 <= out["fused"] <= 1


def test_smoothing_dampens_spikes():
    out = fusion.fuse({"text": Signal(1.0, 1.0)}, prev_smoothed=0.1)
    assert 0.1 < out["smoothed"] < 1.0


def test_old_signals_decay():
    fresh = fusion.fuse({"face": Signal(0.9, 1.0, age_s=0), "text": Signal(0.1, 1.0)})
    old = fusion.fuse({"face": Signal(0.9, 1.0, age_s=300), "text": Signal(0.1, 1.0)})
    assert old["weights"]["face"] < fresh["weights"]["face"]


def test_face_signal_from_browser_payload():
    s = fusion.face_signal({"probs": {"sad": 0.8, "neutral": 0.2}, "reliability": 0.9})
    assert s.distress > 0.6 and s.emotions["sadness"] > 0.7
    assert fusion.face_signal(None) is None


# --------------------------------------------------------------- prosody ---
def _wav_bytes(x: np.ndarray) -> bytes:
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(SR)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def _voice(seconds, f0_fn, amp=0.3, gaps=()):
    t = np.arange(int(seconds * SR)) / SR
    f0 = f0_fn(t)
    phase = 2 * np.pi * np.cumsum(f0) / SR
    x = amp * (np.sin(phase) + 0.5 * np.sin(2 * phase) + 0.25 * np.sin(3 * phase))
    for a, b in gaps:
        x[int(a * SR):int(b * SR)] = 0
    rng = np.random.default_rng(0)
    return (x + 0.002 * rng.standard_normal(len(x))).astype(np.float32)


def test_wav_roundtrip_and_resample():
    x = _voice(1.0, lambda t: np.full_like(t, 150.0))
    data = _wav_bytes(x)
    y, sr = prosody.read_wav(data)
    assert sr == SR and abs(len(y) - len(x)) <= 1


def test_expressive_vs_flat_paused_voice():
    lively = _voice(4.0, lambda t: 180 + 60 * np.sin(2 * np.pi * 0.7 * t), amp=0.4)
    flat = _voice(4.0, lambda t: np.full_like(t, 110.0), amp=0.05,
                  gaps=[(0.8, 1.6), (2.2, 3.1)])
    a = prosody.analyze(lively)
    b = prosody.analyze(flat)
    assert b["features"]["pause_ratio"] > a["features"]["pause_ratio"]
    assert b["features"]["pitch_std_semitones"] < a["features"]["pitch_std_semitones"]
    assert b["distress"] > a["distress"]
    assert b["explanations"], "distressed voice must be explained"


def test_pitch_estimate_close_to_truth():
    x = _voice(2.0, lambda t: np.full_like(t, 200.0))
    out = prosody.analyze(x)
    assert out["features"]["pitch_mean_hz"] == pytest.approx(200, rel=0.05)


def test_silence_has_no_reliability():
    out = prosody.analyze(np.zeros(SR * 2, dtype=np.float32))
    assert out["reliability"] <= 0.05
