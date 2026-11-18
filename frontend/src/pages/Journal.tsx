import { useEffect, useState } from "react";
import { Check } from "lucide-react";
import { api, type Helpline } from "../api";
import { Empty, PageHead } from "../components/ui";
import CrisisCard from "../components/CrisisCard";
import { useApp } from "../components/Layout";

const TAGS = ["exams", "sleep", "friends", "family", "exercise", "placement", "hostel", "music", "project", "health", "money", "relationship"];
const MOOD_WORDS = ["", "very low", "low", "down", "meh", "okay", "fine", "good", "really good", "great", "wonderful"];

export function moodColor(m: number | null) {
  if (m === null) return "var(--surface-2)";
  if (m <= 3) return "var(--clay-soft)";
  if (m <= 5) return "var(--amber-soft)";
  if (m <= 7) return "var(--accent-soft)";
  return "color-mix(in srgb, var(--accent) 55%, var(--surface))";
}

export default function Journal() {
  const { toast } = useApp();
  const [mood, setMood] = useState(6);
  const [sleep, setSleep] = useState(7);
  const [energy, setEnergy] = useState(6);
  const [anxiety, setAnxiety] = useState(4);
  const [tags, setTags] = useState<string[]>([]);
  const [note, setNote] = useState("");
  const [rows, setRows] = useState<any[]>([]);
  const [saved, setSaved] = useState(false);
  const [crisis, setCrisis] = useState<{ helplines: Helpline[]; alert: number | null; reasons: string[] } | null>(null);

  const load = () => api.checkins().then(setRows).catch(() => {});
  useEffect(() => { load(); }, []);

  const save = async () => {
    const r = await api.addCheckin({ mood, sleep_hours: sleep, energy, anxiety, tags, note: note || null });
    setSaved(true);
    toast("Check-in saved and encrypted");
    setTimeout(() => setSaved(false), 2500);
    if (r.risk.tier === "HIGH") setCrisis({ helplines: r.helplines, alert: r.alert_id, reasons: r.risk.reasons.map((x: any) => `${x.rule}: "${x.matched}"`) });
    setNote("");
    load();
  };

  const byDay = new Map(rows.map((r) => [r.day, r.mood]));
  const days: { d: Date; mood: number | null }[] = [];
  const today = new Date();
  const start = new Date(today);
  start.setDate(today.getDate() - 34 - ((today.getDay() + 6) % 7) + 6);
  for (let i = 0; i < 35; i++) {
    const d = new Date(start); d.setDate(start.getDate() + i);
    const key = d.toLocaleDateString("en-CA");
    days.push({ d, mood: byDay.has(key) ? (byDay.get(key) as number) : null });
  }

  const slider = (label: string, v: number, set: (n: number) => void, min: number, max: number, step = 1, unit = "") => (
    <label className="field">
      <span className="row"><span>{label}</span><span className="spacer" /><span className="num" style={{ color: "var(--ink)", fontSize: 15 }}>{v}{unit}</span></span>
      <input type="range" min={min} max={max} step={step} value={v} onChange={(e) => set(Number(e.target.value))} />
    </label>
  );

  return (
    <div>
      <PageHead eyebrow="Mood journal" title={<>Thirty seconds, <em className="gold">once a day</em></>}
        lede="Small notes become patterns you can see. Everything you write here is encrypted on this device." />
      <div className="grid g-main reveal">
        <div className="card">
          <div className="card-head"><h3>How are you feeling today?</h3><span className="chip gold" style={{ textTransform: "capitalize" }}>{MOOD_WORDS[mood]}</span></div>
          <div className="mood-scale">
            {Array.from({ length: 10 }, (_, i) => i + 1).map((n) => (
              <button key={n} className={mood === n ? "on" : ""} onClick={() => setMood(n)}>{n}</button>
            ))}
          </div>
          <div className="grid g-3" style={{ marginTop: 22 }}>
            {slider("Sleep last night", sleep, setSleep, 0, 12, 0.5, " h")}
            {slider("Energy", energy, setEnergy, 1, 10)}
            {slider("Anxiety", anxiety, setAnxiety, 1, 10)}
          </div>
          <div style={{ marginTop: 20 }}>
            <div className="small muted" style={{ marginBottom: 10, fontWeight: 600 }}>What was part of your day?</div>
            <div className="row wrap">
              {TAGS.map((t) => (
                <button key={t} className={`chip toggle ${tags.includes(t) ? "on" : ""}`}
                  onClick={() => setTags(tags.includes(t) ? tags.filter((x) => x !== t) : [...tags, t])}>{t}</button>
              ))}
            </div>
          </div>
          <label className="field" style={{ marginTop: 20 }}>A line about today (optional)
            <textarea className="textarea" value={note} onChange={(e) => setNote(e.target.value)} placeholder="What stood out today?" />
          </label>
          <div className="row" style={{ marginTop: 16 }}>
            <button className="btn primary lg" onClick={save}>Save check-in</button>
            {saved && <span className="row small fade-in" style={{ color: "var(--accent)" }}><Check size={15} />Saved</span>}
          </div>
          {crisis && <div style={{ marginTop: 16 }}><CrisisCard helplines={crisis.helplines} sessionId={null} alertId={crisis.alert} reasons={crisis.reasons} /></div>}
        </div>

        <div className="card">
          <div className="card-head"><h3>Last five weeks</h3></div>
          <div className="heat" style={{ marginBottom: 6 }}>
            {["M", "T", "W", "T", "F", "S", "S"].map((d, i) => <div key={i} className="tiny faint" style={{ aspectRatio: "auto" }}>{d}</div>)}
          </div>
          <div className="heat">
            {days.map(({ d, mood: m }, i) => (
              <div key={i} title={`${d.toDateString()}${m ? ` - mood ${m}` : ""}`}
                style={{ background: moodColor(m), border: d.toDateString() === today.toDateString() ? "1.5px solid var(--gold)" : "1px solid var(--line-2)",
                  color: m && m > 7 ? "var(--accent-ink)" : "var(--ink-2)", opacity: d > today ? 0.35 : 1 }}>
                {d.getDate()}
              </div>
            ))}
          </div>
          <div className="row tiny faint" style={{ marginTop: 14, justifyContent: "space-between" }}>
            {([["low", 2], ["okay", 5], ["good", 7], ["great", 9]] as [string, number][]).map(([l, m]) => (
              <span key={l} className="row" style={{ gap: 5 }}><i className="sw" style={{ background: moodColor(m) }} />{l}</span>
            ))}
          </div>
        </div>
      </div>

      <div className="card fade-in" style={{ marginTop: 18 }}>
        <div className="card-head"><h3>Entries</h3><span className="small faint">{rows.length} saved</span></div>
        {rows.length ? (
          <table className="t">
            <thead><tr><th>Day</th><th>Mood</th><th>Sleep</th><th>Energy</th><th>Anxiety</th><th>Tags</th><th>Note</th></tr></thead>
            <tbody>
              {rows.slice(0, 14).map((r) => (
                <tr key={r.id}>
                  <td className="num">{r.day}</td>
                  <td><span className="row" style={{ gap: 7 }}><i className="sw" style={{ background: moodColor(r.mood), width: 12, height: 12, borderRadius: 4 }} /><b className="num">{r.mood}</b></span></td>
                  <td className="num">{r.sleep_hours ?? "–"}</td>
                  <td className="num">{r.energy ?? "–"}</td>
                  <td className="num">{r.anxiety ?? "–"}</td>
                  <td className="small">{r.tags.join(", ")}</td>
                  <td className="muted" style={{ maxWidth: 340 }}>{r.note ?? ""}</td>
                </tr>
              ))}
            </tbody>
          </table>
        ) : <Empty>No entries yet.</Empty>}
      </div>
    </div>
  );
}
