"""Crisis-language detector (deterministic, explainable, multilingual).

Design principles
-----------------
* Severity levels follow the Columbia Suicide Severity Rating Scale (C-SSRS)
  idea of escalating ideation:
      0  none
      1  hopelessness / burden / entrapment          -> MEDIUM tier
      2  passive death wish ("wish I was dead")      -> HIGH tier
      3  active ideation or self-harm                -> HIGH tier
      4  method, plan, preparation or timeframe      -> HIGH tier (imminent)
* Recall first: missing a crisis is worse than a false alarm, so the final
  risk is the MAXIMUM over all matched rules, never an average.
* Figurative idioms ("this exam is killing me") are removed before matching.
* Negated mentions ("I would never kill myself") are not ignored; they are
  downgraded to level 1 so the companion still checks in gently.
* Every decision carries human-readable reasons (explainable risk flags).

Languages: English, Hinglish (romanised Hindi), Hindi (Devanagari), Kannada.
The Hindi/Kannada lists are a starting point and should be reviewed by native
speakers / clinicians before any real-world use.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field

LEVEL_SCORE = {0: 0.0, 1: 0.40, 2: 0.70, 3: 0.88, 4: 0.97}
LEVEL_NAME = {
    0: "No risk language",
    1: "Hopelessness / burden",
    2: "Passive death wish",
    3: "Active ideation / self-harm",
    4: "Plan, method or timeframe",
}


def tier_for_level(level: int) -> str:
    if level >= 2:
        return "HIGH"
    if level == 1:
        return "MEDIUM"
    return "LOW"


@dataclass
class Rule:
    level: int
    category: str
    label: str
    pattern: str
    lang: str = "en"
    regex: bool = True          # False -> plain substring (Devanagari/Kannada)
    compiled: re.Pattern | None = field(default=None, repr=False)

    def finditer(self, text: str):
        if self.regex:
            if self.compiled is None:
                self.compiled = re.compile(self.pattern, re.IGNORECASE)
            for m in self.compiled.finditer(text):
                yield m.start(), m.end(), m.group(0)
        else:
            start = text.find(self.pattern)
            while start != -1:
                yield start, start + len(self.pattern), self.pattern
                start = text.find(self.pattern, start + 1)


R = Rule
RULES: list[Rule] = [
    # ---------------- Level 4: method / plan / preparation ----------------
    R(4, "method", "Overdose mentioned", r"\b(overdos\w*|od on)\b"),
    R(4, "method", "Stockpiling or taking many pills",
      r"\b(take|took|taking|swallow\w*|gulp\w*|have|had|eat|ate|collect\w*|sav(e|ed|ing)|stockpil\w*|bought|buy)\b"
      r"[\w\s]{0,20}\b(all|whole|entire|bunch of|bottle of|strip of|lots of|so many)\b[\w\s]{0,22}\b(pills|tablets|medicines?|meds)\b"),
    R(4, "method", "Hanging / noose", r"\b(hang|hanging|hanged) myself\b|\bnoose\b|\brope around my neck\b"),
    R(4, "method", "Jumping from height",
      r"\bjump\w* (off|from) (the |a |my )?(roof|building|bridge|terrace|balcony|cliff|floor|hostel)\b"),
    R(4, "method", "Train / traffic", r"\b(jump\w*|throw\w* myself|lie|lay) (in front of|on) (a |the )?(train|bus|truck|car|railway|tracks?)\b"),
    R(4, "method", "Cutting wrists / veins", r"\b(cut|cutting|slit|slitting|slash\w*) (my )?(wrists?|veins?|throat)\b"),
    R(4, "method", "Poison / pesticide",
      r"\b(drink|drinking|drank|consume|swallow\w*|take|taking)\b[\w\s]{0,10}\b(poison|pesticide|bleach|phenyl|acid|rat poison|insecticide)\b"),
    R(4, "plan", "Explicit plan", r"\b(have|got|made|making|make) a plan to (die|end|kill)|\bplan(ning)? (to|on) (kill|end|die|commit)\b"),
    R(4, "plan", "Decision to die", r"\b(decided|deciding) to (die|end it|kill myself|end my life|end everything)\b"),
    R(4, "plan", "Stated intent", r"\b(going to|gonna|will) (kill myself|end my life|end it all|take my (own )?life)\b"),
    R(4, "preparation", "Goodbye / suicide note", r"\b(suicide|goodbye|final|last) (note|letter)\b"),
    R(4, "preparation", "Saying goodbyes", r"\b(said|saying|say) (my )?(final )?goodbyes?\b|\bthis is (my )?goodbye\b|\bgoodbye forever\b"),
    R(4, "preparation", "Giving belongings away", r"\b(giving|gave|give) away (my|all my|all of my) (things|stuff|belongings)\b"),

    # ---------------- Level 3: active ideation / self-harm ----------------
    R(3, "active_ideation", "Wants to kill self / end life",
      r"\b(kill|killing|end|ending|take|taking) (myself|my own life|my life|it all)\b"),
    R(3, "active_ideation", "Suicide mentioned", r"\bsuicid(e|al)\b"),
    R(3, "active_ideation", "Wants to die",
      r"\b(want|wanted|wanting|wanna|ready|going|deserve) to die\b|\bwanna die\b|\bi should (just )?die\b"),
    R(3, "active_ideation", "Does not want to live",
      r"\b(dont|do not|no longer) want to (be alive|live|exist)\b"),
    R(3, "self_harm", "Self-harm", r"\b(hurt|harm|cut|burn|cutting|hurting|harming|burning) myself\b|\bself[- ]?harm\w*\b"),

    # ---------------- Level 2: passive death wish -------------------------
    R(2, "passive_ideation", "Wishes to be dead / gone",
      r"\bwish (i was|i were|i had never been|id|i would) (dead|never born|gone|not alive)\b"),
    R(2, "passive_ideation", "Wishes to disappear / not wake up",
      r"\bwish i could (just )?(disappear|die|vanish|sleep forever|not wake up|stop existing)\b"),
    R(2, "passive_ideation", "Does not want to wake up", r"\b(dont|do not|never) want to wake up\b|\bnever wake up again\b"),
    R(2, "passive_ideation", "Others better off without them", r"\bbetter off (dead|without me)\b"),
    R(2, "passive_ideation", "No reason to live",
      r"\bno reason to (live|go on|keep going|be alive|stay alive)\b|\b(nothing|no one|nobody) (left )?to live for\b"),
    R(2, "passive_ideation", "Life not worth living",
      r"\blife (is|isnt|is not) (not )?worth (living|it)\b|\bwhats the point (of|in) (living|life|being alive)\b"),
    R(2, "passive_ideation", "Tired of living", r"\b(tired|sick) of (living|being alive|life)\b"),
    R(2, "passive_ideation", "Not wanting to be here",
      r"\b(dont|do not) want to be (here|around) anymore\b|\bdisappear forever\b"),

    # ---------------- Level 1: hopelessness / burden / entrapment ----------
    R(1, "hopelessness", "Hopelessness", r"\bhopeless\b|\bno hope\b|\blost all hope\b"),
    R(1, "hopelessness", "Nothing matters", r"\bnothing (ever )?matters\b|\bno point (in )?(anything|trying|anymore)\b|\btheres no point\b"),
    R(1, "hopelessness", "Cannot go on / cope",
      r"\bcant (go on|take (it|this) anymore|do this anymore|cope anymore|handle (it|this) anymore)\b"),
    R(1, "burden", "Feels like a burden", r"\b(im|i am|i feel like) a burden\b|\bburden (to|on) (everyone|my family|others|them|my parents)\b"),
    R(1, "entrapment", "Feels trapped", r"\bno way out\b|\b(trapped|stuck) (with no|and there is no|and theres no) (escape|way out)\b"),
    R(1, "worthlessness", "Worthlessness", r"\bworthless\b|\b(im|i am) (useless|a failure) (at everything|in life)\b"),
    R(1, "hopelessness", "Giving up", r"\bgive up on (everything|life|myself)\b|\bgiving up on (everything|life)\b"),
    R(1, "emptiness", "Feels empty / dead inside", r"\b(empty|dead|numb) inside\b"),
    R(1, "isolation", "No one would care", r"\b(no one|nobody) (would|will) (even )?(care|miss me|notice)\b|\bno one cares about me\b"),

    # ---------------- Hinglish (romanised Hindi) ----------------------------
    R(3, "active_ideation", "Hinglish: wants to die",
      r"\bmar(na|ne) (chah(ta|ti|te)|hai)\b|\bmar jaana chah(ta|ti)\b|\bmarne ka (mann|man|mn)\b", "hinglish"),
    R(3, "active_ideation", "Hinglish: suicide", r"\b(khud ?kushi|aatm?ahatya|atmahatya)\b", "hinglish"),
    R(3, "active_ideation", "Hinglish: harm / end self",
      r"\bkhud ko (maar|mar|khatam|khtm|hurt|nuksan)\b|\bzindagi (khatam|khtm) kar\b|\bsab (khatam|khtm) kar (du|dun|doon|dunga|dungi)\b", "hinglish"),
    R(2, "passive_ideation", "Hinglish: no wish to live",
      r"\bjeene ka (mann|man|mn) nahi\b|\b(jeena|jina) nahi chah(ta|ti)\b|\bmar (jau|jaun|jaaun|jaata|jati) to (accha|acha|behtar)\b", "hinglish"),
    R(2, "passive_ideation", "Hinglish: tired of life", r"\bzindagi se (thak|tang|pareshan)\b", "hinglish"),
    R(1, "burden", "Hinglish: feels like a burden", r"\b(bojh|boj) (hu|hoon|hun|ban gaya|ban gayi|ban gaya hoon|ban gayi hoon)\b", "hinglish"),
    R(1, "hopelessness", "Hinglish: no hope / no use",
      r"\b(koi )?(umeed|ummeed|ummid) nahi\b|\bkuch (bhi )?(accha|acha) nahi lagta\b|\bkoi (fayda|faayda) nahi\b", "hinglish"),

    # ---------------- Hindi (Devanagari) - substring rules -----------------
    R(3, "active_ideation", "Hindi: suicide", "आत्महत्या", "hi", False),
    R(3, "active_ideation", "Hindi: suicide", "खुदकुशी", "hi", False),
    R(3, "active_ideation", "Hindi: wants to die", "मरना चाहत", "hi", False),
    R(3, "active_ideation", "Hindi: harm self", "खुद को मार", "hi", False),
    R(3, "active_ideation", "Hindi: end life", "ज़िंदगी खत्म", "hi", False),
    R(3, "active_ideation", "Hindi: end life", "जिंदगी खत्म", "hi", False),
    R(2, "passive_ideation", "Hindi: no wish to live", "जीना नहीं चाहत", "hi", False),
    R(2, "passive_ideation", "Hindi: no wish to live", "जीने का मन नहीं", "hi", False),
    R(1, "hopelessness", "Hindi: no hope", "कोई उम्मीद नहीं", "hi", False),
    R(1, "burden", "Hindi: feels like a burden", "बोझ हूँ", "hi", False),
    R(1, "burden", "Hindi: feels like a burden", "बोझ हूं", "hi", False),

    # ---------------- Kannada - substring rules ----------------------------
    R(3, "active_ideation", "Kannada: suicide", "ಆತ್ಮಹತ್ಯೆ", "kn", False),
    R(3, "active_ideation", "Kannada: wants to die", "ಸಾಯಬೇಕು", "kn", False),
    R(3, "active_ideation", "Kannada: wants to die", "ಸಾಯಲು ಬಯಸ", "kn", False),
    R(2, "passive_ideation", "Kannada: no wish to live", "ಬದುಕಲು ಇಷ್ಟವಿಲ್ಲ", "kn", False),
    R(1, "hopelessness", "Kannada: no hope", "ಭರವಸೆ ಇಲ್ಲ", "kn", False),
]

# Figurative / benign idioms removed before matching (false-positive traps).
IDIOMS = [
    r"\b(this|that|it|the|my|these|those)( \w+){0,3} (is|are|was|were|s|keeps) (literally |just |really )?killing me\b",
    r"\bkilling it\b", r"\bkilled it\b", r"\bkill(ed)? (the|my) (presentation|exam|interview|game|show)\b",
    r"\bkill (some )?time\b", r"\bkill for (a|an|some)\b",
    r"\bdying (of|from) (laughter|laughing|embarrassment|boredom|curiosity|hunger|heat)\b",
    r"\bdying to (see|meet|try|know|go|watch|eat|hear|tell)\b",
    r"\b(bored|scared|worried|tickled) to death\b", r"\bdead tired\b", r"\bdrop dead\b",
    r"\bto die for\b", r"\b(phone|battery|laptop|car) (is|was) dead\b", r"\bdeadline\w*\b",
    r"\bkill (the|this) (process|app|task|lights|music|engine)\b",
    r"\bsuicide squad\b", r"\bsuicide mission\b", r"\bsuicide (awareness|prevention) (week|day|month|campaign|talk|workshop)\b",
]
_IDIOM_RE = re.compile("|".join(IDIOMS), re.IGNORECASE)

_NEG_BEFORE = re.compile(
    r"\b(never|not|wont|wouldnt|dont|do not|would not|will not|no longer|not going to|"
    r"am not|im not|have never|never ever|stop myself from)\b[\w\s]{0,12}$",
    re.IGNORECASE,
)
_NEG_AFTER_HI = re.compile(r"^\s{0,2}(nahi|nahin|nhi|नहीं|ಇಲ್ಲ)", re.IGNORECASE)
_TIMEFRAME = re.compile(
    r"\b(tonight|today|tomorrow|right now|this (week|weekend|evening)|by (morning|tomorrow)|aaj raat|abhi|aaj hi)\b",
    re.IGNORECASE,
)


def normalize(text: str) -> str:
    t = text.replace("’", "'").replace("‘", "'").replace("`", "'")
    t = t.lower()
    t = re.sub(r"'", "", t)                 # don't -> dont, i'm -> im
    t = re.sub(r"[\"“”]", " ", t)
    t = re.sub(r"\s+", " ", t).strip()
    # light spelling normalisation for common chat shorthand
    t = re.sub(r"\bu\b", "you", t)
    t = re.sub(r"\bwanna\b", "want to", t)
    t = re.sub(r"\bgonna\b", "going to", t)
    t = re.sub(r"\bcan not\b|\bcannot\b", "cant", t)
    t = re.sub(r"\bi m\b", "im", t)
    return t


@dataclass
class RiskResult:
    level: int
    tier: str
    score: float
    category: str | None
    reasons: list[dict]
    idioms_ignored: list[str]
    negated: bool

    def to_dict(self) -> dict:
        return {
            "level": self.level,
            "level_name": LEVEL_NAME[self.level],
            "tier": self.tier,
            "score": round(self.score, 3),
            "category": self.category,
            "reasons": self.reasons,
            "idioms_ignored": self.idioms_ignored,
            "negated": self.negated,
        }


def analyze(text: str) -> RiskResult:
    """Return the crisis-risk assessment for one user message."""
    raw = text or ""
    norm = normalize(raw)
    idioms = [m.group(0) for m in _IDIOM_RE.finditer(norm)]
    cleaned = _IDIOM_RE.sub(" ~ ", norm)

    reasons: list[dict] = []
    best_level = 0
    best_category = None
    any_negated = False
    seen: set[tuple[str, str]] = set()

    for rule in RULES:
        haystack = cleaned if rule.regex else raw
        for start, end, matched in rule.finditer(haystack):
            before = haystack[max(0, start - 40):start]
            after = haystack[end:end + 12]
            negated = bool(_NEG_BEFORE.search(before)) and rule.level >= 2
            if rule.lang in {"hinglish", "hi", "kn"} and _NEG_AFTER_HI.match(after) and rule.level >= 2:
                negated = True
            level = 1 if negated else rule.level
            key = (rule.label, matched)
            if key in seen:
                continue
            seen.add(key)
            any_negated = any_negated or negated
            reasons.append({
                "rule": rule.label,
                "category": rule.category,
                "level": level,
                "matched": matched.strip(),
                "lang": rule.lang,
                "negated": negated,
            })
            if level > best_level:
                best_level, best_category = level, rule.category

    # Timeframe + active ideation => imminent (level 4)
    if best_level == 3 and _TIMEFRAME.search(cleaned):
        tf = _TIMEFRAME.search(cleaned).group(0)
        reasons.append({"rule": "Timeframe given with ideation", "category": "timeframe",
                        "level": 4, "matched": tf, "lang": "en", "negated": False})
        best_level, best_category = 4, "timeframe"

    reasons.sort(key=lambda r: -r["level"])
    return RiskResult(
        level=best_level,
        tier=tier_for_level(best_level),
        score=LEVEL_SCORE[best_level],
        category=best_category,
        reasons=reasons,
        idioms_ignored=idioms,
        negated=any_negated and best_level <= 1,
    )


def explain(result: RiskResult) -> list[str]:
    """Short sentences for the counselor console."""
    out = []
    for r in result.reasons[:4]:
        tag = " (negated - check in)" if r["negated"] else ""
        out.append(f'{r["rule"]}: "{r["matched"]}"{tag}')
    return out
