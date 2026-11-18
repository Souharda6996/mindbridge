"""Reliability-weighted multimodal fusion  (the core novelty of MindBridge).

Every modality m in {face, voice, text} reports
    d_m  - a distress estimate in [0, 1]
    r_m  - how much that estimate can be trusted right now, in [0, 1]
           (face: detection score, lighting, size, frontal pose;
            voice: speech length, signal-to-noise ratio;
            text: message length, classifier confidence)
and has a fixed prior trust  b_m  (text 1.0, voice 0.8, face 0.7).

    w_m  = b_m * r_m * age_decay_m
    D    = sum(w_m * d_m) / sum(w_m)              fused distress
    C    = sum(w_m) / sum(b_m)                    confidence (0 if nothing usable)
    S_t  = a * D + (1 - a) * S_{t-1}              smoothed trajectory

Consequences you can demonstrate live:
    * camera covered / dark room  -> r_face ~ 0  -> face weight drops to ~0
    * noisy room                  -> r_voice drops -> text dominates
    * one-word reply ("ok")       -> r_text drops  -> face/voice dominate
    * a single frown does not spike the score (temporal smoothing)
"""
from __future__ import annotations

import math
from dataclasses import dataclass, field

BASE_TRUST = {"text": 1.0, "voice": 0.8, "face": 0.7}
ALPHA = 0.4                 # smoothing factor for the trajectory
HALF_LIFE_S = 90.0          # older signals count less (signal freshness)
COMMON = ["joy", "sadness", "fear", "anger", "surprise", "neutral"]

# distress weight of each emotion in the shared label space
FACE_DISTRESS = {"sad": 0.85, "fearful": 0.75, "angry": 0.55, "disgusted": 0.45,
                 "surprised": 0.20, "neutral": 0.12, "happy": 0.0}
FACE_TO_COMMON = {"happy": "joy", "sad": "sadness", "fearful": "fear", "angry": "anger",
                  "disgusted": "anger", "surprised": "surprise", "neutral": "neutral"}


@dataclass
class Signal:
    distress: float
    reliability: float
    emotions: dict[str, float] = field(default_factory=dict)   # COMMON label space
    age_s: float = 0.0
    explanations: list[str] = field(default_factory=list)

    def clipped(self) -> "Signal":
        return Signal(
            distress=min(1.0, max(0.0, float(self.distress))),
            reliability=min(1.0, max(0.0, float(self.reliability))),
            emotions=self.emotions, age_s=max(0.0, self.age_s),
            explanations=self.explanations,
        )


def decay(age_s: float) -> float:
    return 0.5 ** (age_s / HALF_LIFE_S)


def fuse(signals: dict[str, Signal | None], prev_smoothed: float | None = None,
         alpha: float = ALPHA) -> dict:
    weights: dict[str, float] = {}
    used: dict[str, Signal] = {}
    for name, sig in signals.items():
        if sig is None or name not in BASE_TRUST:
            continue
        sig = sig.clipped()
        w = BASE_TRUST[name] * sig.reliability * decay(sig.age_s)
        if w > 1e-6:
            weights[name] = w
            used[name] = sig

    total_w = sum(weights.values())
    total_b = sum(BASE_TRUST.values())
    if total_w <= 1e-6:
        fused = prev_smoothed if prev_smoothed is not None else 0.0
        return {
            "fused": round(fused, 4), "confidence": 0.0,
            "smoothed": round(fused, 4), "weights": {}, "contributions": {},
            "emotions": {k: (1.0 if k == "neutral" else 0.0) for k in COMMON},
            "dominant_emotion": "neutral", "dominant_modality": None,
            "explanations": [], "modalities": {},
        }

    fused = sum(weights[n] * used[n].distress for n in used) / total_w
    confidence = min(1.0, total_w / total_b)
    smoothed = fused if prev_smoothed is None else alpha * fused + (1 - alpha) * prev_smoothed

    norm_w = {n: weights[n] / total_w for n in weights}
    contributions = {n: norm_w[n] * used[n].distress for n in used}

    emotions = {k: 0.0 for k in COMMON}
    for n, sig in used.items():
        s = sum(sig.emotions.values()) or 1.0
        for k, v in sig.emotions.items():
            if k in emotions:
                emotions[k] += norm_w[n] * v / s
    es = sum(emotions.values()) or 1.0
    emotions = {k: round(v / es, 4) for k, v in emotions.items()}

    explanations: list[str] = []
    for n in sorted(used, key=lambda x: -contributions[x]):
        for line in used[n].explanations[:2]:
            explanations.append(f"{n}: {line}")

    return {
        "fused": round(fused, 4),
        "confidence": round(confidence, 4),
        "smoothed": round(smoothed, 4),
        "weights": {k: round(v, 4) for k, v in norm_w.items()},
        "contributions": {k: round(v, 4) for k, v in contributions.items()},
        "emotions": emotions,
        "dominant_emotion": max(emotions, key=emotions.get),
        "dominant_modality": max(contributions, key=contributions.get),
        "explanations": explanations,
        "modalities": {n: {"distress": round(s.distress, 4), "reliability": round(s.reliability, 4),
                           "age_s": round(s.age_s, 1)} for n, s in used.items()},
    }


# ---------------------------------------------------------------------------
# Face signal: probabilities come from the in-browser CNN (face-api.js).
# ---------------------------------------------------------------------------
def face_signal(payload: dict | None, age_s: float = 0.0) -> Signal | None:
    if not payload or not payload.get("probs"):
        return None
    probs = {k: float(v) for k, v in payload["probs"].items() if k in FACE_DISTRESS}
    total = sum(probs.values()) or 1.0
    probs = {k: v / total for k, v in probs.items()}
    distress = sum(FACE_DISTRESS[k] * v for k, v in probs.items())
    emotions = {c: 0.0 for c in COMMON}
    for k, v in probs.items():
        emotions[FACE_TO_COMMON[k]] += v
    reliability = float(payload.get("reliability", 0.5))
    explanations = []
    top = max(probs, key=probs.get)
    if top in {"sad", "fearful", "angry"} and probs[top] > 0.4:
        explanations.append(f"facial expression mostly {top} ({probs[top]:.0%})")
    details = payload.get("details") or {}
    if reliability < 0.35:
        why = details.get("issue") or "poor visibility"
        explanations.append(f"low face reliability ({why})")
    return Signal(distress, reliability, emotions, age_s, explanations)


def entropy_confidence(probs: dict[str, float]) -> float:
    """1 - normalised entropy: 1 = certain, 0 = uniform."""
    vals = [p for p in probs.values() if p > 0]
    if len(vals) <= 1:
        return 1.0
    s = sum(vals)
    h = -sum((p / s) * math.log(p / s) for p in vals)
    return max(0.0, 1.0 - h / math.log(len(probs)))
