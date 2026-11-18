# MindBridge — Project Memory

> **A Multimodal AI Companion for Emotional Support and Distress Risk Triage**
> Final-year project · v1 built 17 Nov 2026 · **v2 (current) same day** · this file records *everything*
> needed to understand, run, move, rebuild and present the project.

---

## 0. Quick start (read this first)

| Situation | What to do |
|---|---|
| **Same PC, run the demo** | Double-click `scripts\run.bat` → browser opens `http://localhost:8000` |
| **New PC (copied the whole folder)** | 1. Install **Python 3.12** from python.org (tick *Add python.exe to PATH*) · 2. Double-click `scripts\setup.bat` (one time) · 3. Double-click `scripts\run.bat` |
| **Run all automated tests** | `scripts\run_tests.bat` → expect **143 passed**; face logic: `node frontend\tests\faceLogic.test.ts` → *all face-logic tests passed* |
| **Measure emotion accuracy** | `.venv\Scripts\python.exe scripts\evaluate_emotion.py` |
| **See conversations in 4 languages** | `.venv\Scripts\python.exe scripts\diagnose.py` |
| **Changed dashboard code** | Install Node.js 18+ → `scripts\build_frontend.bat` → restart `run.bat` |
| **Want LLM replies (free)** | Put a free Groq key in `.env` → `GROQ_API_KEY=...` → restart `run.bat` |

* Use **Google Chrome or Microsoft Edge** (voice mode needs their built-in speech recognition).
* Copy the folder **with** `models_cache\` (≈ 2 GB, three models) and the new PC needs **no internet** for the AI.
  Without it, `setup.bat` downloads them once.
* `.venv\` is machine-specific — `setup.bat` recreates it (you may delete it before copying).
* Node.js is **not** needed to run the project; the dashboard is pre-built in `frontend\dist\`.
* **After pulling new code always restart `run.bat`** (an old server keeps serving the old version).

---

## 1. What the project is

MindBridge offers private, first-line emotional support to students through a **text chat** or a
**video conversation with a companion called _Anvaya_** (अन्वय, Sanskrit for *connection* — the companion is the
connection between a student in distress and real care). While the student talks it:

1. reads emotion from the **face** (in the browser, personally calibrated), the **voice** and the **words**
   (English, Hindi, Hinglish, Kannada);
2. combines them with **reliability-weighted fusion** into a distress score with a confidence value;
3. checks every message for **crisis language** in the same four languages;
4. decides a **support tier** (LOW / MEDIUM / HIGH) with plain-language reasons;
5. replies **in the language the student used**, with active listening + CBT, never repeating itself, and
   offers **coping exercises**;
6. in a crisis, switches to a **fixed safety script**, shows **Tele-MANAS 14416 / 112**, offers to alert a
   **trusted contact**, and sends a live alert to the **counsellor console**.

It also has a personal **Home dashboard** (wellbeing score, one-tap mood, "For you" suggestions), a **mood
journal**, a **Calm toolkit** (6 exercises), a printable **therapist report**, **light / dark themes**, and full
**privacy controls** (consent, incognito, encryption, delete-all).

### The seven novelty points (say these to the panel)

1. **Reliability-weighted multimodal fusion** – each signal is weighted by how trustworthy it is *right now*
   (lighting, head pose, face size, noise, speech length, message length, model confidence, signal age).
2. **Personalised face reading with Facial Action Units** – learns each person's resting face, measures changes
   from it, and cross-checks the expression CNN with FACS action units (AU4 brow lowerer, AU12 smile, AU24 lip
   press …) measured from 68 landmarks. Fixes the "always joy" problem.
3. **Truly multilingual** – multilingual emotion model (XLM-RoBERTa), C-SSRS crisis rules and replies in English,
   Hindi (Devanagari), Hinglish and Kannada.
4. **Explainable, tiered human-in-the-loop escalation** – deterministic; language can trigger HIGH, distress alone
   only MEDIUM; LLM switched off in HIGH; HIGH stays until a counsellor resolves it; every alert lists *why*.
5. **A conversation that moves forward** – never repeats a sentence, recognises "yes / no / I don't know / what
   should I do / I'm better", staged validate → explore → deepen → cope/CBT → tip → summary.
6. **A presence that breathes with you** – the lotus-of-light orb breathes at 6 breaths/min (resonance breathing).
7. **Choice-based modality switching** – if the student keeps looking away, Anvaya offers to continue by text.

---

## 2. Architecture

```
BROWSER (React, frontend/)                                   SERVER (FastAPI, backend/)
─────────────────────────                                    ──────────────────────────────────────────────
Camera ─► SSD-MobileNet ─► 68 landmarks ─► expression CNN ─┐
          + personal baseline + action units + smoothing   │ only 7 probabilities + reliability leave the browser
