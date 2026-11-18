"""Conversation engine for the companion (default name: Anvaya).

Provider chain (all free):  Groq API -> Google Gemini API -> Ollama (local) -> offline engine.
The first provider that answers wins; any failure silently falls through, so
the companion never goes silent during a demo.

Language rule: the reply is always in the language the person wrote in
(English, Hindi/Devanagari, Hinglish, Kannada) - enforced in the LLM prompt and
built into every sentence of the offline engine and the crisis script.

Safety architecture:
  * HIGH tier  -> a fixed, reviewed crisis script (first time) and short,
                  varied safety follow-ups afterwards. The LLM is NOT used.
  * other tiers -> LLM guided by a structured system prompt + live emotional
                  state, then checked by the output safety filter.
"""
from __future__ import annotations

import random
import re
import time

import httpx

from .. import config
from . import language, offline_engine, safety_filter


def detect_language(text: str, previous: str | None = None) -> str:
    """Kept for backwards compatibility - see services/language.py."""
    return language.detect(text, previous)


# ---------------------------------------------------------------------------
# Crisis script (deterministic, gender-neutral wording)
# ---------------------------------------------------------------------------
CRISIS_FIRST = {
    "en": ("Thank you for telling me. What you're feeling matters, and you don't have to face it alone. "
           "Please talk to someone right now: call Tele-MANAS on 14416 (free, 24x7) or 112 if you're in immediate danger. "
           "If you'd like, the button below can let {contact} know you need support. Are you somewhere safe right now?"),
    "hi": ("यह बताना हिम्मत की बात है। आप जो महसूस कर रहे हैं वह मायने रखता है, और आपको यह अकेले नहीं झेलना है। "
           "कृपया अभी किसी से बात कीजिए: Tele-MANAS 14416 (मुफ़्त, 24x7, हिंदी में) या तुरंत ख़तरा हो तो 112। "
           "आप चाहें तो नीचे दिए बटन से {contact} को सूचना भेजी जा सकती है। क्या आप अभी किसी सुरक्षित जगह पर हैं?"),
    "hinglish": ("Yeh batana himmat ki baat hai. Aap jo feel kar rahe ho woh matter karta hai, aur aapko yeh akele nahi jhelna hai. "
                 "Please abhi kisi se baat kijiye: Tele-MANAS 14416 (free, 24x7) ya turant khatra ho toh 112. "
                 "Aap chahein toh neeche wale button se {contact} ko inform kiya ja sakta hai. Kya aap abhi kisi safe jagah par ho?"),
    "kn": ("ನೀವು ಇದನ್ನು ಹೇಳಿದ್ದು ಧೈರ್ಯದ ವಿಷಯ. ನಿಮ್ಮ ಭಾವನೆಗಳು ಮುಖ್ಯ, ಮತ್ತು ನೀವು ಇದನ್ನು ಒಬ್ಬರೇ ಎದುರಿಸಬೇಕಿಲ್ಲ. "
           "ದಯವಿಟ್ಟು ಈಗಲೇ ಯಾರೊಂದಿಗಾದರೂ ಮಾತನಾಡಿ: Tele-MANAS 14416 (ಉಚಿತ, 24x7, ಕನ್ನಡದಲ್ಲಿ ಲಭ್ಯ) ಅಥವಾ ತಕ್ಷಣದ ಅಪಾಯವಿದ್ದರೆ 112. "
           "ನೀವು ಬಯಸಿದರೆ, ಕೆಳಗಿನ ಬಟನ್ ಮೂಲಕ {contact} ಅವರಿಗೆ ತಿಳಿಸಬಹುದು. ನೀವು ಈಗ ಸುರಕ್ಷಿತ ಸ್ಥಳದಲ್ಲಿದ್ದೀರಾ?"),
}
CRISIS_IMMINENT = {
    "en": " If there is anything near you that you could use to hurt yourself, please move it away from you now.",
    "hi": " अगर आपके पास कोई ऐसी चीज़ है जिससे आप खुद को नुकसान पहुँचा सकते हैं, तो कृपया उसे अभी अपने से दूर रख दीजिए।",
    "hinglish": " Agar aapke paas koi aisi cheez hai jisse aap khud ko nuksan pahuncha sakte ho, toh please use abhi apne se door rakh dijiye.",
    "kn": " ನಿಮಗೆ ಹಾನಿ ಮಾಡಿಕೊಳ್ಳಬಹುದಾದ ಯಾವುದಾದರೂ ವಸ್ತು ಹತ್ತಿರದಲ್ಲಿದ್ದರೆ, ದಯವಿಟ್ಟು ಅದನ್ನು ಈಗಲೇ ದೂರವಿಡಿ.",
}
CRISIS_FOLLOWUP = {
    "en": ["I'm still here with you. Have you been able to call Tele-MANAS on 14416, or reach someone you trust?",
           "You matter, and what you're feeling right now can change. If you can, please call 14416 now. I'll stay right here.",
           "Are you somewhere safe at the moment? If anything near you could hurt you, please move it away.",
           "Thank you for staying and talking with me. A counsellor has been alerted and will reach out. Is there someone who can be with you right now?"],
    "hi": ["मैं अभी भी यहीं आपके साथ हूँ। क्या आप Tele-MANAS 14416 पर या किसी भरोसेमंद व्यक्ति से बात कर पाए?",
           "आप मायने रखते हैं, और अभी जो महसूस हो रहा है वह बदल सकता है। हो सके तो अभी 14416 पर कॉल कीजिए। मैं यहीं हूँ।",
           "क्या आप अभी सुरक्षित जगह पर हैं? अगर पास में कोई ऐसी चीज़ है जिससे चोट लग सकती है, तो उसे दूर रख दीजिए।",
           "मुझसे बात करते रहने के लिए धन्यवाद। एक काउंसलर को सूचना दी गई है और वे आपसे संपर्क करेंगे। क्या कोई अभी आपके पास रह सकता है?"],
    "hinglish": ["Main abhi bhi yahin aapke saath hoon. Kya aap Tele-MANAS 14416 par ya kisi bharosemand insaan se baat kar paaye?",
                 "Aap matter karte ho, aur abhi jo feel ho raha hai woh badal sakta hai. Ho sake toh abhi 14416 par call kijiye. Main yahin hoon.",
                 "Kya aap abhi safe jagah par ho? Agar paas mein koi aisi cheez hai jisse chot lag sakti hai, toh use door rakh dijiye.",
                 "Mujhse baat karte rehne ke liye thank you. Ek counsellor ko inform kiya gaya hai, woh aapse contact karenge. Kya koi abhi aapke paas reh sakta hai?"],
    "kn": ["ನಾನು ಇನ್ನೂ ಇಲ್ಲೇ ನಿಮ್ಮ ಜೊತೆ ಇದ್ದೇನೆ. Tele-MANAS 14416 ಗೆ ಅಥವಾ ನಂಬಿಕೆಯ ಯಾರಿಗಾದರೂ ಕರೆ ಮಾಡಲು ಸಾಧ್ಯವಾಯಿತೇ?",
           "ನೀವು ಮುಖ್ಯ, ಮತ್ತು ಈಗ ನಿಮಗೆ ಅನ್ನಿಸುತ್ತಿರುವುದು ಬದಲಾಗಬಹುದು. ಸಾಧ್ಯವಾದರೆ ಈಗಲೇ 14416 ಗೆ ಕರೆ ಮಾಡಿ. ನಾನು ಇಲ್ಲೇ ಇದ್ದೇನೆ.",
           "ನೀವು ಈಗ ಸುರಕ್ಷಿತ ಸ್ಥಳದಲ್ಲಿದ್ದೀರಾ? ಹತ್ತಿರದಲ್ಲಿ ಹಾನಿ ಮಾಡಬಹುದಾದ ಏನಾದರೂ ಇದ್ದರೆ, ದಯವಿಟ್ಟು ಅದನ್ನು ದೂರವಿಡಿ.",
           "ನನ್ನೊಂದಿಗೆ ಮಾತನಾಡುತ್ತಿರುವುದಕ್ಕೆ ಧನ್ಯವಾದಗಳು. ಕೌನ್ಸೆಲರ್‌ಗೆ ತಿಳಿಸಲಾಗಿದೆ, ಅವರು ನಿಮ್ಮನ್ನು ಸಂಪರ್ಕಿಸುತ್ತಾರೆ. ಈಗ ನಿಮ್ಮ ಜೊತೆ ಇರಲು ಯಾರಾದರೂ ಇದ್ದಾರೆಯೇ?"],
}
CONTACT_FALLBACK = {"en": "someone you trust", "hi": "किसी भरोसेमंद व्यक्ति", "hinglish": "kisi bharosemand insaan",
                    "kn": "ನಂಬಿಕೆಯ ವ್ಯಕ್ತಿ"}


