"""Measures text-emotion accuracy on backend/app/resources/emotion_cases.json.

Compares v1 (sum-grouping, English model for every language) with v2
(max-grouping + label remap, XLM-EMO + lexicon for Hindi/Hinglish/Kannada).

Run:  .venv\\Scripts\\python.exe scripts\\evaluate_emotion.py
"""
import json
import sys
from collections import defaultdict
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app import config  # noqa: E402
from backend.app.services import language, models  # noqa: E402

V1_MAP = {  # the original v1 grouping
    **{k: "joy" for k in ["admiration", "amusement", "approval", "caring", "desire", "excitement", "gratitude",
                          "joy", "love", "optimism", "pride", "relief"]},
    **{k: "sadness" for k in ["sadness", "grief", "disappointment", "remorse", "embarrassment"]},
    "fear": "fear", "nervousness": "fear",
    **{k: "anger" for k in ["anger", "annoyance", "disapproval", "disgust"]},
    **{k: "surprise" for k in ["surprise", "realization", "curiosity", "confusion"]},
    "neutral": "neutral",
}


def v1(text: str) -> str:
    probs = models._text_probs_model(text)
    groups = defaultdict(float)
    for k, v in probs.items():
        groups[V1_MAP.get(k, "neutral")] += v
    return max(groups, key=groups.get)


def main() -> None:
    models.load_all()
    print("model status:", {k: v["state"] for k, v in models.STATUS.items()})
    for name in ("emotion_cases.json", "emotion_holdout.json"):
        print(f"\n===== {name} =====")
        run(name)


def run(fname: str) -> None:
    cases = json.loads((config.BACKEND_DIR / "app" / "resources" / fname).read_text(encoding="utf-8"))
    score = {"v1": defaultdict(lambda: [0, 0]), "v2": defaultdict(lambda: [0, 0])}
    for c in cases:
        p1 = v1(c["text"])
        out = models.analyze_text(c["text"], language.detect(c["text"]))
        p2 = out["dominant"]
        for name, p in (("v1", p1), ("v2", p2)):
            score[name][c["lang"]][0] += int(p == c["expected"])
            score[name][c["lang"]][1] += 1
        flag = "" if p2 == c["expected"] else "   <-- v2 miss"
        print(f"[{c['lang']:8s}] {c['text'][:48]:50s} exp={c['expected']:8s} v1={p1:8s} v2={p2:8s}{flag}")
    print()
    for name in ("v1", "v2"):
        tot = sum(v[0] for v in score[name].values()), sum(v[1] for v in score[name].values())
        per = ", ".join(f"{k}: {v[0]}/{v[1]}" for k, v in score[name].items())
        print(f"{name}: {tot[0]}/{tot[1]} = {tot[0] / tot[1]:.1%}   ({per})")


if __name__ == "__main__":
    main()