Mic ─► WAV 16 kHz + Web Speech captions ───────────────────┼─► /api/voice ─► wav2vec2 + prosody ──┐
Keyboard ──────────────────────────────────────────────────┴─► /api/chat                          │
                                                                language.py (en / hi / hinglish / kn, sticky)
                                                                     │                             │
                                         crisis.py (C-SSRS 0-4) ─────┤   models.py text emotion:   │
                                                                     │   en → RoBERTa-GoEmotions   │
                                                                     │   hi/kn/hinglish → XLM-EMO  │
                                                                     │        + Indic lexicon      │
                                                                     ▼                             ▼
                                                     fusion.py (reliability-weighted) ◄────────────┘
                                                                     │
                                                     escalation.py (LOW / MEDIUM / HIGH + reasons)
                                     ┌───────────────────────────────┼─────────────────────────────┐
                                     ▼                               ▼                             ▼
                     conversation.py                         alerts → counsellor console    trusted contact (simulated)
   HIGH → crisis script (4 languages, varied follow-ups)
   else → Groq → Gemini → Ollama → offline_engine.py (4 languages, staged, no repeats)
          └► safety_filter.py
                     │
                     ▼  reply in the user's language → chat bubble / spoken by Anvaya (browser TTS)
     SQLite (backend/data/mindbridge.db) – user text encrypted with Fernet