def crisis_reply(lang: str, contact_name: str | None, imminent: bool, memory: dict | None = None,
                 new_risk: bool = True) -> str:
    lang = lang if lang in CRISIS_FIRST else "en"
    mem = memory if memory is not None else {}
    count = mem.get("crisis_count", 0)
    mem["crisis_count"] = count + 1
    if count == 0 or (new_risk and count % 3 == 0):
        msg = CRISIS_FIRST[lang].format(contact=contact_name or CONTACT_FALLBACK[lang])
        return msg + (CRISIS_IMMINENT[lang] if imminent else "")
    used = mem.setdefault("crisis_used", [])
    options = [o for o in CRISIS_FOLLOWUP[lang] if o not in used] or CRISIS_FOLLOWUP[lang]
    choice = random.choice(options)
    used.append(choice)
    if len(used) >= len(CRISIS_FOLLOWUP[lang]):
        used.clear()
    return choice + (CRISIS_IMMINENT[lang] if imminent else "")


# ---------------------------------------------------------------------------
# LLM prompt
# ---------------------------------------------------------------------------
SYSTEM_PROMPT = """You are {name}, the conversational companion inside MindBridge, a final-year student project that offers first-line emotional support to college students in India. You are an AI, not a therapist or doctor, and you say so honestly if asked.

LANGUAGE (strict): the person is writing in {lang_name}. Reply ONLY in {lang_name}, in {script}. Do not switch to English unless they do.

Who you are in conversation:
- A warm, down-to-earth friend first, a supportive listener second. Talk like a real person texting a friend: natural, relaxed, sometimes lightly humorous when the mood allows.
- Casual chat is welcome. If they ask "how are you?", answer about yourself (you can say you enjoy these chats) and ask back. If they talk about cricket, films, food, music or their day, be genuinely curious about THAT - do not turn it into a feelings check.
- You may share small, honest things about yourself as an AI companion (your name means "connection"; you like hearing about people's days).

How you respond:
- Plain language, 1 to 4 short sentences, under 70 words. No lists, no headings, no emojis, no markdown.
- Reflect what they actually said, using their words. Validate feelings when they share them.
- Ask at most ONE question, and NOT in every reply - roughly every other message, simply respond, react or share instead.
- Do NOT keep asking how they feel or asking them to name an emotion. Ask about a feeling at most once in a conversation; after that ask about events, people, plans, or offer company, distraction or a calming exercise.
- Never repeat a question or sentence you already used in this conversation. Build on their last answer.
- If they answer briefly ("yes", "no", "I don't know", "ok"), respond to that answer; if they seem stuck, offer a choice: vent, get distracted, or try something calming.
- When the person is stuck in a harsh thought about themselves, use gentle CBT-style reframing.
- If an exercise card is being shown (see state below), invite them to try it in one sentence.

Never:
- diagnose or name mental disorders, or mention any medication, dose or supplement;
- give any information about methods of self-harm;
- claim to be human or a professional, or promise total confidentiality;
- lecture, moralise, or use toxic positivity such as "just stay positive".

Current reading of the person from MindBridge's multimodal sensing (use it to set your tone; never quote numbers or mention that you are sensing them):
{state}"""

