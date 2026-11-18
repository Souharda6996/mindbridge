"""Phase 2 gate (part 2): the real pretrained models load and give sensible output.

Slow (loads ~800 MB of weights). Run with:
    .venv\\Scripts\\python.exe -m pytest backend\\tests\\test_models.py -m models -q
"""
import io
import wave

import numpy as np
import pytest

pytestmark = pytest.mark.models


@pytest.fixture(scope="module")
def loaded(monkeypatch_module=None):
    from backend.app import config
    from backend.app.services import models

    config.ENABLE_ML_MODELS = True
    models.load_all()
    assert models.STATUS["text"]["state"] == "ready", models.STATUS["text"]
    assert models.STATUS["text_multi"]["state"] == "ready", models.STATUS["text_multi"]
    assert models.STATUS["voice"]["state"] == "ready", models.STATUS["voice"]
    return models


@pytest.mark.parametrize("text,expected_group", [
    ("My grandmother passed away and I can't stop crying", "sadness"),
    ("I'm so scared about tomorrow's interview, I can't calm down", "fear"),
    ("I got placed at my dream company today!", "joy"),
    ("This is so unfair, I'm furious with my roommate", "anger"),
])
def test_text_emotion_groups(loaded, text, expected_group):
    out = loaded.analyze_text(text)
    assert out["engine"] == "roberta-go_emotions"
    top = max(out["emotions"], key=out["emotions"].get)
    assert top == expected_group, out


@pytest.mark.parametrize("text,expected", [
    ("मुझे बहुत गुस्सा आ रहा है", "anger"),
    ("मैं बहुत उदास हूँ", "sadness"),
    ("ನನಗೆ ಪರೀಕ್ಷೆಯ ಬಗ್ಗೆ ಭಯವಾಗುತ್ತಿದೆ", "fear"),
    ("aaj main bahut khush hoon yaar", "joy"),
])
def test_indian_language_emotion(loaded, text, expected):
    from backend.app.services import language
    out = loaded.analyze_text(text, language.detect(text))
    assert out["engine"].startswith("xlm-emo"), out
    assert out["dominant"] == expected, out


@pytest.mark.parametrize("text", ["हाँ", "ಹೌದು", "haan ji"])
def test_one_word_indic_reply_is_neutral(loaded, text):
    from backend.app.services import language
    assert loaded.analyze_text(text, language.detect(text))["dominant"] == "neutral"


def test_holdout_accuracy(loaded):
    import json
    from backend.app import config
    from backend.app.services import language
    cases = json.loads((config.BACKEND_DIR / "app" / "resources" / "emotion_holdout.json").read_text(encoding="utf-8"))
    correct = sum(loaded.analyze_text(c["text"], language.detect(c["text"]))["dominant"] == c["expected"] for c in cases)
    assert correct / len(cases) >= 0.85, f"{correct}/{len(cases)}"


def test_text_distress_ordering(loaded):
    sad = loaded.analyze_text("I feel completely alone and nothing I do matters")["distress"]
    happy = loaded.analyze_text("Today was wonderful, I'm grateful for my friends")["distress"]
    assert sad > happy + 0.3


def _wav(x):
    buf = io.BytesIO()
    with wave.open(buf, "wb") as w:
        w.setnchannels(1)
        w.setsampwidth(2)
        w.setframerate(16000)
        w.writeframes((np.clip(x, -1, 1) * 32767).astype(np.int16).tobytes())
    return buf.getvalue()


def test_voice_model_runs(loaded):
    t = np.arange(16000 * 3) / 16000
    x = 0.3 * np.sin(2 * np.pi * (160 + 40 * np.sin(2 * np.pi * 0.8 * t)) * t)
    x = np.concatenate([np.zeros(8000), x, np.zeros(8000)]) + 0.002 * np.random.default_rng(0).standard_normal(len(x) + 16000)
    out = loaded.analyze_voice(_wav(x), "testing the microphone")
    assert out["engine"] == "wav2vec2 + prosody"
    assert abs(sum(out["model"]["emotions"].values()) - 1.0) < 1e-3
    assert 0 <= out["distress"] <= 1 and out["reliability"] > 0
