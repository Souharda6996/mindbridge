"""Hand-crafted, explainable vocal features (pure NumPy, no extra deps).

Clinically, low mood is associated with lower vocal energy, more and longer
pauses, reduced pitch variability (monotone voice) and slower speech; anxiety
with pitch instability (tremor). We measure those directly so the system can
explain *why* the voice sounded distressed.
"""
from __future__ import annotations

import io
import wave

import numpy as np

SR = 16000
FRAME = 400      # 25 ms
HOP = 160        # 10 ms


def read_wav(data: bytes) -> tuple[np.ndarray, int]:
    """Decode a PCM WAV (8/16/32-bit, mono or stereo) into float32 mono at 16 kHz."""
    with wave.open(io.BytesIO(data), "rb") as w:
        sr = w.getframerate()
        ch = w.getnchannels()
        sw = w.getsampwidth()
        raw = w.readframes(w.getnframes())
    if sw == 2:
        x = np.frombuffer(raw, dtype=np.int16).astype(np.float32) / 32768.0
    elif sw == 4:
        x = np.frombuffer(raw, dtype=np.int32).astype(np.float32) / 2147483648.0
    elif sw == 1:
        x = (np.frombuffer(raw, dtype=np.uint8).astype(np.float32) - 128.0) / 128.0
    else:
        raise ValueError(f"unsupported sample width {sw}")
    if ch > 1:
        x = x.reshape(-1, ch).mean(axis=1)
    if sr != SR and len(x) > 1:
        n_out = int(round(len(x) * SR / sr))
        x = np.interp(np.linspace(0, len(x) - 1, n_out), np.arange(len(x)), x).astype(np.float32)
    return x, SR


def _frames(x: np.ndarray, frame: int = FRAME, hop: int = HOP) -> np.ndarray:
    if len(x) < frame:
        x = np.pad(x, (0, frame - len(x)))
    n = 1 + (len(x) - frame) // hop
    idx = np.arange(frame)[None, :] + hop * np.arange(n)[:, None]
    return x[idx]


def _pitch(frame: np.ndarray, sr: int = SR, fmin: float = 70, fmax: float = 400) -> float | None:
    f = frame - frame.mean()
    if np.max(np.abs(f)) < 1e-4:
        return None
    ac = np.correlate(f, f, mode="full")[len(f) - 1:]
    if ac[0] <= 0:
        return None
    ac = ac / ac[0]
    lo, hi = int(sr / fmax), int(sr / fmin)
    hi = min(hi, len(ac) - 1)
    if hi <= lo:
        return None
    lag = lo + int(np.argmax(ac[lo:hi]))
    if ac[lag] < 0.45:          # weakly periodic -> unvoiced
        return None
    return sr / lag


def _scale(v: float, lo: float, hi: float) -> float:
    """Map v linearly so that lo -> 0 and hi -> 1 (works for lo > hi too)."""
    if hi == lo:
        return 0.0
    return float(min(1.0, max(0.0, (v - lo) / (hi - lo))))


def analyze(x: np.ndarray, sr: int = SR, transcript: str | None = None) -> dict:
    duration = len(x) / sr
    if duration < 0.3:
        return {"duration_s": round(duration, 2), "speech_s": 0.0, "reliability": 0.0,
                "distress": 0.0, "features": {}, "explanations": ["recording too short"]}

    frames = _frames(x)
    rms = np.sqrt(np.mean(frames ** 2, axis=1)) + 1e-9
    noise = float(np.percentile(rms, 10))
    loud = float(np.percentile(rms, 95))
    thr = noise + 0.25 * (loud - noise)
    speech = rms > max(thr, 0.004)
    speech_frames = int(speech.sum())
    speech_s = speech_frames * HOP / sr

    if speech_frames < 10:
        return {"duration_s": round(duration, 2), "speech_s": round(speech_s, 2), "reliability": 0.05,
                "distress": 0.0, "features": {"snr_db": 0.0},
                "explanations": ["almost no speech detected"]}

    idx = np.where(speech)[0]
    span = speech[idx[0]: idx[-1] + 1]
    pause_ratio = float(1.0 - span.mean())
    # long pauses: runs of silence >= 400 ms inside the speaking span
    long_pauses, run = 0, 0
    for s in span:
        if not s:
            run += 1
        else:
            if run * HOP / sr >= 0.4:
                long_pauses += 1
            run = 0

    energy_db = float(20 * np.log10(np.mean(rms[speech])))
    snr_db = float(20 * np.log10(loud / max(noise, 1e-6)))

    # pitch on 40 ms windows of voiced speech
    pframes = _frames(x, frame=640, hop=320)
    prms = np.sqrt(np.mean(pframes ** 2, axis=1))
    pitches = []
    for fr, e in zip(pframes, prms):
        if e > thr:
            p = _pitch(fr, sr)
            if p:
                pitches.append(p)
    pitches_arr = np.array(pitches) if pitches else np.array([])
    if len(pitches_arr) >= 5:
        semis = 12 * np.log2(pitches_arr / np.median(pitches_arr))
        pitch_std_st = float(np.std(semis))
        periods = 1.0 / pitches_arr
        jitter = float(np.mean(np.abs(np.diff(periods))) / np.mean(periods))
        pitch_mean = float(np.mean(pitches_arr))
    else:
        pitch_std_st, jitter, pitch_mean = 3.0, 0.02, 0.0

    words = len(transcript.split()) if transcript else 0
    rate = words / max(speech_s, 0.5) if words else None

    comp = {
        "pauses": _scale(pause_ratio, 0.20, 0.60),
        "monotone": _scale(pitch_std_st, 4.0, 1.2) if len(pitches_arr) >= 5 else 0.3,
        "low_energy": _scale(energy_db, -22.0, -42.0),
        "tremor": _scale(jitter, 0.03, 0.10) if len(pitches_arr) >= 5 else 0.0,
        "slow_rate": _scale(rate, 2.6, 1.2) if rate is not None else 0.3,
    }
    wts = {"pauses": 0.28, "monotone": 0.28, "low_energy": 0.16, "tremor": 0.12, "slow_rate": 0.16}
    distress = float(sum(comp[k] * wts[k] for k in comp))

    expl = []
    if comp["pauses"] > 0.5:
        expl.append(f"long pauses ({pause_ratio:.0%} silence, {long_pauses} long breaks)")
    if comp["monotone"] > 0.5:
        expl.append(f"flat, monotone pitch ({pitch_std_st:.1f} semitone variation)")
    if comp["low_energy"] > 0.5:
        expl.append(f"low vocal energy ({energy_db:.0f} dBFS)")
    if comp["tremor"] > 0.5:
        expl.append(f"unsteady / trembling pitch (jitter {jitter:.1%})")
    if rate is not None and comp["slow_rate"] > 0.5:
        expl.append(f"slow speech ({rate:.1f} words/s)")

    reliability = _scale(speech_s, 0.3, 2.5) * _scale(snr_db, 6.0, 22.0)
    return {
        "duration_s": round(duration, 2),
        "speech_s": round(speech_s, 2),
        "reliability": round(float(reliability), 4),
        "distress": round(distress, 4),
        "components": {k: round(v, 3) for k, v in comp.items()},
        "features": {
            "pause_ratio": round(pause_ratio, 3), "long_pauses": long_pauses,
            "energy_db": round(energy_db, 1), "snr_db": round(snr_db, 1),
            "pitch_mean_hz": round(pitch_mean, 1), "pitch_std_semitones": round(pitch_std_st, 2),
            "jitter": round(jitter, 4), "speech_rate_wps": round(rate, 2) if rate else None,
        },
        "explanations": expl,
    }
