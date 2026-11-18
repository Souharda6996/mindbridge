# MindBridge — Verification Checklist

Each phase was verified before the next one started. Re-run the automated checks any time:
`scripts\run_tests.bat` (expect **143 passed**) and `node frontend\tests\faceLogic.test.ts`
(expect *all face-logic tests passed*).

Legend: ✅ verified · 🔲 to be done by you on presentation day

---

# Version 2 (current)

## V2-1 — Diagnosis of reported problems
- ✅ "Always joy": reproduced — "I feel okay I guess" → 82 % joy (v1 summed 12 positive labels)
- ✅ Hindi replies in English / Hindi emotion wrong: reproduced — "मुझे बहुत गुस्सा आ रहा है" → neutral, reply English
- ✅ Loop: reproduced — grounding exercise + same validation sentence repeated every turn; "yes"/"no" ignored

## V2-2 — Text-emotion accuracy (gate: `scripts/evaluate_emotion.py`, `test_conversation.py`, `test_models.py`)
- ✅ Noisy-OR grouping + label remap + neutral prior correction
- ✅ XLM-EMO multilingual model downloaded, loads offline (`text_multi: ready`)
- ✅ Indic lexicon with negation ("accha nahi lag raha" → sadness); 1-2 word replies → neutral
- ✅ Tuning set (46): v1 60.9 % → **v2 100 %** (en 30/30, hi 8/8, hinglish 4/4, kn 4/4)
- ✅ Held-out set (22, never tuned on): v1 50 % → **v2 95.5 %** (21/22)

## V2-3 — Conversation: no loops, same language (gate: `test_conversation.py`, 24 tests)
- ✅ 10-turn English conversation: no sentence repeated
- ✅ Each exercise offered at most once; declined exercise never offered again
- ✅ Hindi → Devanagari reply, Kannada → Kannada reply, Hinglish → romanised Hindi reply
- ✅ Short answers keep the conversation's language ("ok" after Hindi stays Hindi)
- ✅ "yes" / "हाँ" / "haan" / "ಹೌದು" after an exercise offer → acknowledged
- ✅ "no" / "नहीं" / "nahi" / "ಇಲ್ಲ" → exercise declined
- ✅ "I don't know" / "पता नहीं" / "pata nahi" / "ಗೊತ್ತಿಲ್ಲ" → recognised
- ✅ "what should I do?" → practical tip for the topic
- ✅ Crisis follow-ups vary (3 different messages) and use the user's script
- ✅ Live server, real models: 6-turn English conversation without repetition; Hindi message → Hindi reply,
  "हाँ" → Hindi follow-up (checked in the browser)

## V2-4 — Face accuracy (gate: `node frontend/tests/faceLogic.test.ts`, 11 checks)
- ✅ smile → happy · lowered brows + pressed lips → angry · inner brows up + corners down → sad · surprise → surprised
- ✅ resting face → neutral · geometry scale-invariant
- ✅ a resting face the CNN reads as 60 % happy → **neutral** after calibration
- ✅ an angry frame the raw CNN calls neutral → **angry** with calibration + action units
- ✅ SSD-MobileNet + 68-landmark weights served; face module loads on WebGL
- 🔲 Live camera in Chrome (blocked in the automated browser) — see presentation-day checks

## V2-5 — Name and avatar
- ✅ Companion renamed **Anvaya** (backend greeting, prompt, UI, sidebar) via `COMPANION_NAME`
- ✅ Lotus-of-light orb: breathing 10 s cycle, opens while listening, pulses while speaking, colour by tone,
  centred correctly (transform-origin bug found and fixed)

## V2-6 — Frontend redesign
- ✅ `tsc -b && vite build`: 0 errors; initial JS 2.1 MB → 0.7 MB (face models load only in video mode)
- ✅ Light and dark themes on Home, Companion, How it works, Toolkit (screenshots checked); theme saved and applied
  before first paint; Appearance setting (Light / Dark / Match device)
- ✅ Home: wellbeing ring, one-tap mood (logs a check-in), "For you" from own data, week dots, KPIs, charts, insights
- ✅ Calm toolkit: 6 exercises, deep links (`/toolkit#box_breathing`) open the right one
- ✅ Live evaluation renders with emotion + held-out accuracy computed live
- ✅ No browser console errors other than polling during a deliberate server restart

## V2-7 — Regression
- ✅ All v1 tests still pass (crisis 74, fusion/prosody 11, API 20) + conversation 24 + real models 14 — total **143 passed**

---

# Version 3 (latest)

- ✅ Whisper-small installed and downloaded; detects English 0.99, Hindi 0.97-0.99, Kannada 0.99 on generated speech clips
- ✅ Voice endpoint: Hindi speech while the browser listens in English → Hindi reply (`test_speech.py`)
- ✅ Kannada speech without a browser transcript → asks to repeat in Kannada and switches listening to kn-IN
- ✅ Casual flow verified (10-turn script): greeting → "how are you?" answered about itself → "not feeling good" asked once
  → vague answer → offer to vent / distract / calm → distraction → movie interest → "who are you" → joke → Hindi "कैसे हो?" in Hindi
- ✅ Frontend: Auto-detect language, "I feel" palette, Settings → Conversation AI (Groq/Gemini key) — `tsc` + build clean
- ✅ Full suite **151 passed** with real models
- 🔲 On your laptop: video mode, language = Auto-detect, speak Hindi, then Kannada, then English; each reply should follow
- 🔲 (Recommended) paste a free Groq key in Settings → Conversation AI for the most human-like replies

---

# Version 1 (kept for reference — all still passing)

- ✅ Phase 1 crisis engine: 63/63 labelled messages, 100 % high-risk recall, idiom traps LOW, negation → MEDIUM
- ✅ Phase 2 models + fusion: real models load offline; fusion weights follow reliability; prosody on synthetic audio
- ✅ Phase 3 API: crisis protocol + alert + sticky HIGH + resolve; voice endpoint; journal; eval; delete-all
- ✅ Phase 4 dashboard build; Phase 5 every page in browser; Phase 6 setup.bat executed, run.bat start verified

---

## Presentation-day checks (on your laptop)
- 🔲 Close any old `run.bat` window, start `scripts\run.bat`; sidebar shows Text · English, Text · Indic, Voice **ready**
- 🔲 Chrome → Talk to Anvaya → **Video** → allow camera → relax your face until "Calibrating" finishes
- 🔲 Frown and press lips → label shows anger with "brows lowered"; smile → joy; cover camera → face weight drops
- 🔲 Press mic, speak a sentence, press again → caption appears, Anvaya answers aloud (orb pulses)
- 🔲 Type a Hindi sentence → reply in Hindi; type "yes" twice in English → no repeated question
- 🔲 *How it works → Run evaluation* once
- 🔲 (Optional) free `GROQ_API_KEY` in `.env` → reply label shows `groq/…`
- 🔲 For a fresh demo: stop run.bat, delete `backend\data\`, start again
