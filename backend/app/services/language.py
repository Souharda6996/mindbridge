"""Language identification for English, Hindi (Devanagari), Hinglish (romanised Hindi) and Kannada.

Script detection is exact (Unicode blocks). Hinglish vs English is decided by
counting common Hindi function words written in Latin script. Very short
messages ("ok", "yes") are ambiguous, so the caller can pass the language used
earlier in the conversation and it will be kept ("sticky" language).
"""
from __future__ import annotations

import re

NAMES = {"en": "English", "hi": "Hindi", "hinglish": "Hinglish", "kn": "Kannada"}
SCRIPTS = {"en": "Latin script", "hi": "Devanagari script", "hinglish": "Latin script (romanised Hindi)",
           "kn": "Kannada script"}

_HINGLISH = re.compile(
    r"\b(hai|hain|nahi|nahin|nhi|main|mai|mera|meri|mere|mujhe|mujhko|kya|kyu|kyun|hoon|hun|hu|bahut|bohot|"
    r"yaar|kar|karna|raha|rahi|rahe|kuch|bhi|ab|aaj|kal|tha|thi|ho|gaya|gayi|accha|acha|theek|thik|"
    r"lag|lagta|lagti|matlab|sab|kaise|kaisa|kyunki|lekin|par|aur|toh|tum|aap|apna|apni|wala|wali|ghar|"
    r"dost|pata|samajh|soch|dil|zindagi|jeena|marna|gussa|udaas|darr|khush|tension|pareshan|bas|haan|ji)\b",
    re.I,
)
_EN = re.compile(r"\b(the|is|am|are|was|i|you|my|me|and|but|to|of|it|that|this|feel|feeling|have|not|do|what)\b", re.I)


def detect(text: str, previous: str | None = None) -> str:
    t = text or ""
    if re.search(r"[ऀ-ॿ]", t):
        return "hi"
    if re.search(r"[ಀ-೿]", t):
        return "kn"
    words = re.findall(r"[A-Za-z']+", t)
    hing = len(_HINGLISH.findall(t))
    eng = len(_EN.findall(t))
    if len(words) <= 2 and previous in {"hi", "hinglish", "kn"}:
        return previous                      # "ok", "haan", "yes" -> keep the conversation's language
    if hing >= 2 and hing >= eng:
        return "hinglish"
    if hing >= 1 and len(words) <= 4 and eng == 0:
        return "hinglish"
    return "en"
