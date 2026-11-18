"""Download the two open-source models into ./models_cache (one-time, ~850 MB).

After this runs once, MindBridge works fully offline: config.py sees the
`.models_ready` marker and switches Hugging Face into offline mode.

Run:  .venv\\Scripts\\python.exe scripts\\download_models.py
"""
from __future__ import annotations

import os
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
os.environ["HF_HOME"] = str(ROOT / "models_cache")
os.environ.pop("HF_HUB_OFFLINE", None)
os.environ.pop("TRANSFORMERS_OFFLINE", None)

from huggingface_hub import snapshot_download  # noqa: E402

MODELS = {
    "SamLowe/roberta-base-go_emotions": "Text emotion, English (RoBERTa, GoEmotions 28 labels)",
    "MilaNLProc/xlm-emo-t": "Text emotion, multilingual incl. Hindi (XLM-RoBERTa, 4 labels)",
    "superb/wav2vec2-base-superb-er": "Voice emotion (wav2vec2, IEMOCAP 4 labels)",
}
ALLOW = ["*.json", "*.txt", "*.safetensors", "*.model", "merges.txt", "vocab.*"]


def download_whisper() -> bool:
    print("[download] Speech recognition + language detection (Whisper small, ~480 MB)", flush=True)
    try:
        snapshot_download(repo_id="Systran/faster-whisper-small", local_dir=str(ROOT / "models_cache" / "whisper-small"))
        print("[ok] whisper-small", flush=True)
        return True
    except Exception as exc:  # pragma: no cover
        print(f"[error] whisper: {exc}", flush=True)
        return False


def main() -> int:
    ok = download_whisper()
    for repo, desc in MODELS.items():
        print(f"[download] {desc}: {repo}", flush=True)
        try:
            path = snapshot_download(repo_id=repo, allow_patterns=ALLOW)
            files = [p.name for p in Path(path).iterdir()]
            if not any(f.endswith(".safetensors") for f in files):
                # older repos only ship pytorch_model.bin
                path = snapshot_download(repo_id=repo, allow_patterns=ALLOW + ["*.bin"])
            print(f"[ok] {repo} -> {path}", flush=True)
        except Exception as exc:  # pragma: no cover
            ok = False
            print(f"[error] {repo}: {exc}", flush=True)
    if ok:
        (ROOT / "models_cache" / ".models_ready").write_text("ok", encoding="utf-8")
        print("[done] all models ready - MindBridge can now run offline", flush=True)
        return 0
    return 1


if __name__ == "__main__":
    sys.exit(main())