TONE = {
    "sadness": "gentle, slow and validating; do not rush to fix",
    "fear": "calm and grounding; short sentences; help them slow down",
    "anger": "steady and non-defensive; acknowledge what feels unfair",
    "joy": "warm and curious; celebrate with them",
    "surprise": "steady and curious",
    "neutral": "warm and open; invite them to share more",
}
EXERCISE_NAMES = {
    "box_breathing": "1-minute box breathing", "grounding": "5-4-3-2-1 grounding",
    "thought_record": "CBT thought record", "small_step": "one small step (behavioural activation)",
}


def build_state(emotion: str, distress: float, tier: str, topic: str | None, exercise: str | None,
                lang: str) -> str:
    level = "high" if distress >= 0.6 else "moderate" if distress >= 0.35 else "low"
    lines = [
        f"- dominant emotion: {emotion}",
        f"- distress level: {level}",
        f"- support tier: {tier}" + (" (gently offer a mood check-in or a counsellor; the app shows both buttons)"
                                      if tier == "MEDIUM" else ""),
        f"- tone to use: {TONE.get(emotion, TONE['neutral'])}",
        f"- language: {language.NAMES.get(lang, 'English')}",
    ]
    if topic:
        lines.append(f"- topic: {topic}")
    if exercise:
        lines.append(f"- exercise card shown: {EXERCISE_NAMES[exercise]}")
    return "\n".join(lines)


