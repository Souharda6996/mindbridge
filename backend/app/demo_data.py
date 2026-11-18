"""Sample history so the dashboard is meaningful on the first run.

Clearly flagged with is_demo=1 and removable from Settings -> "Clear sample history".
The story: a student going through an exam month - a dip in mood and sleep
around the exam week, one counsellor alert, then gradual recovery.
"""
from __future__ import annotations

import json
import math
import random
import uuid
from datetime import datetime, timedelta

from . import db, security

TAGS = ["exams", "sleep", "friends", "family", "exercise", "placement", "hostel", "music", "project"]
NOTES = [
    "Long day in the lab, felt okay by evening.", "Couldn't focus, kept checking my phone.",
    "Talked to my sister, that helped.", "Mock test went badly. Feeling behind.",
    "Went for a walk with Rohan, felt lighter.", "Barely slept, exam tomorrow.",
    "Results were better than I expected!", "Quiet day. A bit lonely in the hostel.",
]


def seed(days: int = 28) -> None:
    rng = random.Random(42)
    today = datetime.now().replace(hour=21, minute=0, second=0, microsecond=0)
    with db.tx() as c:
        for i in range(days, 0, -1):
            day = today - timedelta(days=i)
            # dip centred ~12 days ago (exam week), recovery afterwards
            dip = math.exp(-((i - 12) ** 2) / 18.0)
            mood = round(7.2 - 3.4 * dip + rng.uniform(-0.8, 0.8))
            sleep = round(7.4 - 2.6 * dip + rng.uniform(-0.7, 0.6), 1)
            anxiety = round(3 + 5 * dip + rng.uniform(-1, 1))
            energy = round(6.5 - 3 * dip + rng.uniform(-1, 1))
            if rng.random() < 0.15:
                continue  # missed check-ins look realistic
            tags = rng.sample(TAGS, 2) + (["exams"] if dip > 0.5 else [])
            c.execute(
                "INSERT INTO checkins(day, mood, sleep_hours, energy, anxiety, tags, note_enc, created_at, is_demo)"
                " VALUES (?,?,?,?,?,?,?,?,1)",
                (day.date().isoformat(), max(1, min(10, mood)), max(3.5, sleep), max(1, min(10, energy)),
                 max(1, min(10, anxiety)), json.dumps(sorted(set(tags))),
                 security.encrypt(rng.choice(NOTES)), day.isoformat()),
            )

        emotions = ["sadness", "fear", "neutral", "joy", "fear", "sadness", "neutral", "joy", "joy", "neutral"]
        session_days = [26, 23, 19, 15, 13, 12, 11, 8, 5, 2]
        for idx, i in enumerate(session_days):
            dip = math.exp(-((i - 12) ** 2) / 18.0)
            start = today - timedelta(days=i, hours=rng.randint(1, 5))
            distress = round(min(0.92, 0.28 + 0.5 * dip + rng.uniform(-0.06, 0.06)), 3)
            tier = "MEDIUM" if distress >= 0.6 else "LOW"
            sid = str(uuid.uuid4())
            c.execute(
                "INSERT INTO sessions(id, started_at, ended_at, mode, peak_tier, avg_distress, turns, dominant_emotion, is_demo)"
                " VALUES (?,?,?,?,?,?,?,?,1)",
                (sid, start.isoformat(), (start + timedelta(minutes=rng.randint(6, 22))).isoformat(),
                 rng.choice(["text", "video", "text"]), tier, distress, rng.randint(5, 16),
                 "sadness" if dip > 0.6 else emotions[idx]),
            )
            weights = {"text": round(rng.uniform(0.38, 0.5), 3), "voice": round(rng.uniform(0.2, 0.32), 3)}
            weights["face"] = round(1 - weights["text"] - weights["voice"], 3)
            c.execute(
                "INSERT INTO readings(session_id, created_at, fused, confidence, smoothed, payload) VALUES (?,?,?,?,?,?)",
                (sid, start.isoformat(), distress, 0.72, distress, json.dumps({"weights": weights})),
            )
            if i == 12:
                c.execute(
                    "INSERT INTO alerts(session_id, created_at, tier, source, reasons, excerpt_enc, status, note, updated_at, is_demo)"
                    " VALUES (?,?,?,?,?,?,?,?,?,1)",
                    (sid, (start + timedelta(minutes=9)).isoformat(), "MEDIUM", "escalation",
                     json.dumps(['Language: Hopelessness - "no point in trying"',
                                 "Sustained elevated distress (0.71) for 4 turns",
                                 "voice: long pauses (46% silence, 5 long breaks)"]),
                     security.encrypt("I've studied for weeks and there's no point in trying anymore."),
                     "resolved", "Spoke with student on call. Exam anxiety; follow-up booked.",
                     (start + timedelta(hours=3)).isoformat()),
                )
    db.set_setting("demo_seeded", True)


def clear() -> None:
    with db.tx() as c:
        demo_ids = [r[0] for r in c.execute("SELECT id FROM sessions WHERE is_demo = 1").fetchall()]
        for sid in demo_ids:
            c.execute("DELETE FROM readings WHERE session_id = ?", (sid,))
            c.execute("DELETE FROM messages WHERE session_id = ?", (sid,))
        c.execute("DELETE FROM sessions WHERE is_demo = 1")
        c.execute("DELETE FROM checkins WHERE is_demo = 1")
        c.execute("DELETE FROM alerts WHERE is_demo = 1")