```

### Fusion formula (write this on the board)

For each modality *m* ∈ {face, voice, text}: distress `d_m`, reliability `r_m`, prior trust `b_m`
(text 1.0, voice 0.8, face 0.7), signal age `t_m`:

```
w_m = b_m · r_m · 0.5^(t_m / 90 s)      D = Σ w_m·d_m / Σ w_m      C = Σ w_m / Σ b_m      S_t = 0.4·D + 0.6·S_(t-1)
```

### Text emotion (models.py) — what changed in v2 and why

| Problem found | Cause | Fix |
|---|---|---|
| "I feel okay I guess" → 82 % joy | 12 GoEmotions labels were **summed** into "joy"; "approval" counted as joy | **noisy-OR** grouping `P(g)=1-Π(1-w·p)`; approval / caring / desire / realization / curiosity → neutral at half weight; neutral prior ×0.85 (it is GoEmotions' most frequent label) |
| Hindi / Kannada text → always neutral | English-only model | `MilaNLProc/xlm-emo-t` (XLM-RoBERTa, 19 languages) + Hindi/Hinglish/Kannada emotion lexicon with negation ("accha nahi lag raha" → sadness); 1-2 word replies → neutral |
| "better off without me" → joy | surface sentiment | crisis language floors text distress and pulls emotion to sadness (`analyze_text_with_risk`) |

Measured (scripts/evaluate_emotion.py):

| Set | v1 | v2 |
|---|---|---|
| emotion_cases.json (46 sentences, used while tuning) | 60.9 % (en 28/30, hi 0/8, hinglish 0/4, kn 0/4) | **100 %** |
| emotion_holdout.json (22 new sentences, **never tuned on**) | 50.0 % | **95.5 %** (21/22) |

Quote the held-out number as the honest accuracy.

### Face reading (frontend/src/lib/face.ts + faceLogic.ts) — v2

1. **SSD-MobileNet v1** detector (more accurate than TinyFaceDetector) + **full 68-point landmarks**.
2. **Reliability** = detection score × face size × brightness × frontal pose (explained in the UI).
3. **Calibration**: the first 6 good frames (~4 s, frontal, well lit) store the person's resting expression mix
   and face geometry. *Recalibrate* button in video mode.
4. **Baseline-relative CNN**: only *increases* over the resting mix count as expression; no change → neutral.
   Before calibration a prior correction rebalances the CNN's neutral/happy bias.
5. **Action units** (scale-free, inter-ocular units): AU4 brow lowerer, AU1/AU2 brow raisers, AU12 smile, AU15
   corner depressor, AU24 lip press, AU26 jaw drop, AU5/AU7 lid raise/tighten, AU10 upper-lip raiser →
   Ekman prototypes (e.g. anger = AU4 + AU24 + AU5/7 − smile).
6. **Combine** 55 % calibrated CNN + 45 % AUs (AU weight × frontal-pose factor), **EMA** smoothing.
7. UI shows the top emotion, reliability and cues ("brows lowered · lips pressed").

`node frontend/tests/faceLogic.test.ts` proves: smile → happy, lowered brows + pressed lips → angry, inner brows up
+ corners down → sad, surprise → surprised, resting → neutral, scale invariance, a resting face the CNN reads as
60 % happy is neutral after calibration, and an angry frame the raw CNN calls neutral becomes angry.

### Conversation engine (offline_engine.py) — v2

* Every sentence exists in **en / hi / hinglish / kn**; language detected per message (`language.py`), short
  replies keep the previous language.
* Session memory of every sentence used → **no repeats** (reflection lines are skipped rather than reused).
* Per-topic stages: validate (once) → explore → deepen → cope / CBT reframe → practical tip → summary.
* Intents: greeting, thanks, bye, yes (after an exercise offer → "go ahead"), no (declines that exercise for
  good), I don't know, what should I do (→ concrete tip), I'm better.
* Each exercise offered once; counsellor offer at most every 4 turns; every 4th turn holds space without a question.
* Crisis: first message = full script with helplines (4 languages); later turns = varied short safety follow-ups.
* LLM path: prompt enforces the reply language and forbids repeating; Groq uses frequency/presence penalties;
  a reply too similar to an earlier one is rejected.

### Escalation rules (escalation.py) — unchanged

| Tier | Trigger | Action |
|---|---|---|
| LOW | – | supportive chat, exercises |
| MEDIUM | crisis level 1, or smoothed distress ≥ 0.60 for 3 turns (≥ 0.80 for 2) with confidence ≥ 0.30, or high distress in 2 of last 3 sessions | gentler tone, check-in + counsellor buttons, non-urgent alert |
| HIGH | crisis level ≥ 2 | crisis script (no LLM), helplines, trusted-contact offer, urgent alert; sticky until resolved |

---

## 3. Tech stack (all free)

| Layer | Technology |
|---|---|
| Backend | Python 3.12, FastAPI, Uvicorn |
| Database / encryption | SQLite, `cryptography` Fernet |
| Text emotion (English) | `SamLowe/roberta-base-go_emotions` |
| Text emotion (Hindi, Hinglish, Kannada) | `MilaNLProc/xlm-emo-t` + lexicon |
| Voice emotion | `superb/wav2vec2-base-superb-er` + NumPy prosody |
| Face | `@vladmandic/face-api` (TensorFlow.js/WebGL): SSD-MobileNet v1, 68-landmark net, expression CNN |
| Speech | Web Speech API + SpeechSynthesis |
| Dialogue | Groq / Gemini free tiers → Ollama → offline engine |
| Frontend | React 19, TypeScript, Vite 6, Recharts, lucide-react, code-split pages |
| Typography | **Cormorant Garamond** (display serif) + **Manrope** (UI) + IBM Plex Mono — bundled, work offline |
| Themes | CSS custom properties, `data-theme` light/dark, saved in localStorage, applied before first paint |

Pinned Python versions: `backend/requirements.lock.txt` (torch 2.15.0+cpu, transformers 5.23.0, fastapi 0.163.1).

---

## 4. Folder map

```
FINAL PROJ/
├── memory.md · CHECKLIST.md · README.md · .env.example · .env
├── scripts/  setup.bat · run.bat · run_tests.bat · build_frontend.bat
│             download_models.py · evaluate_emotion.py · diagnose.py
├── models_cache/                      3 Hugging Face models (+ .models_ready marker)
├── backend/
│   ├── requirements.txt / requirements.lock.txt
│   ├── app/
│   │   ├── main.py                    API + per-turn pipeline + serves frontend/dist
│   │   ├── config.py                  paths, env vars, helplines, COMPANION_NAME
│   │   ├── db.py · security.py · demo_data.py
│   │   ├── resources/                 crisis_cases.json (63) · emotion_cases.json (46) · emotion_holdout.json (22)
│   │   └── services/
│   │       ├── language.py            en / hi / hinglish / kn detection (sticky)
│   │       ├── crisis.py              multilingual crisis detector
│   │       ├── escalation.py · fusion.py · prosody.py · safety_filter.py
│   │       ├── models.py              RoBERTa + XLM-EMO + wav2vec2 + fallbacks
│   │       ├── conversation.py        LLM chain, prompt, crisis scripts (4 languages)
│   │       └── offline_engine.py      staged, non-repeating, 4-language reply engine
│   └── tests/  test_crisis · test_fusion_prosody · test_api · test_conversation · test_models
└── frontend/
    ├── src/theme.tsx                  light / dark / system
    ├── src/pages/   Home · Companion · Journal · Toolkit · Counselor · Report · HowItWorks · Settings
    ├── src/components/  Layout (sidebar + top bar + app context) · Orb · Inspector · CrisisCard ·
    │                    Exercises (6) · ConsentModal · ui (Ring, Gauge, CountUp …)
    ├── src/lib/     face.ts (FaceAnalyzer) · faceLogic.ts (pure, tested) · audio.ts · speech.ts
    ├── tests/faceLogic.test.ts
    ├── public/models/                 face-api weights
    └── dist/                          built dashboard served by FastAPI
