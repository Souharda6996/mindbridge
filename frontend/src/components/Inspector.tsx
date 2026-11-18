import type { ReactElement } from "react";
import { Area, AreaChart, ReferenceLine, ResponsiveContainer, YAxis } from "recharts";
import { Camera, Languages, Mic, Type, X } from "lucide-react";
import { EMO_COLORS, MOD_COLORS, pct, type FusionOut, type Tier } from "../api";
import { Bar, Gauge, TierBadge } from "./ui";

const ICON: Record<string, ReactElement> = { face: <Camera size={14} />, voice: <Mic size={14} />, text: <Type size={14} /> };
const LANG: Record<string, string> = { en: "English", hi: "Hindi", hinglish: "Hinglish", kn: "Kannada" };
const FACE_WORD: Record<string, string> = { happy: "joy", sad: "sadness", angry: "anger", fearful: "fear", disgusted: "disgust", surprised: "surprise", neutral: "neutral" };

export interface FaceLive { reliability: number; issue: string | null; top: string; cues: string[]; calibrated: boolean; calibration: number }

export default function Inspector({ fusion, tier, trajectory, reasons, provider, latency, faceLive, language, onClose }: {
  fusion: FusionOut | null; tier: Tier; trajectory: { smoothed: number }[]; reasons: string[];
  provider?: string; latency?: number; faceLive?: FaceLive | null; language?: string; onClose?: () => void;
}) {
  const mods = ["face", "voice", "text"];
  return (
    <aside className="inspector fade-in">
      <div className="card">
        <div className="card-head">
          <div>
            <div className="eyebrow gold">Live analysis</div>
            <h3 style={{ marginTop: 4 }}>How you seem right now</h3>
          </div>
          <div className="row" style={{ gap: 6 }}>
            <TierBadge tier={tier} />
            {onClose && <button className="icon-btn" style={{ width: 30, height: 30 }} onClick={onClose} aria-label="Hide analysis"><X size={14} /></button>}
          </div>
        </div>
        <Gauge value={fusion?.smoothed ?? 0} confidence={fusion?.confidence ?? 0} />
        <div className="divider" />
        <div className="row tiny faint" style={{ marginBottom: 10, fontWeight: 700, letterSpacing: "0.08em", textTransform: "uppercase" }}>
          <span style={{ width: 76 }}>Signal</span><span className="spacer">distress · reliability</span><span>weight</span>
        </div>
        <div className="stack" style={{ gap: 13 }}>
          {mods.map((m) => {
            const s = fusion?.modalities?.[m];
            const w = fusion?.weights?.[m] ?? 0;
            return (
              <div className="mod-row" key={m} style={{ opacity: s ? 1 : 0.4 }}>
                <span className="mod-name"><span style={{ color: MOD_COLORS[m] }}>{ICON[m]}</span>{m}</span>
                <div className="stack" style={{ gap: 4 }}>
                  <Bar value={s?.distress ?? 0} color={MOD_COLORS[m]} />
                  <Bar value={s?.reliability ?? 0} color="var(--ink-3)" height={3} />
                </div>
                <span className="num" style={{ textAlign: "right", fontWeight: 700 }}>{s ? pct(w) : "off"}</span>
              </div>
            );
          })}
        </div>
        {faceLive && (
          <div className="small faint" style={{ marginTop: 12 }}>
            {faceLive.calibrated ? <>Face reads <b style={{ color: "var(--ink)" }}>{FACE_WORD[faceLive.top] ?? faceLive.top}</b>
              {faceLive.cues.length > 0 && <> · {faceLive.cues.join(", ")}</>}</>
              : <>Learning your resting face… {Math.round(faceLive.calibration * 100)}%</>}
            {faceLive.issue && <> · <span style={{ color: "var(--amber)" }}>{faceLive.issue}</span></>}
          </div>
        )}
        {language && <div className="row small faint" style={{ marginTop: 8, gap: 6 }}><Languages size={13} />Replying in {LANG[language] ?? language}</div>}
      </div>

      <div className="card">
        <div className="card-head"><h3>Emotion blend</h3><span className="tiny faint">weighted by reliability</span></div>
        <div className="stack" style={{ gap: 9 }}>
          {Object.entries(fusion?.emotions ?? { neutral: 1 }).sort((a, b) => b[1] - a[1]).map(([k, v]) => (
            <div key={k} className="row small">
              <span style={{ width: 66, color: "var(--ink-2)", textTransform: "capitalize" }}>{k}</span>
              <div style={{ flex: 1 }}><Bar value={v} color={EMO_COLORS[k]} /></div>
              <span className="num faint" style={{ width: 38, textAlign: "right" }}>{pct(v)}</span>
            </div>
          ))}
        </div>
      </div>

      <div className="card">
        <div className="card-head"><h3>Trajectory</h3><span className="tiny faint">this session</span></div>
        <div style={{ height: 74 }}>
          {trajectory.length > 1 ? (
            <ResponsiveContainer>
              <AreaChart data={trajectory} margin={{ top: 4, right: 0, left: 0, bottom: 0 }}>
                <defs>
                  <linearGradient id="trajFill" x1="0" y1="0" x2="0" y2="1">
                    <stop offset="0%" stopColor="var(--gold)" stopOpacity={0.35} />
                    <stop offset="100%" stopColor="var(--gold)" stopOpacity={0} />
                  </linearGradient>
                </defs>
                <YAxis domain={[0, 1]} hide />
                <ReferenceLine y={0.6} stroke="var(--clay)" strokeOpacity={0.5} strokeDasharray="3 3" />
                <Area type="monotone" dataKey="smoothed" stroke="var(--gold)" fill="url(#trajFill)" strokeWidth={2} isAnimationActive={false} />
              </AreaChart>
            </ResponsiveContainer>
          ) : <p className="small faint">Appears after a couple of messages.</p>}
        </div>
        {(reasons.length > 0 || (fusion?.explanations?.length ?? 0) > 0) && (
          <>
            <div className="divider" />
            <div className="eyebrow" style={{ marginBottom: 8 }}>Why</div>
            <div className="stack" style={{ gap: 4 }}>
              {[...reasons, ...(fusion?.explanations ?? [])].filter((x, i, a) => a.indexOf(x) === i).slice(0, 6)
                .map((r, i) => <div key={i} className="reason">{r}</div>)}
            </div>
          </>
        )}
        {provider && <p className="tiny faint" style={{ marginTop: 14 }}>reply · {provider}{latency !== undefined ? ` · ${latency} ms` : ""}</p>}
      </div>
    </aside>
  );
}
