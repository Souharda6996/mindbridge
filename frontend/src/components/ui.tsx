import { useEffect, useRef, useState, type ReactNode } from "react";
import type { Tier } from "../api";

export function TierBadge({ tier }: { tier: Tier | string }) {
  const label = tier === "HIGH" ? "High risk" : tier === "MEDIUM" ? "Medium" : "Low";
  return <span className={`tier ${tier}`}>{label}</span>;
}

export function Bar({ value, color, height = 6 }: { value: number; color: string; height?: number }) {
  return (
    <div className="bar" style={{ height }}>
      <i style={{ width: `${Math.max(0, Math.min(1, value)) * 100}%`, background: color }} />
    </div>
  );
}

export function Switch({ checked, onChange, label }: { checked: boolean; onChange: (v: boolean) => void; label?: string }) {
  return (
    <label className="switch" aria-label={label}>
      <input type="checkbox" checked={checked} onChange={(e) => onChange(e.target.checked)} />
      <span />
    </label>
  );
}

export function PageHead({ eyebrow, title, lede, right }: { eyebrow: string; title: ReactNode; lede?: ReactNode; right?: ReactNode }) {
  return (
    <div className="page-head fade-in">
      <div>
        <div className="eyebrow gold">{eyebrow}</div>
        <h1 style={{ marginTop: 8 }}>{title}</h1>
        {lede && <p className="lede">{lede}</p>}
      </div>
      {right && <div className="row wrap no-print">{right}</div>}
    </div>
  );
}

export function SectionHead({ num, title, lede }: { num: string; title: string; lede?: string }) {
  return (
    <div style={{ marginBottom: 18 }}>
      <div className="section-head">
        <span className="section-num">{num}</span>
        <h2>{title}</h2>
      </div>
      {lede && <p className="muted" style={{ maxWidth: 760 }}>{lede}</p>}
    </div>
  );
}

/** Animated number that counts up when it first appears. */
export function CountUp({ value, decimals = 0, duration = 900 }: { value: number | null | undefined; decimals?: number; duration?: number }) {
  const [shown, setShown] = useState(0);
  const from = useRef(0);
  useEffect(() => {
    if (value === null || value === undefined || Number.isNaN(value)) return;
    const start = performance.now();
    const a = from.current;
    let raf = 0;
    const step = (t: number) => {
      const k = Math.min(1, (t - start) / duration);
      const eased = 1 - Math.pow(1 - k, 3);
      setShown(a + (value - a) * eased);
      if (k < 1) raf = requestAnimationFrame(step);
      else from.current = value;
    };
    raf = requestAnimationFrame(step);
    return () => cancelAnimationFrame(raf);
  }, [value, duration]);
  if (value === null || value === undefined || Number.isNaN(value)) return <>–</>;
  return <>{shown.toFixed(decimals)}</>;
}

/** Circular progress ring (wellbeing score). */
export function Ring({ value, size = 168, stroke = 12, children }: { value: number; size?: number; stroke?: number; children?: ReactNode }) {
  const r = (size - stroke) / 2;
  const c = 2 * Math.PI * r;
  const [v, setV] = useState(0);
  useEffect(() => { const id = requestAnimationFrame(() => setV(Math.max(0, Math.min(1, value)))); return () => cancelAnimationFrame(id); }, [value]);
  return (
    <div className="ring-wrap" style={{ width: size, height: size }}>
      <svg width={size} height={size} style={{ transform: "rotate(-90deg)" }}>
        <defs>
          <linearGradient id="ringGrad" x1="0" y1="0" x2="1" y2="1">
            <stop offset="0%" stopColor="var(--gold)" />
            <stop offset="100%" stopColor="var(--accent)" />
          </linearGradient>
        </defs>
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="var(--surface-3)" strokeWidth={stroke} />
        <circle cx={size / 2} cy={size / 2} r={r} fill="none" stroke="url(#ringGrad)" strokeWidth={stroke} strokeLinecap="round"
          strokeDasharray={c} strokeDashoffset={c * (1 - v)} style={{ transition: "stroke-dashoffset 1.4s cubic-bezier(.2,.7,.2,1)" }} />
      </svg>
      <div className="ring-label">{children}</div>
    </div>
  );
}

/** Semi-circular gauge for fused distress. */
export function Gauge({ value, confidence, size = 220 }: { value: number; confidence: number; size?: number }) {
  const v = Math.max(0, Math.min(1, value));
  const r = size / 2 - 14;
  const cx = size / 2, cy = size / 2;
  const arc = (from: number, to: number) => {
    const a0 = Math.PI * (1 - from), a1 = Math.PI * (1 - to);
    return `M ${cx + r * Math.cos(a0)} ${cy - r * Math.sin(a0)} A ${r} ${r} 0 0 1 ${cx + r * Math.cos(a1)} ${cy - r * Math.sin(a1)}`;
  };
  const color = v >= 0.6 ? "var(--clay)" : v >= 0.35 ? "var(--amber)" : "var(--good)";
  const label = v >= 0.6 ? "elevated" : v >= 0.35 ? "moderate" : "calm";
  return (
    <svg width="100%" viewBox={`0 0 ${size} ${size / 2 + 34}`} role="img" aria-label={`Fused distress ${Math.round(v * 100)} percent`}>
      <path d={arc(0, 1)} stroke="var(--surface-3)" strokeWidth="14" fill="none" strokeLinecap="round" />
      <path d={arc(0.6, 1)} stroke="var(--clay-soft)" strokeWidth="14" fill="none" />
      {v > 0.005 && <path d={arc(0, v)} stroke={color} strokeWidth="14" fill="none" strokeLinecap="round" style={{ transition: "all 0.6s ease" }} />}
      <text x={cx} y={cy - 6} textAnchor="middle" fontFamily="var(--serif)" fontWeight="500" fontSize="46" fill="var(--ink)">{Math.round(v * 100)}</text>
      <text x={cx} y={cy + 15} textAnchor="middle" fontFamily="var(--sans)" fontWeight="700" fontSize="9.5" letterSpacing="1.6" fill="var(--ink-3)">
        {label.toUpperCase()} · CONFIDENCE {Math.round(confidence * 100)}%
      </text>
      <text x={14} y={cy + 30} fontFamily="var(--sans)" fontSize="10" fill="var(--ink-3)">0</text>
      <text x={size - 14} y={cy + 30} textAnchor="end" fontFamily="var(--sans)" fontSize="10" fill="var(--ink-3)">100</text>
    </svg>
  );
}

export function Empty({ children }: { children: ReactNode }) {
  return <div className="faint small" style={{ padding: "22px 0", textAlign: "center" }}>{children}</div>;
}

/** Shared tooltip style for Recharts that follows the theme. */
export const tooltipStyle = {
  contentStyle: { background: "var(--surface)", border: "1px solid var(--line)", borderRadius: 12, fontSize: 12, boxShadow: "var(--shadow)" },
  labelStyle: { color: "var(--ink)", fontWeight: 700 },
  itemStyle: { color: "var(--ink-2)" },
};
export const axisTick = { fontSize: 11, fill: "var(--ink-3)" };
