"""Central configuration for MindBridge.

Everything is driven by environment variables (optionally loaded from a `.env`
file in the project root) so the project can move between machines without
code changes. Importing this module must happen BEFORE `transformers` is
imported, because it points the Hugging Face cache at the project folder.
"""
from __future__ import annotations

import os
from pathlib import Path

ROOT_DIR = Path(__file__).resolve().parents[2]          # .../FINAL PROJ
BACKEND_DIR = ROOT_DIR / "backend"
DATA_DIR = Path(os.environ.get("MINDBRIDGE_DATA_DIR", BACKEND_DIR / "data"))
MODELS_DIR = ROOT_DIR / "models_cache"
FRONTEND_DIST = ROOT_DIR / "frontend" / "dist"
CASES_FILE = BACKEND_DIR / "app" / "resources" / "crisis_cases.json"

try:  # optional .env support
    from dotenv import load_dotenv

    load_dotenv(ROOT_DIR / ".env")
except Exception:  # pragma: no cover - dotenv is optional
    pass

# Keep downloaded models inside the project so the folder is self-contained.
os.environ.setdefault("HF_HOME", str(MODELS_DIR))
os.environ.setdefault("HF_HUB_DISABLE_TELEMETRY", "1")
os.environ.setdefault("TOKENIZERS_PARALLELISM", "false")
if (MODELS_DIR / ".models_ready").exists():
    # Models already downloaded -> never touch the network at startup.
    os.environ.setdefault("HF_HUB_OFFLINE", "1")
    os.environ.setdefault("TRANSFORMERS_OFFLINE", "1")


def _flag(name: str, default: bool) -> bool:
    value = os.environ.get(name)
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


DATA_DIR.mkdir(parents=True, exist_ok=True)
DB_PATH = Path(os.environ.get("MINDBRIDGE_DB", DATA_DIR / "mindbridge.db"))
KEY_PATH = DATA_DIR / "secret.key"

# --- AI models (free, open-source, run on CPU) ------------------------------
ENABLE_ML_MODELS = _flag("MINDBRIDGE_ENABLE_MODELS", True)
TEXT_MODEL_ID = os.environ.get("TEXT_MODEL_ID", "SamLowe/roberta-base-go_emotions")
TEXT_MULTI_MODEL_ID = os.environ.get("TEXT_MULTI_MODEL_ID", "MilaNLProc/xlm-emo-t")
VOICE_MODEL_ID = os.environ.get("VOICE_MODEL_ID", "superb/wav2vec2-base-superb-er")

# --- Conversation engine (all free options) ---------------------------------
# auto = first available of: groq -> gemini -> ollama -> offline
LLM_PROVIDER = os.environ.get("LLM_PROVIDER", "auto").strip().lower()
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "").strip()
GROQ_MODELS = [m.strip() for m in os.environ.get(
    "GROQ_MODELS", "llama-3.3-70b-versatile,openai/gpt-oss-120b,llama-3.1-8b-instant"
).split(",") if m.strip()]
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "").strip()
GEMINI_MODELS = [m.strip() for m in os.environ.get(
    "GEMINI_MODELS", "gemini-2.5-flash,gemini-2.0-flash"
).split(",") if m.strip()]
OLLAMA_URL = os.environ.get("OLLAMA_URL", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "llama3.2:3b")
LLM_TIMEOUT_S = float(os.environ.get("LLM_TIMEOUT_S", "20"))

# --- Helplines shown in the crisis card (India) -----------------------------
HELPLINES = [
    {"name": "Tele-MANAS (Govt. of India, 24x7, free)", "number": "14416",
     "alt": "1-800-891-4416", "languages": "20+ Indian languages"},
    {"name": "National Emergency Number", "number": "112", "alt": None,
     "languages": "Police / Ambulance / Fire"},
]

APP_VERSION = "2.0.0"

# Name of the AI companion. "Anvaya" (अन्वय) is Sanskrit for "connection" -
# the companion is the connection between a student in distress and real care.
COMPANION_NAME = os.environ.get("COMPANION_NAME", "Anvaya")
