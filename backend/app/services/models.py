"""Pretrained open-source models (CPU) with graceful fallbacks.

* Text  : SamLowe/roberta-base-go_emotions  - RoBERTa fine-tuned on Google's
          GoEmotions (58k Reddit comments, 28 emotions, multi-label/sigmoid).
* Voice : superb/wav2vec2-base-superb-er    - wav2vec2 fine-tuned on IEMOCAP
          (4 emotions: neutral, happy, angry, sad).

Models load in a background thread at server start so the UI is usable
immediately. If a model cannot load (no download, low RAM) the system falls
back to a lexicon (text) or prosody-only analysis (voice) and lowers that
modality's reliability - the fusion engine then trusts it less. This is the
same reliability idea applied to the software itself.
"""
from __future__ import annotations

import re
import threading
import time

import numpy as np

from .. import config
from . import prosody, stt
from .fusion import COMMON, Signal, entropy_confidence

TEXT_DISTRESS = None  # v1 per-label weights removed; distress now computed per group (GROUP_DISTRESS)

STATUS: dict[str, dict] = {
    "text": {"state": "pending", "model": config.TEXT_MODEL_ID, "detail": ""},
    "text_multi": {"state": "pending", "model": config.TEXT_MULTI_MODEL_ID, "detail": ""},
    "voice": {"state": "pending", "model": config.VOICE_MODEL_ID, "detail": ""},
}
STATUS["speech"] = stt.STATUS   # same dict object - Whisper updates it directly
_text = {"tok": None, "model": None, "labels": None}
_multi = {"tok": None, "model": None, "labels": None}
_voice = {"fe": None, "model": None, "labels": None}
_lock = threading.Lock()

# ---------------- GoEmotions (28 labels) -> 6 shared groups -----------------
# v2 mapping. "approval" ("ok", "I agree"), "caring", "desire", "realization" and
# "curiosity" are NOT joy - counting them as joy made calm messages look happy.
# "confusion" ("I don't know what to do") is grouped with fear/anxiety.
TEXT_TO_COMMON = {
    "admiration": "joy", "amusement": "joy", "excitement": "joy", "gratitude": "joy", "joy": "joy",
    "love": "joy", "optimism": "joy", "pride": "joy", "relief": "joy",
    "approval": "neutral", "caring": "neutral", "desire": "neutral", "realization": "neutral",
    "curiosity": "neutral", "neutral": "neutral",
    "sadness": "sadness", "grief": "sadness", "disappointment": "sadness", "remorse": "sadness",
    "embarrassment": "sadness",
    "fear": "fear", "nervousness": "fear", "confusion": "fear",
    "anger": "anger", "annoyance": "anger", "disapproval": "anger", "disgust": "anger",
    "surprise": "surprise",
}
GROUP_DISTRESS = {"sadness": 0.85, "fear": 0.75, "anger": 0.55, "surprise": 0.2, "neutral": 0.12, "joy": 0.0}

# Indian-language emotion words (Hinglish, Devanagari Hindi, Kannada) used with XLM-EMO.
INDIC_LEXICON = {
    "anger": r"gussa|gusse|naraz|naraaz|irritate|chidh|chid gaya|pagal kar|गुस्सा|गुस्से|नाराज़|नाराज|चिढ़|ಕೋಪ|ಸಿಟ್ಟು",
    "sadness": r"(accha|acha|khush|theek) nahi|(अच्छा|खुश|ठीक) नहीं|ಚೆನ್ನಾಗಿಲ್ಲ|udaas|udas|dukhi|akela|akeli|yaad aa|rona|ro raha|ro rahi|toot|उदास|दुखी|अकेला|अकेली|याद आ|रोना|रो रहा|रो रही|ಬೇಸರ|ದುಃಖ|ಒಂಟಿ",
    "fear": r"darr|dar lag|ghabra|tension|pareshan|chinta|डर|घबराहट|घबरा|चिंता|परेशान|टेंशन|ಭಯ|ಆತಂಕ|ಚಿಂತೆ",
    "joy": r"khush|khushi|maza|mazaa|accha lag|acha lag|badhiya|खुश|खुशी|मज़ा|मजा|अच्छा लग|बढ़िया|ಖುಷಿ|ಸಂತೋಷ",
}
_NEG_AFTER = re.compile(r"^\W{0,2}\s*(\w+\s+){0,2}(nahi|nahin|nhi|नहीं|ಇಲ್ಲ)", re.I)
VOICE_LABELS = {"neu": "neutral", "hap": "joy", "ang": "anger", "sad": "sadness"}
VOICE_DISTRESS = {"sadness": 0.85, "anger": 0.55, "neutral": 0.12, "joy": 0.0}

