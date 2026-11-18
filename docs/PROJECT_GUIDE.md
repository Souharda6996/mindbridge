# MindBridge — Project Guide (plain-language explanation)

*A multimodal AI companion for emotional support and distress-risk triage — final-year project.*

---

## 1. The idea in one minute

Many students feel low, anxious or overwhelmed but never talk to anyone: counsellors are few, therapy is costly, and there is stigma.
**MindBridge** is a private, always-available *first step*. A student chats (typing or by video/voice) with a companion called
**Anvaya** (Sanskrit for *connection*). While they talk, the system quietly estimates how distressed they seem, from **three
signals**: their **face**, their **voice** and their **words**. If something serious appears, it does not try to handle it alone:
it shows helplines (**Tele-MANAS 14416**, **112**), can inform a trusted contact, and alerts a human **counsellor**.

> MindBridge is a *bridge* to professional care, not a replacement. It never diagnoses and never gives medical advice.

---

## 2. What the user sees (the 8 pages)

| Page | What it does |
|---|---|
| **Home** | Greeting, wellbeing score (0-100), one-tap mood log, "For you" suggestions built from the user's own week, 30-day charts, insights |
| **Talk to Anvaya** | Text chat or video mode. A side panel shows *live analysis*: distress gauge, which signal is trusted how much, emotions, reasons |
| **Mood journal** | 30-second daily check-in (mood, sleep, energy, anxiety, tags, note); 5-week heat-map |
| **Calm toolkit** | 6 exercises: box breathing, 5-4-3-2-1 grounding, CBT thought record, one small step, sleep wind-down, three good things |
| **Counsellor console** | Live alerts with the *reasons*; acknowledge / add a note / resolve |
| **Therapist report** | Printable summary the student can share with a therapist |
| **How it works** | Panel-friendly explainer: architecture, novelty, fusion playground, live evaluation |
| **Privacy & settings** | Light/dark theme, consent switches, trusted contact, free AI key, incognito, **delete all data** |

Anvaya's visual form is a **lotus of light** that breathes at 6 breaths per minute (the calming "resonance" pace), opens when
listening and pulses when speaking. It is deliberately faceless, to avoid an uncanny cartoon face.

---

## 3. How one message is understood (the pipeline)

```
  FACE (browser)  ─┐
  VOICE (server)  ─┼─►  FUSION  ─►  distress score + confidence ─┐
  TEXT  (server)  ─┘                                             ├─► ESCALATION ─► LOW / MEDIUM / HIGH
  CRISIS RULES (words) ──────────────────────────────────────────┘          │
                                                                            ▼
                               reply (in the user's language) + exercises + alerts
```

### 3.1 Face — on the user's device
* Runs in the browser with TensorFlow.js (**video never leaves the device**; only 7 emotion probabilities and a reliability score are sent).
* Steps: detect face → 68 landmarks → expression network → **calibrate to the person's resting face (first ~4 s)** → add **Facial Action Units**
  (e.g. lowered brows + pressed lips = anger; lip-corner pull = smile) → smooth over time.
* Why: generic expression networks are biased to "neutral/happy". Calibration + action units fixed the "always shows joy" problem.

### 3.2 Voice
* A wav2vec2 emotion model plus hand-made features that psychology links to low mood: **long pauses, flat pitch, low energy, trembling pitch, slow speech**.
* **Whisper** (free, offline) detects *which language was spoken* (English / Hindi / Kannada) and transcribes Hindi and English.

### 3.3 Text
* English: RoBERTa trained on GoEmotions (28 emotions) with a probabilistic ("noisy-OR") way of grouping them into 6 emotions.
* Hindi, Hinglish, Kannada: multilingual XLM-RoBERTa (XLM-EMO) + a small emotion-word lexicon that understands negation ("accha nahi lag raha" = sad).

### 3.4 Fusion — the main novelty
Each signal *m* gets a distress score `d` and a **reliability** `r` (is the camera dark? is the room noisy? was the message one word?):

```
weight  w = trust × reliability × freshness        fused distress  D = Σ(w·d) / Σw
confidence C = Σw / Σtrust                         smoothed over time so one frown does not spike it
```
So if the camera is covered, the face's weight drops to ~0 automatically and voice + text carry the decision.
(Try it on **How it works → Fusion playground**.)

### 3.5 Crisis detection — deterministic on purpose
* Rules in **English, Hinglish, Hindi and Kannada**, graded like the clinical C-SSRS scale: 0 none · 1 hopelessness/burden · 2 passive death wish · 3 active ideation/self-harm · 4 plan/method/timeframe.
* Handles **negation** ("I would never…" → check in gently) and **idioms** ("this exam is killing me" → not a crisis).
* The final risk is the **maximum** over all rules, never an average: one clear statement is enough.
* Why not let the AI decide? An AI is not predictable or auditable; safety logic must be testable. The AI is **switched off** in HIGH tier.

