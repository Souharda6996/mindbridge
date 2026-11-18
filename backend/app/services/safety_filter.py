"""Output safety filter - checks every reply BEFORE the user sees it.

Even a well-prompted LLM can slip. This deterministic layer blocks replies
that diagnose, mention medication/doses, describe self-harm methods, or claim
to be a human professional, and swaps in a safe fallback.
"""
from __future__ import annotations

import re

from . import crisis

CHECKS = [
    ("diagnosis", re.compile(
        r"\byou (have|might have|may have|probably have|are suffering from|seem to have|clearly have)\b[\w\s]{0,20}"
        r"\b(depression|bipolar|anxiety disorder|ptsd|ocd|adhd|schizophrenia|bpd|borderline|personality disorder|"
        r"eating disorder|panic disorder|clinical)\b", re.I)),
    ("medication", re.compile(
        r"\b(sertraline|fluoxetine|escitalopram|citalopram|paroxetine|venlafaxine|bupropion|xanax|alprazolam|"
        r"diazepam|valium|clonazepam|lorazepam|zolpidem|ambien|lithium|quetiapine|olanzapine|melatonin|"
        r"antidepressants?|sleeping pills?|benzodiazepines?|ssris?)\b", re.I)),
    ("dosage", re.compile(r"\b\d+\s?(mg|milligrams?|ml|tablets?|pills?)\b", re.I)),
    ("impersonation", re.compile(r"\b(as (a|your) (doctor|therapist|psychiatrist|psychologist)|i am (a|your) "
                                 r"(doctor|therapist|psychiatrist|psychologist|human))\b", re.I)),
]

SAFE_FALLBACK = ("I want to be careful here, because that's something a qualified professional should guide you on. "
                 "I'm an AI companion, not a doctor. What I can do is listen and help you think things through. "
                 "Would you like to tell me more about how you're feeling?")


def check(reply: str) -> tuple[str, list[str]]:
    """Return (safe_reply, flags). Flags are logged for the evaluation page."""
    flags = [name for name, rx in CHECKS if rx.search(reply)]
    method = crisis.analyze(reply)
    if method.level >= 4:
        flags.append("self-harm method content")
    if flags:
        return SAFE_FALLBACK, flags
    return reply, []