# Small lexicon used only when the RoBERTa model is unavailable.
LEXICON = {
    "sadness": "sad|down|low|cry|crying|lonely|alone|empty|hopeless|miss|hurt|depressed|heartbroken|tired|exhausted|lost|udaas|dukhi|akela",
    "fear": "anxious|anxiety|scared|afraid|worried|nervous|panic|stress|stressed|tense|overthinking|tension|darr|ghabrahat",
    "anger": "angry|furious|annoyed|irritated|frustrated|hate|mad|gussa",
    "joy": "happy|glad|great|good|excited|grateful|thankful|calm|relaxed|better|proud|love|khush|accha",
}


def _load_text() -> None:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(config.TEXT_MODEL_ID)
    model = AutoModelForSequenceClassification.from_pretrained(config.TEXT_MODEL_ID)
    model.eval()
    _text.update(tok=tok, model=model, labels=[model.config.id2label[i] for i in range(model.config.num_labels)])


def _load_voice() -> None:
    from transformers import AutoFeatureExtractor, AutoModelForAudioClassification

    fe = AutoFeatureExtractor.from_pretrained(config.VOICE_MODEL_ID)
    model = AutoModelForAudioClassification.from_pretrained(config.VOICE_MODEL_ID)
    model.eval()
    _voice.update(fe=fe, model=model, labels=[model.config.id2label[i] for i in range(model.config.num_labels)])


def _load_multi() -> None:
    from transformers import AutoModelForSequenceClassification, AutoTokenizer

    tok = AutoTokenizer.from_pretrained(config.TEXT_MULTI_MODEL_ID)
    model = AutoModelForSequenceClassification.from_pretrained(config.TEXT_MULTI_MODEL_ID)
    model.eval()
    _multi.update(tok=tok, model=model, labels=[model.config.id2label[i].lower() for i in range(model.config.num_labels)])


def load_all() -> None:
    """Load all models (called once, in a background thread)."""
    if not config.ENABLE_ML_MODELS:
        for k in STATUS:
            STATUS[k].update(state="fallback", detail="models disabled by config")
        return
    try:
        import torch

        torch.set_num_threads(max(1, min(4, torch.get_num_threads())))
    except Exception:
        pass
    for name, loader in (("text", _load_text), ("voice", _load_voice), ("text_multi", _load_multi)):
        STATUS[name]["state"] = "loading"
        t0 = time.time()
        try:
            loader()
            STATUS[name].update(state="ready", detail=f"loaded in {time.time() - t0:.1f}s")
        except Exception as exc:  # pragma: no cover - depends on environment
            STATUS[name].update(state="fallback", detail=f"{type(exc).__name__}: {exc}"[:300])
    stt.load()   # Whisper speech recognition (sets its own status in STATUS["speech"])


def start_background_loading() -> None:
    threading.Thread(target=load_all, name="model-loader", daemon=True).start()


# ---------------------------------------------------------------------------
# Text emotion
# ---------------------------------------------------------------------------
def _text_probs_model(text: str) -> dict[str, float]:
    import torch

    with _lock, torch.no_grad():
        enc = _text["tok"](text, return_tensors="pt", truncation=True, max_length=256)
        logits = _text["model"](**enc).logits[0]
        probs = torch.sigmoid(logits).tolist()
    return dict(zip(_text["labels"], probs))


def _text_probs_lexicon(text: str) -> dict[str, float]:
    t = text.lower()
    scores = {k: len(re.findall(rf"\b({v})\b", t)) for k, v in LEXICON.items()}
    total = sum(scores.values())
    if total == 0:
        return {"neutral": 0.8}
    out = {k: 0.85 * v / total for k, v in scores.items() if v}
    out["neutral"] = 0.15
    return out