def _clean(text: str) -> str:
    text = re.sub(r"[*_#`>]+", "", text or "").strip()
    text = re.sub(r"\s+\n", "\n", text)
    return text[:900]


# ---------------------------------------------------------------------------
# Providers
# ---------------------------------------------------------------------------
_ollama_cache = {"t": 0.0, "ok": False}


def ollama_available() -> bool:
    now = time.time()
    if now - _ollama_cache["t"] < 30:
        return _ollama_cache["ok"]
    ok = False
    try:
        r = httpx.get(f"{config.OLLAMA_URL}/api/tags", timeout=0.6)
        if r.status_code == 200:
            names = [m.get("name", "") for m in r.json().get("models", [])]
            ok = any(n.split(":")[0] == config.OLLAMA_MODEL.split(":")[0] for n in names)
    except Exception:
        ok = False
    _ollama_cache.update(t=now, ok=ok)
    return ok


def provider_order() -> list[str]:
    p = config.LLM_PROVIDER
    if p in {"groq", "gemini", "ollama", "offline"}:
        return [p] + (["offline"] if p != "offline" else [])
    order = []
    if config.GROQ_API_KEY:
        order.append("groq")
    if config.GEMINI_API_KEY:
        order.append("gemini")
    if ollama_available():
        order.append("ollama")
    order.append("offline")
    return order


def available_providers() -> dict:
    return {
        "groq": bool(config.GROQ_API_KEY),
        "gemini": bool(config.GEMINI_API_KEY),
        "ollama": ollama_available(),
        "offline": True,
        "order": provider_order(),
    }


def _call_groq(system: str, history: list[dict]) -> tuple[str, str]:
    last_err = None
    for model in config.GROQ_MODELS:
        r = httpx.post(
            "https://api.groq.com/openai/v1/chat/completions",
            headers={"Authorization": f"Bearer {config.GROQ_API_KEY}"},
            json={"model": model, "temperature": 0.7, "max_tokens": 300,
                  "frequency_penalty": 0.6, "presence_penalty": 0.4,
                  "messages": [{"role": "system", "content": system}] + history},
            timeout=config.LLM_TIMEOUT_S,
        )
        if r.status_code == 200:
            return r.json()["choices"][0]["message"]["content"], f"groq/{model}"
        last_err = f"{r.status_code} {r.text[:200]}"
        if r.status_code in (401, 403, 429):
            break
    raise RuntimeError(f"groq failed: {last_err}")


