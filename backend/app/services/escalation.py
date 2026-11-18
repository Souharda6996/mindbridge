"""Tiered escalation engine (deterministic - the LLM never decides this).

Inputs per turn:
  * language risk from crisis.analyze()        (what the person SAID)
  * fused multimodal distress from fusion.py   (how the person SEEMS)
  * the session's distress trajectory          (how it is TRENDING)

Output: LOW / MEDIUM / HIGH plus the list of reasons and the actions the app
must take. Language risk can raise the tier to HIGH on its own; distress
alone can raise it to MEDIUM at most (feeling sad is not a crisis), which
keeps false HIGH alarms low while never under-reacting to risk language.
"""
from __future__ import annotations

from dataclasses import dataclass

TIER_ORDER = {"LOW": 0, "MEDIUM": 1, "HIGH": 2}

SUSTAINED_THRESHOLD = 0.60     # smoothed distress considered "elevated"
SUSTAINED_TURNS = 3            # consecutive elevated turns -> MEDIUM
SEVERE_THRESHOLD = 0.80        # very high distress, two turns -> MEDIUM
MIN_CONFIDENCE = 0.30          # ignore distress when fusion confidence is poor


def max_tier(a: str, b: str) -> str:
    return a if TIER_ORDER[a] >= TIER_ORDER[b] else b


@dataclass
class Decision:
    tier: str
    reasons: list[str]
    actions: list[dict]
    create_alert: bool
    urgency: str  # routine | elevated | imminent

    def to_dict(self) -> dict:
        return {"tier": self.tier, "reasons": self.reasons, "actions": self.actions,
                "create_alert": self.create_alert, "urgency": self.urgency}


def decide(risk: dict, fusion: dict | None, elevated_streak: int,
           session_peak: str = "LOW", prior_sessions_high: int = 0) -> Decision:
    reasons: list[str] = []
    tier = "LOW"

    # 1) What the person said ------------------------------------------------
    if risk["tier"] != "LOW":
        tier = risk["tier"]
        for r in risk["reasons"][:3]:
            neg = " (negated)" if r.get("negated") else ""
            reasons.append(f'Language: {r["rule"]} - "{r["matched"]}"{neg}')

    # 2) How the person seems (multimodal distress) ---------------------------
    if fusion and fusion.get("confidence", 0) >= MIN_CONFIDENCE:
        s = fusion.get("smoothed", 0.0)
        if s >= SEVERE_THRESHOLD and elevated_streak >= 2:
            tier = max_tier(tier, "MEDIUM")
            reasons.append(f"Very high fused distress ({s:.2f}) for {elevated_streak} turns")
        elif s >= SUSTAINED_THRESHOLD and elevated_streak >= SUSTAINED_TURNS:
            tier = max_tier(tier, "MEDIUM")
            reasons.append(f"Sustained elevated distress ({s:.2f}) for {elevated_streak} turns")
        for line in fusion.get("explanations", [])[:2]:
            if tier != "LOW":
                reasons.append(line)

    # 3) Trajectory across sessions -------------------------------------------
    if prior_sessions_high >= 2:
        tier = max_tier(tier, "MEDIUM")
        reasons.append(f"Distress elevated in {prior_sessions_high} of the last 3 sessions")

    # Once HIGH in a session, stay HIGH until a counselor resolves it.
    if session_peak == "HIGH" and tier != "HIGH":
        reasons.append("Session already escalated to HIGH - staying in safety mode")
        tier = "HIGH"

    urgency = "routine"
    actions: list[dict] = []
    if tier == "HIGH":
        urgency = "imminent" if risk.get("level", 0) >= 4 else "elevated"
        actions = [
            {"type": "crisis_card"},
            {"type": "offer_trusted_contact"},
            {"type": "counselor_notified"},
        ]
    elif tier == "MEDIUM":
        actions = [{"type": "suggest_checkin"}, {"type": "offer_counselor"}]

    create_alert = tier == "HIGH" or (tier == "MEDIUM" and (
        risk["tier"] == "MEDIUM" or elevated_streak >= SUSTAINED_TURNS or prior_sessions_high >= 2))
    return Decision(tier=tier, reasons=reasons, actions=actions,
                    create_alert=create_alert, urgency=urgency)