# weak / ambiguous labels count half; "neutral" is GoEmotions' most frequent training
# label (~30 %) so the model over-predicts it - a 0.85 prior correction rebalances it.
LABEL_WEIGHT = {"approval": 0.5, "caring": 0.5, "desire": 0.5, "realization": 0.5, "curiosity": 0.5,
                "neutral": 0.85, "confusion": 0.8}


def group_goemotions(probs: dict[str, float]) -> dict[str, float]:
    """28 sigmoid scores -> 6 groups using noisy-OR: P(group) = 1 - prod(1 - w*p).

    v1 SUMMED members, so nine weak positive labels outvoted one clear emotion
    ("I feel okay I guess" -> 82 % joy). Noisy-OR lets independent evidence add
    up gently and can never exceed 1. Measured on emotion_cases.json:
    v1 60.9 % -> v2 accuracy reported by scripts/evaluate_emotion.py."""
    keep = {c: 1.0 for c in COMMON}
    for label, p in probs.items():
        g = TEXT_TO_COMMON.get(label, "neutral")
        keep[g] *= 1.0 - LABEL_WEIGHT.get(label, 1.0) * p
    groups = {k: 1.0 - v for k, v in keep.items()}
    s = sum(groups.values()) or 1.0
    return {k: v / s for k, v in groups.items()}


def _multi_probs(text: str) -> dict[str, float]:
    import torch

    with _lock, torch.no_grad():
        enc = _multi["tok"](text, return_tensors="pt", truncation=True, max_length=256)
        p = torch.softmax(_multi["model"](**enc).logits[0], dim=-1).tolist()
    return dict(zip(_multi["labels"], p))


def _indic_lexicon(text: str) -> dict[str, float]:
    """Counts Indian-language emotion words; a negation right after a joy word
    ("accha nahi lag raha") flips it to sadness."""
    t = text.lower()
    hits = {k: 0.0 for k in INDIC_LEXICON}
    for emo, pat in INDIC_LEXICON.items():
        for m in re.finditer(pat, t):
            if emo == "joy" and _NEG_AFTER.match(t[m.end():m.end() + 25]):
                hits["sadness"] += 1
            else:
                hits[emo] += 1
    return hits


def _analyze_indic(text: str) -> tuple[dict[str, float], str, list[str]]:
    """Hindi / Hinglish / Kannada: XLM-EMO (4 emotions) blended with the lexicon."""
    hits = _indic_lexicon(text)
    n_hits = sum(hits.values())
    groups = {c: 0.0 for c in COMMON}
    notes: list[str] = []
    if _multi["model"] is not None:
        p = _multi_probs(text)
        conf = max(p.values())
        # XLM-EMO has no "neutral" class: low confidence -> treat part of the mass as neutral.
        # One- or two-word replies ("हाँ", "ok", "ಹೌದು") carry no emotion of their own.
        neutral = min(0.7, max(0.0, (0.6 - conf) / 0.6) * 0.9)
        if len(re.findall(r"\w+", text)) <= 2 and not n_hits:
            neutral = 0.85
        for k, v in p.items():
            if k in groups:
                groups[k] = v * (1 - neutral)
        groups["neutral"] = neutral
        engine = "xlm-emo" + (" + indic lexicon" if n_hits else "")
    else:
        groups["neutral"] = 0.6
        engine = "indic lexicon"
    if n_hits:
        w = 0.5 if _multi["model"] is not None else 0.85
        lex = {k: v / n_hits for k, v in hits.items()}
        for k in groups:
            groups[k] = (1 - w) * groups[k] + w * lex.get(k, 0.0)
        found = [k for k, v in hits.items() if v]
        notes.append("emotion words found: " + ", ".join(found))
    s = sum(groups.values()) or 1.0
    return {k: v / s for k, v in groups.items()}, engine, notes


