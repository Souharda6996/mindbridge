"""Shows multi-turn offline conversations in each language (checks for loops & language match)."""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from backend.app import config  # noqa: E402,F401
from backend.app.services import language, offline_engine  # noqa: E402

CONVERSATIONS = {
    "English": [("my exams are next week", "fear", 0.5), ("I keep studying but nothing sticks", "fear", 0.55),
                ("yes", "neutral", 0.3), ("I don't know", "neutral", 0.3), ("what should I do?", "fear", 0.5),
                ("exams are just too much", "fear", 0.6), ("no", "neutral", 0.3), ("I'm feeling a bit better now", "joy", 0.2)],
    "Hindi": [("मुझे परीक्षा की बहुत चिंता हो रही है", "fear", 0.6), ("हाँ", "neutral", 0.3),
              ("मैं पढ़ता हूँ पर कुछ याद नहीं रहता", "sadness", 0.55), ("पता नहीं", "neutral", 0.3),
              ("मैं क्या करूँ?", "fear", 0.5), ("नहीं", "neutral", 0.3)],
    "Hinglish": [("yaar mujhe bahut gussa aa raha hai roommate pe", "anger", 0.5), ("woh kabhi nahi sunta", "anger", 0.5),
                 ("haan", "neutral", 0.3), ("kya karun ab", "anger", 0.5)],
    "Kannada": [("ನನಗೆ ತುಂಬಾ ಒಂಟಿತನ ಅನ್ನಿಸುತ್ತಿದೆ", "sadness", 0.6), ("ಹೌದು", "neutral", 0.3), ("ಗೊತ್ತಿಲ್ಲ", "neutral", 0.3)],
}

for title, turns in CONVERSATIONS.items():
    print(f"\n=================== {title} ===================")
    mem, lang, seen = {}, None, set()
    for text, emo, d in turns:
        lang = language.detect(text, lang)
        r = offline_engine.respond(text, emo, d, "LOW", mem, lang)
        sentences = [s.strip() for s in r["reply"].replace("?", "?|").replace(".", ".|").replace("।", "।|").split("|") if s.strip()]
        repeats = [s for s in sentences if s in seen]
        seen.update(sentences)
        print(f"> [{lang}] {text}")
        print(f"< {r['reply']}" + (f"   [exercise: {r['exercise']}]" if r["exercise"] else "")
              + (f"   !! REPEATED: {repeats}" if repeats else ""))
