# MindBridge

**A multimodal AI companion for emotional support and distress-risk triage.**
Students talk to **Anvaya** (Sanskrit: *connection*) by text or video. MindBridge reads emotion from the face
(personally calibrated, with facial action units), the voice and the words, combines them with *reliability-weighted
fusion*, understands and replies in English, Hindi, Hinglish and Kannada, and escalates to people — counsellor
console, trusted contact, Tele-MANAS 14416 — when needed. Light and dark themes.

## Run it
1. Install Python 3.12 (tick *Add to PATH*).
2. `scripts\setup.bat` (first time only).
3. `scripts\run.bat` → opens http://localhost:8000 (use Chrome or Edge).

Tests: `scripts\run_tests.bat` (143 tests) and `node frontend\tests\faceLogic.test.ts`.

Everything is free and works offline after setup. Optional free LLM keys go in `.env` (see `.env.example`).

**New here? Read the plain-language [Project Guide](docs/PROJECT_GUIDE.md).**

**Full documentation, architecture, build history, demo script and viva Q&A: [memory.md](memory.md).**
Verification record: [CHECKLIST.md](CHECKLIST.md).

> Student research prototype — not a substitute for professional care. In an emergency call 112;
> for free mental-health support call Tele-MANAS 14416.
