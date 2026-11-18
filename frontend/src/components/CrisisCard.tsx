import { useState } from "react";
import { Phone, ShieldAlert, UserRoundCheck } from "lucide-react";
import { api, type Helpline } from "../api";

export default function CrisisCard({ helplines, sessionId, alertId, reasons }:
  { helplines: Helpline[]; sessionId: string | null; alertId: number | null; reasons: string[] }) {
  const [notified, setNotified] = useState<string | null>(null);
  const [err, setErr] = useState<string | null>(null);

  const notify = async () => {
    try {
      const r = await api.notifyContact(sessionId, alertId);
      setNotified(r.recipient?.name ?? "your trusted contact");
    } catch (e) {
      setErr((e as Error).message);
    }
  };

  return (
    <div className="crisis fade-in">
      <div className="row" style={{ marginBottom: 6 }}>
        <ShieldAlert size={19} color="var(--clay)" />
        <h3>You don't have to go through this alone</h3>
      </div>
      <p className="small muted" style={{ marginBottom: 14 }}>
        Trained people are available right now, free and confidential. A campus counsellor has also been notified.
      </p>
      <div className="stack" style={{ gap: 8 }}>
        {helplines.map((h) => (
          <div className="helpline" key={h.number}>
            <div>
              <div style={{ fontWeight: 700 }}>{h.name}</div>
              <div className="faint small">{h.languages}{h.alt ? ` · also ${h.alt}` : ""}</div>
            </div>
            <a className="btn primary" href={`tel:${h.number}`}><Phone size={15} />{h.number}</a>
          </div>
        ))}
      </div>
      <div className="row wrap" style={{ marginTop: 14 }}>
        {notified ? (
          <span className="chip toggle on"><UserRoundCheck size={14} /> {notified} has been asked to check on you</span>
        ) : (
          <button className="btn" onClick={notify}><UserRoundCheck size={15} /> Let my trusted contact know</button>
        )}
        {err && <span className="small" style={{ color: "var(--clay)" }}>{err}</span>}
      </div>
      {reasons.length > 0 && (
        <details style={{ marginTop: 14 }}>
          <summary className="small faint" style={{ cursor: "pointer" }}>Why am I seeing this?</summary>
          <div className="stack" style={{ gap: 4, marginTop: 8 }}>
            {reasons.map((r, i) => <div key={i} className="reason">{r}</div>)}
          </div>
        </details>
      )}
    </div>
  );
}
