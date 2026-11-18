import { useEffect, useRef, useState } from "react";
import { CheckCircle2, Eye, MessageCircleWarning, PhoneCall, UserRoundCheck } from "lucide-react";
import { api, pct, timeAgo } from "../api";
import { Empty, PageHead, TierBadge } from "../components/ui";

const FILTERS = ["open", "new", "acknowledged", "resolved", "all"] as const;
const SOURCE: Record<string, string> = {
  escalation: "Automatic escalation", user_request: "Student asked for a counsellor", journal: "Mood-journal note",
};

export default function Counselor() {
  const [alerts, setAlerts] = useState<any[]>([]);
  const [filter, setFilter] = useState<(typeof FILTERS)[number]>("open");
  const [notes, setNotes] = useState<Record<number, string>>({});
  const [outbox, setOutbox] = useState<any[]>([]);
  const seen = useRef<Set<number>>(new Set());
  const [fresh, setFresh] = useState<Set<number>>(new Set());

  const load = async () => {
    const a = await api.alerts();
    const newIds = a.filter((x) => !seen.current.has(x.id)).map((x) => x.id);
    if (seen.current.size > 0 && newIds.length) setFresh(new Set(newIds));
    a.forEach((x) => seen.current.add(x.id));
    setAlerts(a);
    api.notifications().then(setOutbox).catch(() => {});
  };
  useEffect(() => {
    load().catch(() => {});
    const id = setInterval(() => load().catch(() => {}), 4000);
    return () => clearInterval(id);
  }, []);

  const update = async (id: number, status: string) => {
    await api.updateAlert(id, status, notes[id]);
    load();
  };

  const shown = alerts.filter((a) => filter === "all" ? true : filter === "open" ? a.status !== "resolved" : a.status === filter);
  const counts = {
    new: alerts.filter((a) => a.status === "new").length,
    high: alerts.filter((a) => a.tier === "HIGH" && a.status !== "resolved").length,
    resolved: alerts.filter((a) => a.status === "resolved").length,
  };

  return (
    <div>
      <PageHead eyebrow="Care team · campus counsellor view" title={<>Counsellor <em className="gold">console</em></>}
        lede="Alerts arrive here in real time with the reasons behind them, so a human can decide what to do. The AI never handles a crisis alone." />

      <div className="grid g-3 reveal" style={{ marginBottom: 18 }}>
        <div className="card kpi"><div className="label"><MessageCircleWarning size={14} />New alerts</div><div className="value">{counts.new}</div></div>
        <div className="card kpi"><div className="label"><PhoneCall size={14} />High-risk, unresolved</div><div className="value" style={{ color: counts.high ? "var(--clay)" : undefined }}>{counts.high}</div></div>
        <div className="card kpi"><div className="label"><CheckCircle2 size={14} />Resolved</div><div className="value">{counts.resolved}</div></div>
      </div>

      <div className="row" style={{ marginBottom: 14 }}>
        <div className="seg">
          {FILTERS.map((f) => <button key={f} className={filter === f ? "on" : ""} onClick={() => setFilter(f)} style={{ textTransform: "capitalize" }}>{f}</button>)}
        </div>
        <span className="spacer" />
        <span className="small faint">Refreshes every 4 seconds</span>
      </div>

      <div className="grid g-main" style={{ alignItems: "start" }}>
        <div className="stack">
          {shown.length === 0 && <div className="card"><Empty>No alerts in this view.</Empty></div>}
          {shown.map((a) => (
            <div key={a.id} className={`alert-card ${a.status} fade-in`}
              style={fresh.has(a.id) ? { boxShadow: "0 0 0 3px var(--clay-tint)" } : undefined}>
              <div className="row" style={{ marginBottom: 10 }}>
                <TierBadge tier={a.tier} />
                <span style={{ fontWeight: 600 }}>{SOURCE[a.source] ?? a.source}</span>
                <span className="faint small">· {timeAgo(a.created_at)}</span>
                {a.demo && <span className="chip">sample</span>}
                <span className="spacer" />
                <span className="chip" style={{ textTransform: "capitalize" }}>{a.status}</span>
              </div>
              {a.excerpt && <p className="quote" style={{ marginBottom: 12 }}>"{a.excerpt}"</p>}
              <div className="eyebrow" style={{ marginBottom: 6 }}>Why this was flagged</div>
              <div className="stack" style={{ gap: 4, marginBottom: 12 }}>
                {a.reasons.map((r: string, i: number) => <div key={i} className="reason">{r}</div>)}
              </div>
              <div className="row wrap small faint" style={{ marginBottom: 12, gap: 14 }}>
                {a.session && <span>Session: {a.session.mode} · {a.session.turns} turns · avg distress {pct(a.session.avg_distress)}</span>}
                {a.contact_notified ? <span className="row" style={{ gap: 4, color: "var(--accent)" }}><UserRoundCheck size={13} />trusted contact informed</span> : null}
              </div>
              {a.note && <p className="small" style={{ marginBottom: 10 }}><b>Counsellor note:</b> {a.note}</p>}
              {a.status !== "resolved" && (
                <div className="row wrap">
                  <input className="input" style={{ flex: 1, minWidth: 220 }} placeholder="Add a note (e.g. called student, follow-up booked)"
                    value={notes[a.id] ?? ""} onChange={(e) => setNotes({ ...notes, [a.id]: e.target.value })} />
                  {a.status === "new" && <button className="btn" onClick={() => update(a.id, "acknowledged")}><Eye size={15} />Acknowledge</button>}
                  <button className="btn primary" onClick={() => update(a.id, "resolved")}><CheckCircle2 size={15} />Resolve</button>
                </div>
              )}
            </div>
          ))}
        </div>

        <div className="stack">
          <div className="card">
            <div className="card-head"><h3>Escalation protocol</h3></div>
            <div className="stack small" style={{ gap: 10 }}>
              <div><TierBadge tier="LOW" /><p className="muted" style={{ marginTop: 4 }}>Supportive conversation and coping exercises.</p></div>
              <div><TierBadge tier="MEDIUM" /><p className="muted" style={{ marginTop: 4 }}>Hopelessness language or sustained high distress: gentler tone, check-in prompt, counsellor offered, non-urgent alert.</p></div>
              <div><TierBadge tier="HIGH" /><p className="muted" style={{ marginTop: 4 }}>Death wish, ideation, self-harm or a plan: fixed safety script, helplines shown, trusted contact offered, urgent alert here. Stays on until a counsellor resolves it.</p></div>
            </div>
          </div>
          <div className="card">
            <div className="card-head"><h3>Trusted-contact outbox</h3><span className="small faint">simulated</span></div>
            {outbox.length ? outbox.slice(0, 5).map((n) => (
              <div key={n.id} style={{ padding: "8px 0", borderTop: "1px solid var(--line-2)" }}>
                <div className="small"><b>{n.recipient}</b> <span className="faint">· {n.channel} · {timeAgo(n.created_at)}</span></div>
                <div className="small muted">{n.message}</div>
              </div>
            )) : <Empty>No contacts notified.</Empty>}
          </div>
        </div>
      </div>
    </div>
  );
}
