"""Spoken-language detection + speech-to-text (free, offline) - hybrid design.

Problem: the browser's Web Speech API must be TOLD which language to expect. If it
listens in English and the student speaks Hindi, it outputs English-looking
garbage and the companion replies in English.

Solution:
  1. Whisper-small (faster-whisper / CTranslate2, int8 CPU) DETECTS the spoken
     language from the audio (~2.5 s). Measured on test speech: English 0.99,
     Hindi 0.97-0.99, Kannada 0.99 (after grouping related languages - Whisper
     sometimes labels Kannada as Telugu/Sinhala and Hindi as Urdu).
  2. Transcript:
       * if the browser recogniser was already listening in that language -> use
         its transcript (Google's recogniser is excellent, incl. Kannada);
       * else English / Hindi -> Whisper transcribes (accurate for both);
       * else Kannada -> Whisper-small is unreliable for Kannada, so we switch the
         browser recogniser to Kannada and politely ask (in Kannada) to repeat.
  3. The detected language is returned so the browser listens in it next time.
"""
from __future__ import annotations

import threading
import time

import numpy as np

from .. import config

STATUS = {"state": "pending", "model": "whisper-small (int8)", "detail": ""}
_model = None
_lock = threading.Lock()

# Whisper language code -> MindBridge language (closely related languages grouped)
FAMILY = {"en": "en", "hi": "hi", "ur": "hi", "mr": "hi", "ne": "hi", "pa": "hi", "gu": "hi", "bn": "hi",
          "kn": "kn", "te": "kn", "ta": "kn", "ml": "kn", "si": "kn"}
LOCALE = {"en": "en-IN", "hi": "hi-IN", "kn": "kn-IN"}


def load() -> None:
    global _model
    if not config.ENABLE_ML_MODELS:
        STATUS.update(state="fallback", detail="models disabled by config")
        return
    path = config.MODELS_DIR / "whisper-small"
    if not (path / "model.bin").exists():
        STATUS.update(state="fallback", detail="whisper-small not downloaded (run setup.bat)")
        return
    STATUS["state"] = "loading"
    t0 = time.time()
    try:
        from faster_whisper import WhisperModel

        _model = WhisperModel(str(path), device="cpu", compute_type="int8", cpu_threads=6)
        STATUS.update(state="ready", detail=f"loaded in {time.time() - t0:.1f}s")
    except Exception as exc:  # pragma: no cover
        STATUS.update(state="fallback", detail=f"{type(exc).__name__}: {exc}"[:300])


def available() -> bool:
    return _model is not None


def detect_language(audio: np.ndarray) -> tuple[str, float, dict[str, float]]:
    with _lock:
        _, _, all_probs = _model.detect_language(audio=audio.astype(np.float32), vad_filter=True)
    grouped: dict[str, float] = {}
    for code, p in all_probs:
        fam = FAMILY.get(code)
        if fam:
            grouped[fam] = grouped.get(fam, 0.0) + float(p)
    if not grouped:
        return "en", 0.0, {}
    total = sum(grouped.values())
    grouped = {k: v / total for k, v in grouped.items()}
    lang = max(grouped, key=grouped.get)
    return lang, grouped[lang], grouped


def whisper_transcribe(audio: np.ndarray, lang: str) -> tuple[str, bool]:
    """Returns (text, reliable). Repetition loops (high compression ratio) = unreliable."""
    with _lock:
        segments, _ = _model.transcribe(
            audio.astype(np.float32), language=lang, beam_size=1, vad_filter=True,
            condition_on_previous_text=False, no_repeat_ngram_size=3, temperature=0.0,
        )
        segs = list(segments)
    text = " ".join(s.text.strip() for s in segs).strip()
    reliable = bool(text) and all(s.compression_ratio < 2.2 for s in segs)
    return text, reliable


def recognize(audio: np.ndarray, mode: str = "auto", browser_text: str = "", browser_lang: str = "") -> dict:
    """mode: 'auto' | 'en' | 'hi' | 'kn'.  browser_lang: 'en' | 'hi' | 'kn' (what the browser listened in)."""
    t0 = time.time()
    probs: dict[str, float] = {}
    if _model is None:
        # Whisper unavailable (not downloaded / disabled): trust the browser transcript as before
        lang = mode if mode in LOCALE else (browser_lang if browser_lang in LOCALE else "en")
        return {"text": browser_text, "language": lang, "confidence": 0.0, "probs": {}, "source": "browser",
                "locale": LOCALE[lang], "needs_repeat": not browser_text, "seconds": 0.0}
    if mode in LOCALE:
        lang, conf = mode, 1.0
    elif _model is not None and len(audio) > 16000 * 0.6:
        lang, conf, probs = detect_language(audio)
        if conf < 0.5 and browser_text and browser_lang in LOCALE:
            lang, conf = browser_lang, conf      # unsure -> trust what the browser heard
    else:
        lang, conf = (browser_lang if browser_lang in LOCALE else "en"), 0.0

    text, source = "", "none"
    if browser_text and browser_lang == lang:
        text, source = browser_text, "browser"
    elif _model is not None and lang in ("en", "hi"):
        text, ok = whisper_transcribe(audio, lang)
        source = "whisper" if ok else "none"
        if not ok:
            text = ""
    if not text and browser_text and browser_lang == lang:
        text, source = browser_text, "browser"

    return {"text": text, "language": lang, "confidence": round(conf, 3), "probs": {k: round(v, 3) for k, v in probs.items()},
            "source": source, "locale": LOCALE[lang], "needs_repeat": not text, "seconds": round(time.time() - t0, 2)}


RETRY_MESSAGE = {
    "en": "Sorry, I didn't quite catch that. Could you say it once more?",
    "hi": "माफ़ कीजिए, ठीक से सुनाई नहीं दिया। क्या आप एक बार फिर कह सकते हैं?",
    "kn": "ನೀವು ಕನ್ನಡದಲ್ಲಿ ಮಾತನಾಡಿದಿರಿ ಎಂದು ಗೊತ್ತಾಯಿತು. ಈಗ ನಾನು ಕನ್ನಡದಲ್ಲಿ ಕೇಳುತ್ತಿದ್ದೇನೆ. ದಯವಿಟ್ಟು ಇನ್ನೊಮ್ಮೆ ಹೇಳುತ್ತೀರಾ?",
}
