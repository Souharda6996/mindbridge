import { useEffect, useState } from "react";

/** The companion's visual presence: a lotus of light around a breathing orb.
 *
 *  - The orb breathes on a 10-second cycle (6 breaths per minute, the slow "resonance"
 *    pace used in breathing therapy) so simply looking at it gently paces the user.
 *  - The lotus (growth through difficulty, a familiar Indian symbol) opens while listening.
 *  - While speaking the core pulses with the voice; colour follows the conversation's tone.
 *  A faceless form avoids the uncanny or culturally-specific look of a cartoon face. */
export type Expression = "neutral" | "smile" | "soft" | "calm" | "steady" | "concerned";

const PALETTE: Record<Expression, [string, string, string]> = {
  //            core light            core deep         petal
  neutral:   ["#f3dfb4", "var(--accent)", "var(--gold)"],
  smile:     ["#f7e2a6", "#c08a2c", "#e0b65a"],
  soft:      ["#dfe8f3", "#4c719a", "#82a6cd"],
  calm:      ["#dcefe6", "#2a6b5c", "#82c2ad"],
  steady:    ["#ece6da", "#55645d", "#a8b0a8"],
  concerned: ["#f6dcd0", "#b4532e", "#e48b6c"],
};
const STATE_TEXT: Record<string, string> = { idle: "here with you", listening: "listening", speaking: "speaking", thinking: "reflecting" };

export default function Orb({ expression = "neutral", speaking = false, listening = false, thinking = false, size = 300, name }:
  { expression?: Expression; speaking?: boolean; listening?: boolean; thinking?: boolean; size?: number; name?: string }) {
  const [amp, setAmp] = useState(0);
  useEffect(() => {
    if (!speaking) { setAmp(0); return; }
    const id = window.setInterval(() => setAmp(0.2 + Math.random() * 0.8), 120);
    return () => clearInterval(id);
  }, [speaking]);

  const [light, deep, petal] = PALETTE[expression] ?? PALETTE.neutral;
  const open = listening ? 1.1 : speaking ? 1.03 + amp * 0.05 : 1;
  const state = speaking ? "speaking" : listening ? "listening" : thinking ? "thinking" : "idle";
  const petals = Array.from({ length: 8 }, (_, i) => i * 45);

  return (
    <div style={{ display: "grid", justifyItems: "center", gap: 10 }}>
      <svg width={size} height={size} viewBox="-150 -150 300 300" role="img" aria-label={`${name ?? "Companion"} is ${STATE_TEXT[state]}`}>
        <defs>
          <radialGradient id="orbCore" cx="38%" cy="32%" r="75%">
            <stop offset="0%" stopColor="#fffaf0" />
            <stop offset="28%" stopColor={light} />
            <stop offset="100%" stopColor={deep} />
          </radialGradient>
          <radialGradient id="orbGlow" cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={petal} stopOpacity="0.55" />
            <stop offset="100%" stopColor={petal} stopOpacity="0" />
          </radialGradient>
          <linearGradient id="petalFill" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor={petal} stopOpacity="0.55" />
            <stop offset="100%" stopColor={petal} stopOpacity="0.05" />
          </linearGradient>
        </defs>

        <circle r="140" fill="url(#orbGlow)" className="orb-glow" />
        {/* listening ripples */}
        {listening && [0, 1, 2].map((i) => (
          <circle key={i} r="70" fill="none" stroke={petal} strokeWidth="1.2" className="orb-ripple" style={{ animationDelay: `${i * 0.8}s` }} />
        ))}
        {/* lotus */}
        <g className="orb-lotus" style={{ transform: `scale(${open})`, transition: "transform 0.6s cubic-bezier(.2,.7,.2,1)" }}>
          {petals.map((a) => (
            <path key={a} transform={`rotate(${a})`} d="M0 -122 C 30 -96 34 -62 0 -40 C -34 -62 -30 -96 0 -122 Z"
              fill="url(#petalFill)" stroke={petal} strokeOpacity="0.55" strokeWidth="1" />
          ))}
          {petals.map((a) => (
            <path key={`i${a}`} transform={`rotate(${a + 22.5})`} d="M0 -96 C 20 -78 22 -58 0 -44 C -22 -58 -20 -78 0 -96 Z"
              fill="url(#petalFill)" stroke={petal} strokeOpacity="0.35" strokeWidth="0.8" />
          ))}
        </g>
        {/* breathing core */}
        <g className="orb-breath">
          <circle r={56 + amp * 5} fill="url(#orbCore)" style={{ transition: "r 0.12s" }} />
          <circle r="56" fill="none" stroke="#fff" strokeOpacity="0.35" strokeWidth="1" />
          <ellipse cx="-17" cy="-21" rx="17" ry="10" fill="#fff" opacity="0.32" transform="rotate(-30 -17 -21)" />
        </g>
        {thinking && (
          <g className="orb-think">
            {[0, 120, 240].map((a) => <circle key={a} r="3" cx="0" cy="-74" fill={petal} transform={`rotate(${a})`} />)}
          </g>
        )}
        <style>{`
          /* the viewBox is centred on (0,0); with the default view-box reference, "0 0" is that centre */
          .orb-breath { animation: orbBreath 10s ease-in-out infinite; transform-origin: 0 0; }
          .orb-lotus { transform-origin: 0 0; }
          .orb-glow { animation: orbGlow 10s ease-in-out infinite; }
          svg:hover .orb-lotus { filter: brightness(1.05); }
          .orb-ripple { animation: orbRipple 2.4s ease-out infinite; }
          .orb-think { animation: orbSpin 1.6s linear infinite; transform-origin: 0 0; }
          @keyframes orbBreath { 0%, 100% { transform: scale(0.94); } 50% { transform: scale(1.06); } }
          @keyframes orbGlow { 0%, 100% { opacity: 0.7; } 50% { opacity: 1; } }
          @keyframes orbRipple { from { r: 62px; opacity: 0.7; } to { r: 140px; opacity: 0; } }
          @keyframes orbSpin { to { transform: rotate(360deg); } }
          g.orb-lotus { animation: lotusTurn 90s linear infinite; }
          @keyframes lotusTurn { from { rotate: 0deg; } to { rotate: 360deg; } }
        `}</style>
      </svg>
      {name && (
        <div style={{ textAlign: "center", marginTop: -6 }}>
          <div className="serif" style={{ fontSize: 26, fontWeight: 600, lineHeight: 1 }}>{name}</div>
          <div className="eyebrow" style={{ marginTop: 6 }}>{STATE_TEXT[state]}</div>
        </div>
      )}
    </div>
  );
}
