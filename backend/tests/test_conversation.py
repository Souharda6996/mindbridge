"""v2 gate: no conversation loops, reply language = user language, short answers handled."""
import re

import pytest

from backend.app.services import conversation, language, models, offline_engine

DEVANAGARI = re.compile(r"[ऀ-ॿ]")
KANNADA = re.compile(r"[ಀ-೿]")


def _sentences(reply: str) -> list[str]:
    return [s.strip() for s in re.split(r"(?<=[.?!।])\s+", reply) if s.strip()]


def _chat(turns, lang_hint=None, tier="LOW"):
    mem, lang, replies = {}, lang_hint, []
    for text, emo, d in turns:
        lang = language.detect(text, lang)
        replies.append(offline_engine.respond(text, emo, d, tier, mem, lang))
    return replies, mem


def test_no_sentence_repeats_over_ten_turns():
    turns = [("my exams are next week", "fear", 0.5), ("I keep studying but nothing sticks", "fear", 0.55),
             ("I'm so stressed about it", "fear", 0.6), ("my parents expect a lot", "fear", 0.5),
             ("it's just too much", "sadness", 0.6), ("I can't focus at all", "fear", 0.5),
             ("everyone else seems fine", "sadness", 0.5), ("I studied all night", "sadness", 0.5),
             ("exams are just too much", "fear", 0.6), ("I don't know anymore", "sadness", 0.5)]
    replies, _ = _chat(turns)
    seen = []
    for r in replies:
        for s in _sentences(r["reply"]):
            assert s not in seen, f"repeated sentence: {s!r}"
            seen.append(s)


def test_each_exercise_offered_at_most_once():
    turns = [("my heart is racing", "fear", 0.7)] * 6
    replies, _ = _chat(turns)
    offered = [r["exercise"] for r in replies if r["exercise"]]
    assert len(offered) == len(set(offered))


@pytest.mark.parametrize("text,script", [
    ("मुझे परीक्षा की बहुत चिंता हो रही है", DEVANAGARI),
    ("ನನಗೆ ತುಂಬಾ ಒಂಟಿತನ ಅನ್ನಿಸುತ್ತಿದೆ", KANNADA),
])
def test_reply_uses_same_script(text, script):
    replies, _ = _chat([(text, "fear", 0.5)])
    assert script.search(replies[0]["reply"])


def test_hinglish_reply_is_romanised_hindi():
    replies, _ = _chat([("yaar mujhe bahut gussa aa raha hai", "anger", 0.5)])
    reply = replies[0]["reply"]
    assert not DEVANAGARI.search(reply)
    assert re.search(r"\b(aap|hai|kya|ki|ke|mein)\b", reply, re.I)


def test_language_is_sticky_for_short_answers():
    assert language.detect("ok", "hi") == "hi"
    assert language.detect("haan", None) == "hinglish"
    assert language.detect("I am feeling low today", "hinglish") == "en"


@pytest.mark.parametrize("answer,lang", [("yes", "en"), ("हाँ", "hi"), ("haan", "hinglish"), ("ಹೌದು", "kn")])
def test_yes_after_exercise_offer_is_acknowledged(answer, lang):
    mem = {"last_q": "exercise", "last_exercise": "box_breathing", "turn": 3}
    r = offline_engine.respond(answer, "neutral", 0.3, "LOW", mem, lang)
    assert r["intent"] == "affirm" and r["reply"] in offline_engine.AFFIRM_EXERCISE[lang]


@pytest.mark.parametrize("answer,lang", [("no", "en"), ("नहीं", "hi"), ("nahi", "hinglish"), ("ಇಲ್ಲ", "kn")])
def test_no_declines_exercise_and_it_is_not_offered_again(answer, lang):
    mem = {"last_q": "exercise", "last_exercise": "box_breathing", "turn": 3, "offered": ["box_breathing"]}
    r = offline_engine.respond(answer, "neutral", 0.3, "LOW", mem, lang)
    assert r["intent"] == "deny" and "box_breathing" in mem["declined"]


@pytest.mark.parametrize("text", ["I don't know", "idk", "पता नहीं", "pata nahi", "ಗೊತ್ತಿಲ್ಲ"])
def test_unsure_is_recognised(text):
    lang = language.detect(text)
    r = offline_engine.respond(text, "neutral", 0.3, "LOW", {}, lang)
    assert r["intent"] == "unsure"


def test_help_request_gets_a_practical_tip():
    mem = {}
    offline_engine.respond("my exams are next week", "fear", 0.4, "LOW", mem, "en")
    r = offline_engine.respond("what should I do?", "fear", 0.4, "LOW", mem, "en")
    assert any(t in r["reply"] for t in offline_engine.TIPS["exam"]["en"]) or r["exercise"]


def test_crisis_followups_vary_and_match_language():
    mem = {}
    first = conversation.crisis_reply("hi", "प्रिया", False, mem, True)
    second = conversation.crisis_reply("hi", "प्रिया", False, mem, False)
    third = conversation.crisis_reply("hi", "प्रिया", False, mem, False)
    assert "14416" in first and DEVANAGARI.search(first)
    assert len({first, second, third}) == 3


def test_crisis_kannada_script():
    assert KANNADA.search(conversation.crisis_reply("kn", None, True, {}, True))


def test_goemotions_grouping_no_longer_inflates_joy():
    # raw label scores the real model produced for "I feel okay I guess"
    probs = {"approval": 0.573, "caring": 0.177, "neutral": 0.111, "relief": 0.064, "joy": 0.052, "realization": 0.035}
    groups = models.group_goemotions(probs)
    assert max(groups, key=groups.get) == "neutral"
    # and for "Finally finished my project and it works perfectly"
    probs = {"approval": 0.402, "joy": 0.303, "admiration": 0.137, "neutral": 0.079, "excitement": 0.074, "relief": 0.046}
    groups = models.group_goemotions(probs)
    assert max(groups, key=groups.get) == "joy"


def test_indic_lexicon_with_negation():
    hits = models._indic_lexicon("aaj accha nahi lag raha")
    assert hits["sadness"] >= 1 and hits["joy"] == 0
