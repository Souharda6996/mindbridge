import { useEffect, useState } from "react";
import { Area, AreaChart, CartesianGrid, ResponsiveContainer, XAxis, YAxis } from "recharts";
import { Printer } from "lucide-react";
import { api, pct } from "../api";
import { axisTick, PageHead, TierBadge } from "../components/ui";
import { LotusMark } from "../components/Layout";

export default function Report() {
  const [r, setR] = useState<any>(null);
  const [days, setDays] = useState(30);
  useEffect(() => { api.report(days).then(setR); }, [days]);
  if (!r) return <div className="skeleton" style={{ height: 400 }} />;
  const k = r.dashboard.kpis;

  return (
    <div>
      <PageHead eyebrow="Shareable summary" title="Therapist report"
        lede={`Prepared for ${r.profile?.name ?? "the student"} · last ${r.period_days} days · generated ${new Date(r.generated_at).toLocaleString("en-IN")}`}
        right={<>
          <select className="select" style={{ width: 120 }} value={days} onChange={(e) => setDays(Number(e.target.value))}>
            <option value={14}>14 days</option><option value={30}>30 days</option><option value={60}>60 days</option>
          </select>
          <button className="btn primary" onClick={() => window.print()}><Printer size={15} />Print / save as PDF</button>
        </>} />

      <div className="reveal">
        <div className="row" style={{ gap: 14, marginBottom: 18 }}>
          <LotusMark size={40} />
          <div><div className="serif" style={{ fontSize: 22, fontWeight: 600 }}>MindBridge wellbeing summary</div>
            <div className="small faint">Shared with consent · not a diagnosis</div></div>
        </div>
        <div className="grid g-4">
          {[["Average mood (7 d)", `${k.avg_mood_7d ?? "–"}`, "/ 10"], ["Average sleep (7 d)", `${k.avg_sleep_7d ?? "–"}`, "h"],
            ["Average anxiety (7 d)", `${k.avg_anxiety_7d ?? "–"}`, "/ 10"], ["Support sessions", `${k.sessions}`, ""]].map(([l, v, u]) => (
            <div key={l} className="card kpi"><div className="label">{l}</div><div className="value" style={{ fontSize: 36 }}>{v}<small>{u}</small></div></div>
          ))}
        </div>

        <div className="card" style={{ marginTop: 18 }}>
          <div className="card-head"><h3>Mood trend</h3></div>
          <div style={{ height: 210 }}>
            <ResponsiveContainer>
              <AreaChart data={r.dashboard.mood_series} margin={{ top: 4, right: 4, left: -20, bottom: 0 }}>
                <CartesianGrid stroke="var(--grid)" vertical={false} />
                <XAxis dataKey="day" tick={axisTick} axisLine={false} tickLine={false} minTickGap={30} />
                <YAxis domain={[0, 10]} tick={axisTick} axisLine={false} tickLine={false} />
                <Area dataKey="mood" stroke="var(--accent)" fill="var(--accent-soft)" strokeWidth={2} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          </div>
        </div>

        <div className="grid g-2" style={{ marginTop: 18 }}>
          <div className="card">
            <div className="card-head"><h3>Observed patterns</h3></div>
            <div className="stack">
              {r.dashboard.insights.map((s: string, i: number) => (
                <div key={i} className="row top"><span className="serif italic gold" style={{ fontSize: 22, lineHeight: 1 }}>{i + 1}</span><span>{s}</span></div>
              ))}
            </div>
            <div className="divider" />
            <p className="small muted">{r.dashboard.distress_series.length} support sessions; {r.dashboard.distress_series.filter((s: any) => s.distress >= 0.6).length} above the
              sustained-distress threshold. Most recent: {pct(k.latest_distress)}.</p>
          </div>
          <div className="card">
            <div className="card-head"><h3>Journal excerpts</h3><span className="tiny faint">shared by the student</span></div>
            <div className="stack" style={{ gap: 12 }}>
              {r.journal_excerpts.map((j: any, i: number) => (
                <div key={i}><div className="tiny faint">{j.day} · mood {j.mood}</div><div className="quote" style={{ fontSize: 17 }}>{j.note}</div></div>
              ))}
            </div>
          </div>
        </div>

        <div className="card" style={{ marginTop: 18 }}>
          <div className="card-head"><h3>Safety events</h3></div>
          <table className="t">
            <thead><tr><th>Date</th><th>Tier</th><th>Status</th><th>Reasons</th></tr></thead>
            <tbody>
              {r.alerts.map((a: any, i: number) => (
                <tr key={i}><td className="num">{a.created_at.slice(0, 10)}</td><td><TierBadge tier={a.tier} /></td>
                  <td style={{ textTransform: "capitalize" }}>{a.status}</td><td className="small">{a.reasons.join(" · ")}</td></tr>
              ))}
            </tbody>
          </table>
        </div>
        <p className="small faint" style={{ marginTop: 18 }}>{r.disclaimer}</p>
      </div>
    </div>
  );
}
