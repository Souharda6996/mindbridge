"""Spoken-language detection with real Whisper on real speech clips (English, Hindi, Kannada).

Run:  pytest backend\\tests\\test_speech.py -m models
Clips live in backend/tests/audio (generated once with edge-tts); tests skip if they are absent.
"""
import io
import wave
from pathlib import Path

import numpy as np
import pytest

pytestmark = pytest.mark.models
AUDIO = Path(__file__).parent / "audio"


@pytest.fixture(scope="module")
def stt_ready():
    from backend.app import config
    from backend.app.services import stt

    config.ENABLE_ML_MODELS = True
    stt.load()
    if not stt.available():
        pytest.skip("whisper not available")
    return stt


def _clip(name):
    if not (AUDIO / name).exists():
        pytest.skip(f"{name} missing")
    from backend.tests.audio_utils import load_audio
    return load_audio(str(AUDIO / name))


@pytest.mark.parametrize("clip,expected", [("en_low.mp3", "en"), ("hi_angry.mp3", "hi"), ("hi_howareyou.mp3", "hi"), ("kn_sad.mp3", "kn")])
def test_language_detected(stt_ready, clip, expected):
    lang, conf, _ = stt_ready.detect_language(_clip(clip))
    assert lang == expected and conf > 0.5


def test_hindi_speech_is_transcribed_in_devanagari(stt_ready):
    out = stt_ready.recognize(_clip("hi_angry.mp3"))
    assert out["language"] == "hi" and any("ऀ" <= ch <= "ॿ" for ch in out["text"])


def test_kannada_without_browser_text_asks_to_repeat(stt_ready):
    out = stt_ready.recognize(_clip("kn_sad.mp3"))
    assert out["language"] == "kn" and out["needs_repeat"] and out["locale"] == "kn-IN"


def test_kannada_with_browser_text_is_used(stt_ready):
    out = stt_ready.recognize(_clip("kn_sad.mp3"), browser_text="ನನಗೆ ಬೇಸರವಾಗಿದೆ", browser_lang="kn")
    assert out["text"] == "ನನಗೆ ಬೇಸರವಾಗಿದೆ" and out["source"] == "browser"


def test_voice_endpoint_replies_in_spoken_language(stt_ready):
    """Hindi speech + an English-listening browser (the bug) -> Hindi reply."""
    from fastapi.testclient import TestClient
    from backend.app import main

    audio = _clip("hi_angry.mp3")
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1); w.setsampwidth(2); w.setframerate(16000)
        w.writeframes((np.clip(audio, -1, 1) * 32767).astype(np.int16).tobytes())
    with TestClient(main.app) as c:
        sid = c.post("/api/session", json={"mode": "video"}).json()["session_id"]
        r = c.post("/api/voice", data={"session_id": sid, "transcript": "", "browser_locale": "en-IN", "lang_mode": "auto"},
                   files={"audio": ("v.wav", buf.getvalue(), "audio/wav")}).json()
    assert r["stt"]["language"] == "hi" and r["stt"]["locale"] == "hi-IN"
    assert any("ऀ" <= ch <= "ॿ" for ch in r["reply"]), r["reply"]
