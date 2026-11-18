"""Tiny helper for sentences that exist in all four supported languages."""
from __future__ import annotations

LANGS = ("en", "hi", "hinglish", "kn")


def L(en, hi, hg, kn) -> dict:
    """Build {"en": [...], "hi": [...], "hinglish": [...], "kn": [...]} (str or list per language)."""
    as_list = lambda v: v if isinstance(v, list) else [v]  # noqa: E731
    return {"en": as_list(en), "hi": as_list(hi), "hinglish": as_list(hg), "kn": as_list(kn)}