```

---

## 5. API reference (backend/app/main.py)

| Method & path | Purpose |
|---|---|
| GET `/api/health` | models (text, text_multi, voice), LLM providers, companion name, helplines |
| POST `/api/session` | start session → `session_id`, greeting (in profile language), `companion` |
| POST `/api/chat` | `{session_id, text, face?}` → reply, `language`, tier, fusion, reasons, actions |
| POST `/api/voice` | multipart `session_id, transcript, audio(wav), face?` |
| POST `/api/session/{id}/face` | live face reading → fusion |
| POST `/api/fusion/simulate` · POST `/api/analyze/text` | playground · language analysis |
| GET `/api/dashboard` · GET/POST `/api/checkins` | home + journal |
| GET `/api/alerts` · POST `/api/alerts/{id}` · POST `/api/counselor/request` · POST `/api/trusted-contact/notify` | care team |
| GET/PUT `/api/settings[/key]` · GET `/api/report` | settings, therapist report |
| GET `/api/eval` | crisis set, emotion set + held-out set, safety red-team |
| DELETE `/api/data` · POST `/api/demo/seed` · DELETE `/api/demo` | privacy / sample data |

Interactive docs: `http://localhost:8000/docs`.

---

## 6. Build history

**v1 (Phases 0-6)** – backend, crisis engine, fusion, models, conversation, dashboard, handover. 111 tests.

**v2 (user feedback: "too simple", "loops", "replies in English to Hindi", "face always shows joy", new
name, luxury fonts, dark mode, meaningful avatar):**

1. *Diagnosis* (`scripts/diagnose.py`) reproduced all three bugs and found the causes (§2).
2. *Text emotion*: noisy-OR grouping + label remap; XLM-EMO for Indian languages; lexicon with negation;
   short replies neutral. 60.9 % → 100 % (tuning set), 50 % → 95.5 % (held-out).
3. *Conversation*: offline engine rewritten (4 languages, stages, intents, no repeats); crisis scripts in
   Devanagari Hindi and Kannada, gender-neutral; LLM prompt enforces language and novelty.
4. *Face*: SSD + 68 landmarks, calibration, action units, prior correction, smoothing (§2).
5. *Name*: Aastra → **Anvaya** (`COMPANION_NAME` in `.env` changes it everywhere).
6. *Avatar*: cartoon face → **lotus-of-light orb** that breathes at 6 breaths/min, opens while listening, pulses
   while speaking, changes colour with the conversation's tone.
7. *Frontend redesign*: evergreen + champagne palette, Cormorant Garamond + Manrope, paper grain, staggered
   reveal animations (off with reduced-motion), top bar with theme toggle / alerts / profile, new **Home**
   (wellbeing ring, one-tap mood, "For you", week dots, KPIs, insights), new **Calm toolkit** (6 exercises incl.
   sleep wind-down and three good things), redesigned companion (starters in 4 languages, dictation, hideable
   analysis, calibration overlay), dark mode everywhere, code-split bundle (initial JS 2.1 MB → 0.7 MB).