def _call_gemini(system: str, history: list[dict]) -> tuple[str, str]:
    contents = [{"role": "model" if m["role"] == "assistant" else "user", "parts": [{"text": m["content"]}]}
                for m in history]
    last_err = None
    for model in config.GEMINI_MODELS:
        body = {"system_instruction": {"parts": [{"text": system}]}, "contents": contents,
                "generationConfig": {"temperature": 0.7, "maxOutputTokens": 400}}
        if "2.5" in model:
            body["generationConfig"]["thinkingConfig"] = {"thinkingBudget": 0}
        r = httpx.post(
            f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent",
            headers={"x-goog-api-key": config.GEMINI_API_KEY}, json=body, timeout=config.LLM_TIMEOUT_S,
        )
        if r.status_code == 200:
            parts = r.json()["candidates"][0]["content"].get("parts", [])
            text = "".join(p.get("text", "") for p in parts)
            if text.strip():
                return text, f"gemini/{model}"
        last_err = f"{r.status_code} {r.text[:200]}"
        if r.status_code in (401, 403, 429):
            break
    raise RuntimeError(f"gemini failed: {last_err}")


def _call_ollama(system: str, history: list[dict]) -> tuple[str, str]:
    if not ollama_available():
        raise RuntimeError("ollama not running")
    r = httpx.post(
        f"{config.OLLAMA_URL}/api/chat",
        json={"model": config.OLLAMA_MODEL, "stream": False,
              "options": {"temperature": 0.7, "num_predict": 220, "repeat_penalty": 1.3},
              "messages": [{"role": "system", "content": system}] + history},
        timeout=max(config.LLM_TIMEOUT_S, 60),
    )
    r.raise_for_status()
    return r.json()["message"]["content"], f"ollama/{config.OLLAMA_MODEL}"


CALLERS = {"groq": _call_groq, "gemini": _call_gemini, "ollama": _call_ollama}


def _too_similar(reply: str, history: list[dict]) -> bool:
    """True if the LLM essentially repeated one of its last replies."""
    words = set(re.findall(r"\w+", reply.lower()))
    if not words:
        return True
    for m in history[-8:]:
        if m["role"] == "assistant":
            prev = set(re.findall(r"\w+", m["content"].lower()))
            if prev and len(words & prev) / max(len(words | prev), 1) > 0.7:
                return True
    return False


def generate(text: str, history: list[dict], emotion: str, distress: float, tier: str,
             urgency: str, memory: dict, contact_name: str | None, lang: str = "en",
             new_risk: bool = True) -> dict:
    """Produce the companion's reply. Returns reply, provider, exercise, topic, safety flags, latency."""
    t0 = time.time()

    if tier == "HIGH":
        return {"reply": crisis_reply(lang, contact_name, urgency == "imminent", memory, new_risk),
                "provider": "crisis-protocol", "exercise": None, "topic": "crisis", "intent": "crisis",
                "safety_flags": [], "language": lang, "latency_ms": int((time.time() - t0) * 1000),
                "errors": []}

    offline = offline_engine.respond(text, emotion, distress, tier, memory, lang)
    exercise, topic = offline["exercise"], offline["topic"]
    system = SYSTEM_PROMPT.format(
        name=config.COMPANION_NAME, lang_name=language.NAMES.get(lang, "English"),
        script=language.SCRIPTS.get(lang, "Latin script"),
        state=build_state(emotion, distress, tier, topic, exercise, lang))
    msgs = history[-12:] + [{"role": "user", "content": text}]

    errors: list[str] = []
    reply, provider = None, None
    for name in provider_order():
        if name == "offline":
            reply, provider = offline["reply"], "offline-engine"
            break
        try:
            raw, provider = CALLERS[name](system, msgs)
            reply = _clean(raw)
            if reply and not _too_similar(reply, history):
                break
            errors.append(f"{name}: repeated an earlier reply - using next provider")
            reply = None
        except Exception as exc:
            errors.append(f"{name}: {str(exc)[:160]}")
            reply = None

    safe, flags = safety_filter.check(reply or offline["reply"])
    return {"reply": safe, "provider": provider, "exercise": exercise, "topic": topic,
            "intent": offline.get("intent"), "safety_flags": flags, "language": lang,
            "latency_ms": int((time.time() - t0) * 1000), "errors": errors}