def analyze_text(text: str, lang: str = "en") -> dict:
    """Emotion probabilities (6 groups), distress and reliability for one message."""
    notes: list[str] = []
    top: list[tuple[str, float]]
    if lang in {"hi", "kn", "hinglish"}:
        groups, engine, notes = _analyze_indic(text)
        top = sorted(groups.items(), key=lambda kv: -kv[1])[:5]
        conf = top[0][1]
    else:
        if _text["model"] is not None:
            probs = _text_probs_model(text)
            engine = "roberta-go_emotions"
        else:
            probs = _text_probs_lexicon(text)
            engine = "lexicon-fallback"
        groups = group_goemotions(probs)
        top = sorted(probs.items(), key=lambda kv: -kv[1])[:5]
        conf = top[0][1] if top else 0.0

    distress = sum(GROUP_DISTRESS[k] * v for k, v in groups.items())
    words = len(re.findall(r"\w+", text))
    length_factor = min(1.0, 0.25 + words / 10.0)
    reliability = length_factor * (0.55 + 0.45 * min(1.0, conf))
    if engine in {"lexicon-fallback", "indic lexicon"}:
        reliability *= 0.6

    dominant = max(groups, key=groups.get)
    explanations = []
    if dominant in {"sadness", "fear", "anger"} and groups[dominant] >= 0.4:
        explanations.append(f"language conveys {dominant} ({groups[dominant]:.0%})")
    explanations += notes
    if words <= 2:
        explanations.append("very short message - low text reliability")

    return {
        "engine": engine,
        "language": lang,
        "top": [{"label": k, "score": round(v, 4)} for k, v in top],
        "emotions": {k: round(v, 4) for k, v in groups.items()},
        "dominant": dominant,
        "distress": round(distress, 4),
        "reliability": round(reliability, 4),
        "explanations": explanations,
    }


def text_signal(result: dict) -> Signal:
    return Signal(result["distress"], result["reliability"], result["emotions"], 0.0, result["explanations"])


# ---------------------------------------------------------------------------
# Voice emotion = wav2vec2 classifier (60%) + explainable prosody (40%)
# ---------------------------------------------------------------------------
def analyze_voice(wav_bytes: bytes, transcript: str | None = None) -> dict:
    x, sr = prosody.read_wav(wav_bytes)
    pros = prosody.analyze(x, sr, transcript)
    model_out = None
    if _voice["model"] is not None and pros["speech_s"] > 0.3:
        import torch

        with _lock, torch.no_grad():
            clip = x[: sr * 12]  # cap at 12 s for speed
            inputs = _voice["fe"](clip, sampling_rate=sr, return_tensors="pt")
            logits = _voice["model"](**inputs).logits[0]
            p = torch.softmax(logits, dim=-1).tolist()
        raw = dict(zip(_voice["labels"], p))
        emo = {VOICE_LABELS.get(k, k): float(v) for k, v in raw.items()}
        model_distress = sum(VOICE_DISTRESS.get(k, 0.0) * v for k, v in emo.items())
        model_out = {
            "engine": "wav2vec2-superb-er",
            "emotions": {k: round(v, 4) for k, v in emo.items()},
            "distress": round(model_distress, 4),
            "confidence": round(entropy_confidence(emo), 4),
        }

    emotions = {c: 0.0 for c in COMMON}
    if model_out:
        distress = 0.6 * model_out["distress"] + 0.4 * pros["distress"]
        for k, v in model_out["emotions"].items():
            emotions[k] = v
        reliability = pros["reliability"] * (0.7 + 0.3 * model_out["confidence"])
        engine = "wav2vec2 + prosody"
    else:
        distress = pros["distress"]
        emotions["neutral"] = 1.0 - distress
        emotions["sadness"] = distress
        reliability = pros["reliability"] * 0.6
        engine = "prosody-only"

    explanations = list(pros["explanations"])
    if model_out:
        top = max(model_out["emotions"], key=model_out["emotions"].get)
        if top in {"sadness", "anger"} and model_out["emotions"][top] > 0.45:
            explanations.insert(0, f"vocal tone classified as {top} ({model_out['emotions'][top]:.0%})")

    return {
        "engine": engine,
        "distress": round(float(distress), 4),
        "reliability": round(float(reliability), 4),
        "emotions": {k: round(v, 4) for k, v in emotions.items()},
        "model": model_out,
        "prosody": pros,
        "explanations": explanations,
    }


def voice_signal(result: dict) -> Signal:
    return Signal(result["distress"], result["reliability"], result["emotions"], 0.0, result["explanations"])


def wait_until_loaded(timeout: float = 180.0) -> None:
    t0 = time.time()
    while time.time() - t0 < timeout:
        if all(s["state"] in {"ready", "fallback"} for s in STATUS.values()):
            return
        time.sleep(0.5)