8. *Verification*: 143 backend tests + face-logic tests pass; every page checked in light and dark mode; Hindi
   conversation and English multi-turn conversation checked through the live server.
   Bugs found & fixed during v2: "I don't know" with apostrophe, Hindi "हाँ"/"नहीं" not recognised (Python `\b`
   fails after Devanagari vowel signs), reflection repeated when pool exhausted, "accha nahi" negation,
   one-word Hindi reply scored as joy, lotus rotating around the wrong origin (SVG transform-origin).

---

## 6b. v3 (user feedback: "asks the same feeling questions", "no casual chat", "Hindi/Kannada speech gets English reply")

**Causes found**
* Voice: after every reply the page switched the browser recogniser to the language of that reply. One English turn →
  next Hindi sentence heard by an English recogniser → English-looking text → English reply.
* Loop: every non-trivial message got reflect + validate + a *feelings* question; DEEPEN/UNSURE pools were all
  "how do you feel / name a feeling". No small-talk path existed.

**Fixes**
1. `services/stt.py` – **Whisper-small** (faster-whisper, int8, offline) detects the spoken language (en / hi / kn, related
   languages grouped, e.g. Telugu→Kannada, Urdu→Hindi). Hindi/English are transcribed by Whisper; Kannada uses the browser
   transcript (Whisper-small is unreliable for Kannada) or asks (in Kannada) to repeat while switching the recogniser to
   Kannada. Reply language = *spoken* language. `/api/voice` takes `browser_locale` + `lang_mode` (`auto|en|hi|kn`).
2. Video mode language selector: **Auto-detect** (default) / English / हिन्दी / ಕನ್ನಡ; listening locale is updated from
   the server's detection, never from the last reply.
3. `services/smalltalk.py` – casual talk in 4 languages: how are you, who are you, are you human, what are you doing,
   jokes, bored, nothing much, compliments, favourites, filler, and interests (cricket, movies, music, food, games, outings).
4. Feeling low → asked **what happened once**; afterwards (or after 2 vague answers) a **choice**: vent / distract /
   calming exercise. Longer messages or every 3rd turn get a reaction without a question; a callback to an earlier
   topic; no more "name a feeling" questions.
5. **"I feel" palette** above the message box (Anxious, Sad, Angry, Lonely, Overwhelmed, Tired, Happy) fills a starter
   phrase in the current conversation language so expressing emotion takes one tap.
6. LLM prompt rewritten: friend first, casual chat welcome, at most one question and not every turn, never keep asking
   about feelings. **Settings → Conversation AI**: paste a free Groq/Gemini key, tested live and saved to `.env`.
   (Offline engine remains the fallback; real conversational quality is best with the free Groq key.)

**Run-time notes:** Whisper adds ~0.5 GB RAM and ~3 s per spoken turn on CPU; `models_cache/whisper-small` (~480 MB)
is downloaded by `setup.bat`. `/api/health` shows `speech` status. Tests: 151 (incl. `test_speech.py`, real Hindi
speech + English-listening browser → Hindi reply).

---

## 7. Moving to another PC

