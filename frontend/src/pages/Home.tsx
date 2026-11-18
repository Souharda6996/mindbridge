import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { Area, AreaChart, CartesianGrid, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { ArrowRight, ArrowUpRight, Flame, MessagesSquare, Moon, NotebookPen, Sparkles, Waves } from "lucide-react";
import { api, pct, timeAgo } from "../api";
import { axisTick, CountUp, Empty, Ring, TierBadge, tooltipStyle } from "../components/ui";
import { useApp } from "../components/Layout";
import { EXERCISES } from "../components/Exercises";

const fmtDay = (d: string) => new Date(d).toLocaleDateString("en-IN", { day: "numeric", month: "short" });
const MOODS: [number, string, string][] = [[2, "Low", "var(--e-sadness)"], [4, "Down", "var(--e-fear)"], [6, "Okay", "var(--e-neutral)"],
  [8, "Good", "var(--m-text)"], [10, "Great", "var(--e-joy)"]];

function greeting() {
  const h = new Date().getHours();
  return h < 5 ? "Still awake" : h < 12 ? "Good morning" : h < 17 ? "Good afternoon" : "Good evening";
}

/** 0-100 wellbeing estimate from the last 7 days (mood, sleep, anxiety, conversation distress). */
function wellbeing(k: any) {
  const parts: [number, number][] = [];
  if (k.avg_mood_7d != null) parts.push([(k.avg_mood_7d - 1) / 9, 0.45]);
  if (k.avg_sleep_7d != null) parts.push([Math.min(1, Math.max(0, (k.avg_sleep_7d - 4) / 4)), 0.2]);
  if (k.avg_anxiety_7d != null) parts.push([1 - (k.avg_anxiety_7d - 1) / 9, 0.2]);
  if (k.latest_distress != null) parts.push([1 - k.latest_distress, 0.15]);
  const w = parts.reduce((s, [, x]) => s + x, 0);
  return w ? Math.round((parts.reduce((s, [v, x]) => s + v * x, 0) / w) * 100) : null;
}

export default function Home() {
  const { settings, companion, toast } = useApp();
  const nav = useNavigate();
  const [d, setD] = useState<any>(null);
  const [err, setErr] = useState<string | null>(null);
  const [logged, setLogged] = useState<number | null>(null);

  const load = () => api.dashboard(30).then(setD).catch((e) => setErr(e.message));
  useEffect(() => { load(); }, []);

  const today = new Date().toLocaleDateString("en-CA");
  const todayEntry = d?.mood_series?.find((c: any) => c.day === today);
  const k = d?.kpis;
  const score = k ? wellbeing(k) : null;
  const rawName = (settings?.profile?.name ?? "").trim();
  const name = rawName ? rawName[0].toUpperCase() + rawName.slice(1) : "";

  const recs = useMemo(() => {
    if (!k) return [];
    const out: { icon: any; tone: string; title: string; why: string; to: string }[] = [];
    if (k.avg_sleep_7d != null && k.avg_sleep_7d < 7)
      out.push({ icon: <Moon size={19} />, tone: "blue", title: "Try the sleep wind-down tonight", why: `You've averaged ${k.avg_sleep_7d} h of sleep this week.`, to: "/toolkit#sleep_winddown" });
    if (k.avg_anxiety_7d != null && k.avg_anxiety_7d >= 5)
      out.push({ icon: <Waves size={19} />, tone: "accent", title: "One minute of box breathing", why: `Anxiety has been ${k.avg_anxiety_7d}/10 on average.`, to: "/toolkit#box_breathing" });
    const tags = (d.top_tags ?? []).map((t: any) => t[0]);
    if (tags.includes("exams"))
      out.push({ icon: <NotebookPen size={19} />, tone: "plum", title: "Untangle exam worries", why: "\"exams\" appears often in your check-ins.", to: "/toolkit#thought_record" });
    if (k.avg_mood_7d != null && k.avg_mood_prev_7d != null && k.avg_mood_7d > k.avg_mood_prev_7d)
      out.push({ icon: <Sparkles size={19} />, tone: "gold", title: "Note three good things", why: "Your mood is rising. Capture what's helping.", to: "/toolkit#gratitude" });
    out.push({ icon: <MessagesSquare size={19} />, tone: "accent", title: `Talk it through with ${companion}`, why: "A private space to think out loud, any time.", to: "/companion" });
    return out.slice(0, 4);
  }, [d, k, companion]);

  const quickLog = async (mood: number) => {
    setLogged(mood);
    await api.addCheckin({ mood, tags: [], note: null });
    toast("Mood logged. Add more detail in your journal any time.");
    load();
  };

  if (err) return <div className="banner medium">Cannot reach the server: {err}</div>;
  if (!d) return <div className="stack"><div className="skeleton" style={{ height: 220 }} /><div className="skeleton" style={{ height: 300 }} /></div>;

  const delta = k.avg_mood_7d != null && k.avg_mood_prev_7d != null ? k.avg_mood_7d - k.avg_mood_prev_7d : null;
  const last7 = Array.from({ length: 7 }, (_, i) => {
    const dt = new Date(); dt.setDate(dt.getDate() - (6 - i));
    const key = dt.toLocaleDateString("en-CA");
    const e = d.mood_series.find((c: any) => c.day === key);
    return { key, label: dt.toLocaleDateString("en-IN", { weekday: "narrow" }), mood: e?.mood ?? null };
  });
  const hasDemo = d.recent_sessions.some((s: any) => s.demo);

  return (
    <div className="reveal">
      <section className="hero">
        <div className="grid" style={{ gridTemplateColumns: "minmax(0,1.5fr) auto", alignItems: "center", gap: 28 }}>
          <div>
            <div className="eyebrow gold">{new Date().toLocaleDateString("en-IN", { weekday: "long", day: "numeric", month: "long" })}</div>
            <h1 style={{ marginTop: 10 }}>{greeting()}{name ? <>, <em>{name}</em></> : ""}.</h1>
            <p className="muted" style={{ marginTop: 12, fontSize: 16, maxWidth: 560 }}>
              {k.checkin_streak > 1 ? <>You've checked in <b>{k.checkin_streak} days</b> in a row. </> : null}
              {delta !== null ? (delta > 0.2 ? <>Your mood is up <b>{delta.toFixed(1)} points</b> on last week. Keep doing what's working.</>
                : delta < -0.2 ? <>This week has felt heavier than the last. Be gentle with yourself; {companion} is here if you want to talk.</>
                  : <>Your week has been steady.</>) : <>Start with a quick check-in below.</>}
            </p>
            <div className="row wrap" style={{ marginTop: 22 }}>
              <button className="btn primary lg" onClick={() => nav("/companion")}>Talk to {companion} <ArrowRight size={16} /></button>
              <Link className="btn lg" to="/journal">Open journal</Link>
            </div>
          </div>
          <Ring value={(score ?? 0) / 100} size={188}>
            <div>
              <div className="serif num" style={{ fontSize: 52, fontWeight: 500, lineHeight: 1 }}><CountUp value={score} /></div>
              <div className="eyebrow" style={{ marginTop: 6 }}>Wellbeing</div>
            </div>
          </Ring>
        </div>
      </section>

      {hasDemo && <div className="banner info" style={{ marginTop: 16 }}>Showing sample history so the dashboard can be demonstrated. Remove it in Privacy & settings.</div>}

      <div className="grid g-main" style={{ marginTop: 18 }}>
        <div className="card">
          <div className="card-head">
            <div><h3>How are you, right now?</h3><p className="small faint">One tap. It shapes your insights.</p></div>
            {todayEntry && <span className="chip gold">Today: {todayEntry.mood}/10</span>}
          </div>
          <div className="mood-pills">
            {MOODS.map(([v, label, color]) => (
              <button key={v} className={`mood-pill ${(logged ?? todayEntry?.mood) === v ? "on" : ""}`} onClick={() => quickLog(v)}>
                <span className="mood-dot" style={{ background: color, boxShadow: `0 0 0 4px color-mix(in srgb, ${color} 20%, transparent)` }} />
                {label}
              </button>
            ))}
          </div>
          <div className="divider" />
          <div className="row" style={{ marginBottom: 10 }}><span className="eyebrow">Your week</span><span className="spacer" />
            <span className="row tiny faint" style={{ gap: 6 }}><Flame size={13} color="var(--gold)" />{k.checkin_streak}-day streak</span></div>
          <div className="week-dots">
            {last7.map((x) => (
              <div key={x.key} style={{ textAlign: "center" }}>
                <div className="week-dot" title={x.mood ? `mood ${x.mood}` : "no check-in"} style={{
                  background: x.mood == null ? "var(--surface-2)" : x.mood <= 3 ? "var(--clay-soft)" : x.mood <= 5 ? "var(--amber-soft)" : x.mood <= 7 ? "var(--accent-soft)" : "var(--accent)",
                  color: x.mood != null && x.mood > 7 ? "var(--accent-ink)" : "var(--ink-2)", border: x.key === today ? "1.5px solid var(--gold)" : "1px solid var(--line-2)",
                }}>{x.mood ?? "·"}</div>
                <div className="tiny faint" style={{ marginTop: 4 }}>{x.label}</div>
              </div>
            ))}
          </div>
        </div>

        <div className="card">
          <div className="card-head"><h3>For you</h3><span className="tiny faint">based on your week</span></div>
          <div className="stack" style={{ gap: 10 }}>
            {recs.map((r) => (
              <Link key={r.title} to={r.to} className="rec">
                <span className={`icon-tile ${r.tone}`}>{r.icon}</span>
                <span style={{ flex: 1 }}><b style={{ display: "block", fontWeight: 700 }}>{r.title}</b><span className="small faint">{r.why}</span></span>
                <ArrowUpRight size={16} className="faint" />
              </Link>
            ))}
          </div>
        </div>
      </div>

      <div className="grid g-4" style={{ marginTop: 18 }}>
        {[
          ["Average mood", k.avg_mood_7d, 1, "/ 10", delta !== null ? `${delta >= 0 ? "▲" : "▼"} ${Math.abs(delta).toFixed(1)} vs last week` : "", delta === null ? "flat" : delta > 0.2 ? "up" : delta < -0.2 ? "down" : "flat"],
          ["Average sleep", k.avg_sleep_7d, 1, "hours", "target 7–9 h", k.avg_sleep_7d >= 7 ? "up" : "down"],
          ["Average anxiety", k.avg_anxiety_7d, 1, "/ 10", "lower is calmer", k.avg_anxiety_7d <= 4 ? "up" : "flat"],
          ["Conversations", k.sessions, 0, "in 30 days", `latest distress ${pct(k.latest_distress)}`, "flat"],
        ].map(([label, v, dec, unit, sub, cls]) => (
          <div key={String(label)} className="card kpi lift">
            <div className="label">{label as string}</div>
            <div className="value"><CountUp value={v as number} decimals={dec as number} /><small>{unit as string}</small></div>
            <div className={`delta ${cls}`}>{sub as string}</div>
          </div>
        ))}
      </div>

      <div className="grid g-main" style={{ marginTop: 18 }}>
        <div className="card">
          <div className="card-head">
            <div><h3>Your last 30 days</h3><p className="small faint">Mood and sleep from your check-ins</p></div>
            <div className="row tiny faint" style={{ gap: 14 }}>
              <span className="row" style={{ gap: 6 }}><i className="sw" style={{ background: "var(--accent)" }} />mood</span>
              <span className="row" style={{ gap: 6 }}><i className="sw" style={{ background: "var(--gold)" }} />sleep</span>
            </div>
          </div>
          <div style={{ height: 270 }}>
            {d.mood_series.length ? (
              <ResponsiveContainer>
                <AreaChart data={d.mood_series} margin={{ top: 6, right: 6, left: -20, bottom: 0 }}>
                  <defs>
                    <linearGradient id="moodFill" x1="0" y1="0" x2="0" y2="1">
                      <stop offset="0%" stopColor="var(--accent)" stopOpacity={0.28} />
                      <stop offset="100%" stopColor="var(--accent)" stopOpacity={0} />
                    </linearGradient>
                  </defs>
                  <CartesianGrid stroke="var(--grid)" vertical={false} />
                  <XAxis dataKey="day" tickFormatter={fmtDay} tick={axisTick} axisLine={false} tickLine={false} minTickGap={28} />
                  <YAxis domain={[0, 10]} tick={axisTick} axisLine={false} tickLine={false} />
                  <Tooltip labelFormatter={(l) => fmtDay(String(l))} {...tooltipStyle} />
                  <Area type="monotone" dataKey="mood" stroke="var(--accent)" strokeWidth={2.4} fill="url(#moodFill)" dot={false} animationDuration={1100} />
                  <Line type="monotone" dataKey="sleep_hours" stroke="var(--gold)" strokeWidth={1.8} dot={false} strokeDasharray="5 4" />
                </AreaChart>
              </ResponsiveContainer>
            ) : <Empty>No check-ins yet.</Empty>}
          </div>
        </div>
        <div className="card">
          <div className="card-head"><h3>What we're noticing</h3></div>
          {d.insights.length ? (
            <div className="stack" style={{ gap: 14 }}>
              {d.insights.map((s: string, i: number) => (
                <div key={i} className="row top" style={{ gap: 12 }}>
                  <span className="serif italic gold" style={{ fontSize: 24, lineHeight: 1 }}>{i + 1}</span>
                  <span>{s}</span>
                </div>
              ))}
            </div>
          ) : <Empty>Insights appear after a week of check-ins.</Empty>}
          <div className="divider" />
          <div className="row wrap">{d.top_tags.map(([t, n]: [string, number]) => <span key={t} className="chip">{t} <b className="num">{n}</b></span>)}</div>
          <p className="tiny faint" style={{ marginTop: 14 }}>Patterns, not diagnoses.</p>
        </div>
      </div>

      <div className="grid g-side" style={{ marginTop: 18 }}>
        <div className="card">
          <div className="card-head"><h3>Calm toolkit</h3><Link className="small" to="/toolkit">See all</Link></div>
          <div className="stack" style={{ gap: 10 }}>
            {["box_breathing", "grounding", "sleep_winddown"].map((id) => (
              <Link key={id} to={`/toolkit#${id}`} className="rec">
                <span className={`icon-tile ${EXERCISES[id].tone}`}>{EXERCISES[id].icon}</span>
                <span style={{ flex: 1 }}><b style={{ display: "block" }}>{EXERCISES[id].title}</b><span className="small faint">{EXERCISES[id].minutes} · {EXERCISES[id].best}</span></span>
              </Link>
            ))}
          </div>
        </div>
        <div className="card">
          <div className="card-head"><h3>Recent conversations</h3><Link to="/companion" className="small">New conversation</Link></div>
          {d.recent_sessions.length ? (
            <table className="t">
              <thead><tr><th>When</th><th>Mode</th><th>Tone</th><th>Distress</th><th>Tier</th></tr></thead>
              <tbody>
                {d.recent_sessions.slice(0, 6).map((s: any) => (
                  <tr key={s.id}>
                    <td>{timeAgo(s.started_at)}</td>
                    <td style={{ textTransform: "capitalize" }}>{s.mode}</td>
                    <td style={{ textTransform: "capitalize" }}>{s.emotion ?? "–"}</td>
                    <td className="num">{pct(s.distress)}</td>
                    <td><TierBadge tier={s.tier} /></td>
                  </tr>
                ))}
              </tbody>
            </table>
          ) : <Empty>No conversations yet.</Empty>}
        </div>
      </div>
    </div>
  );
}