### 3.6 Escalation tiers

| Tier | Triggers | What happens |
|---|---|---|
| **LOW** | nothing worrying | normal supportive chat |
| **MEDIUM** | hopelessness words, or high distress for several turns | gentler tone, check-in + "talk to a counsellor" buttons, non-urgent alert |
| **HIGH** | passive death wish, self-harm, plan | fixed safety script, helplines, trusted-contact offer, urgent counsellor alert; **stays HIGH until a counsellor resolves it** |

Every alert carries **plain-language reasons** (the phrase, the vocal pattern, the trend), so a human sees *why*.

---

## 4. How Anvaya talks

* **Replies in the language you used** (English, Hindi, Hinglish, Kannada); spoken language is auto-detected in video mode.
* **Never repeats** a sentence in a conversation, understands "yes / no / I don't know / what should I do?".
* **Casual, human-style chat**: answers "how are you?" about itself, jokes, interests (cricket, films, music…).
* When someone feels low it asks **what happened once**, then offers a choice (talk it out / get distracted / calming exercise) instead of endless feeling questions.
* Dialogue engine order (all free): **Groq → Gemini → Ollama (local) → built-in offline engine**. Paste a free Groq key in Settings for the most natural replies; without a key the offline engine still works.
* Every reply passes a **safety filter** (blocks diagnoses, medication/dosage, self-harm methods, claiming to be a human professional).

---

## 5. Privacy & ethics
* Video is analysed **in the browser**; audio is analysed in memory; nothing is recorded by default.
* Stored text is **encrypted** (Fernet: AES-128 + HMAC). Deleting data rotates the key, so old data becomes unreadable.
* Consent switches for camera, microphone, history, counsellor alerts, trusted-contact alerts; **incognito mode**; **delete-all** button.
* Trusted-contact messages never include conversation content (and are *simulated* in this prototype).
* Honest limits: emotion models are trained on acted/Western data; Hindi/Kannada word lists need native-speaker and clinical review; the test sets are small.

---

## 6. Technology

| Part | Choice |
|---|---|
| Backend | Python 3.12, FastAPI, SQLite |
| AI models (all free, CPU, offline) | RoBERTa-GoEmotions, XLM-EMO, wav2vec2-SUPERB-ER, Whisper-small, face-api.js (SSD-MobileNet + landmarks + expression CNN) |
| Frontend | React 19 + TypeScript + Vite; Recharts; fonts Cormorant Garamond + Manrope; light & dark themes |
| Speech | Browser Web Speech API + Whisper |
| Tests | pytest (151 tests) + a Node test for face logic |

---

## 7. Evidence it works (all re-runnable)

| Measure | Result |
|---|---|
| High-risk crisis recall (63 labelled messages, 4 languages) | **100 %** (32/32) |
| Crisis precision / idiom traps | 100 % / all 13 stay LOW |
| Text-emotion accuracy, tuning set (46 sentences) | 60.9 % → **100 %** (Hindi/Hinglish/Kannada 0 % → 100 %) |
| Text-emotion accuracy, **held-out** set (never tuned on) | 50 % → **95.5 %** |
| Unsafe replies blocked by the safety filter | 8 / 8 (safe replies all passed) |
| Spoken-language detection on test speech | English 99 %, Hindi 97-99 %, Kannada 99 % |
| Face logic unit tests | smile→happy, brows+lips→angry, resting face→neutral, "always joy" case fixed |
| Automated tests | **151 pass** |

Run them: `scripts\run_tests.bat`, `scripts\evaluate_emotion.py`, or the **How it works → Run evaluation** button.

---

## 8. Run it

1. Install Python 3.12 (tick *Add to PATH*).
2. Double-click `scripts\setup.bat` once (downloads ~2.5 GB of free AI models).
3. Double-click `scripts\run.bat` → open `http://localhost:8000` in Chrome or Edge.

More detail (folder map, API list, troubleshooting, demo script, viva questions): [`memory.md`](../memory.md). Verification record: [`CHECKLIST.md`](../CHECKLIST.md).

---

## 9. Limitations and future work
* Camera/microphone paths were not exercised by automated tests (browser blocks devices); verify once on a real laptop.
* Cloud AI (if enabled) sees message text; offline mode does not.
* Future: integrate real campus counselling/Tele-MANAS workflows, fine-tune a risk classifier on clinically annotated Indian-language data, learn fusion weights from data, mobile app, and a clinical pilot with ethics approval.

> *MindBridge is a student research prototype. It is not a medical device and not a substitute for professional care. In an emergency call 112; for free, confidential support call Tele-MANAS 14416.*