1. Copy the whole `FINAL PROJ` folder (skip `.venv\` and `frontend\node_modules\` if you like; **keep
   `models_cache\`** to avoid a 2 GB download).
2. Install Python 3.12 (64-bit), tick *Add python.exe to PATH*.
3. `scripts\setup.bat` (internet needed for pip packages; ~5-10 min).
4. `scripts\run.bat` → sidebar *System* should show Text · English, Text · Indic and Voice = **ready** (~15 s).
5. Optional: `scripts\run_tests.bat` → `143 passed`.

RAM: the three models use ≈ 2.3 GB. On a 4 GB PC set `MINDBRIDGE_ENABLE_MODELS=0` in `.env` (lexicon + prosody
fallbacks keep everything working, with lower reliability).

---

## 8. Configuration (.env)

```
GROQ_API_KEY=            # free at console.groq.com/keys
GEMINI_API_KEY=          # free at aistudio.google.com/apikey
LLM_PROVIDER=auto        # auto | groq | gemini | ollama | offline
COMPANION_NAME=Anvaya    # rename the companion everywhere
MINDBRIDGE_ENABLE_MODELS=1
```

---

## 9. Troubleshooting

| Problem | Fix |
|---|---|
| Old design / old behaviour | An old `run.bat` window is still running → close it and start `run.bat` again |
| Text · Indic shows *fallback* | `models_cache` incomplete → delete `models_cache\.models_ready`, run `setup.bat` (internet) |
| Face shows "calibrating" forever | Sit facing the camera in good light for ~4 s; press *Recalibrate* |
| Face reading seems off | Press *Recalibrate* with a relaxed face; avoid back-lighting |
| Camera "Permission denied" | Chrome address bar → camera icon → Allow; use `http://localhost` |
| Hindi voice reply silent | Windows: Settings → Time & language → Speech → add Hindi voice (Kannada voices may be unavailable) |
| Port 8000 busy | Close the other run.bat window, or change `--port` in run.bat |
| Want a clean demo | Stop run.bat → delete `backend\data\` → start again |

---

## 10. Demo script for the panel (≈ 9 minutes)

1. **Home** – "Everything here is about the student: wellbeing score, one-tap mood, suggestions computed from their
   own week." Toggle **dark mode** in the top bar.
2. **How it works → Architecture & 7 novelty points.**
3. **Fusion playground** – *Good conditions* → *Dark room* (face weight → 2 %) → *Smiling, sad words*.
4. **How the face is read** – calibration + action-unit table.
5. **Language analysis** – *This exam is killing me* (LOW, idiom) → *मुझे बहुत गुस्सा आ रहा है* (anger, Hindi) →
   *ab jeene ka mann nahi karta* (HIGH, Hinglish).
6. **Run evaluation** – 100 % crisis recall, text-emotion accuracy, held-out 95.5 %, 8/8 unsafe replies blocked.
7. **Talk to Anvaya (text)** – English: "I have exams next week and I can't focus" → "yes" → "what should I do?"
   (no loop, practical tip). Then Hindi: "मुझे अपने रूममेट पर बहुत गुस्सा आ रहा है" → reply in Hindi.
8. **Video mode** – allow camera, hold a relaxed face while it calibrates, then frown / press lips → anger with cues
   "brows lowered · lips pressed"; smile → joy. Speak a sentence; Anvaya answers aloud while the orb pulses.
9. **Crisis** – "sometimes I feel everyone would be better off without me" → safety mode, helplines, trusted contact.
10. **Counsellor console** – alert with reasons → note → Resolve. **Calm toolkit**, **Therapist report** → Print.

### Likely viva questions

* **Why did the face always show joy before, and what did you change?** Expression CNNs trained on FER-style data
  are biased to neutral/happy, and some resting faces look "happy" to them. We now calibrate to each person's
  resting face and add geometric Facial Action Units; the unit tests show the exact failure case being fixed.
* **How accurate is the text emotion?** 95.5 % on a held-out set we never tuned on (was 50 %); Hindi/Hinglish/Kannada
  went from 0 % to correct because of the multilingual XLM-RoBERTa model.
* **Why noisy-OR?** Summing 28 independent sigmoid scores let many weak positive labels outvote one strong emotion;
  noisy-OR combines evidence probabilistically and cannot exceed 1.
* **Why not let the LLM detect crises?** Non-deterministic and hard to audit; rules are tested (63 cases, 100 % recall).
* **Why the name Anvaya and the lotus?** Anvaya = "connection"; the lotus is growth through difficulty; the orb
  breathes at the resonance rate (6/min) so it gently paces the user. A faceless form avoids the uncanny valley.
* **Limitations?** See §11.

---

## 11. Known limitations (be honest)

* Camera and microphone could not be exercised by the automated test browser (it blocks devices). Face logic is
  unit-tested and the face models were verified to load and run (WebGL). **Test video mode once in Chrome.**
* Groq/Gemini integration is written against their public REST APIs but was not exercised without a key.
* Trusted-contact SMS/email is **simulated** (outbox in the counsellor console).
* Hindi/Kannada sentences and lexicons should be reviewed by native speakers / clinicians; test sets are small.
* Single-user prototype (no login); counsellor view is a role, not a separate account.
* Held-out miss: "Everyone in my group got selected except me" → neutral (implicit sadness is hard without context).
