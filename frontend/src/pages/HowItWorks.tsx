import { useEffect, useRef, useState } from "react";
import { Play, Search } from "lucide-react";
import { api, MOD_COLORS, pct, type FusionOut } from "../api";
import { Bar, Gauge, PageHead, SectionHead, Switch, TierBadge } from "../components/ui";
import { useApp } from "../components/Layout";
import Orb from "../components/Orb";

type Mod = { on: boolean; distress: number; reliability: number };
const PRESETS: Record<string, Record<string, Mod>> = {
  "Good conditions": { face: { on: true, distress: 0.7, reliability: 0.9 }, voice: { on: true, distress: 0.65, reliability: 0.85 }, text: { on: true, distress: 0.6, reliability: 0.9 } },
  "Dark room": { face: { on: true, distress: 0.1, reliability: 0.05 }, voice: { on: true, distress: 0.7, reliability: 0.85 }, text: { on: true, distress: 0.75, reliability: 0.9 } },
  "Noisy room": { face: { on: true, distress: 0.65, reliability: 0.85 }, voice: { on: true, distress: 0.1, reliability: 0.1 }, text: { on: true, distress: 0.7, reliability: 0.9 } },
  "One-word reply": { face: { on: true, distress: 0.8, reliability: 0.9 }, voice: { on: true, distress: 0.75, reliability: 0.8 }, text: { on: true, distress: 0.1, reliability: 0.25 } },
  "Smiling, sad words": { face: { on: true, distress: 0.05, reliability: 0.9 }, voice: { on: true, distress: 0.6, reliability: 0.8 }, text: { on: true, distress: 0.85, reliability: 0.95 } },
  "Camera off": { face: { on: false, distress: 0.5, reliability: 0.5 }, voice: { on: false, distress: 0.5, reliability: 0.5 }, text: { on: true, distress: 0.7, reliability: 0.9 } },
};

const AU_TABLE: [string, string, string][] = [
  ["AU4", "Brow lowerer", "anger, concentration, sadness"], ["AU1 / AU2", "Inner / outer brow raiser", "sadness, fear, surprise"],
  ["AU12", "Lip-corner puller", "joy"], ["AU15", "Lip-corner depressor", "sadness, disgust"], ["AU24", "Lip pressor", "anger"],
  ["AU5 / AU7", "Lid raiser / tightener", "fear, surprise / anger"], ["AU26", "Jaw drop", "surprise, fear"], ["AU10", "Upper-lip raiser", "disgust"],
];

export default function HowItWorks() {
  const { companion } = useApp();
  const [mods, setMods] = useState<Record<string, Mod>>(PRESETS["Good conditions"]);
  const [preset, setPreset] = useState("Good conditions");
  const [sim, setSim] = useState<FusionOut | null>(null);
  const [evalData, setEvalData] = useState<any>(null);
  const [running, setRunning] = useState(false);
  const [showAll, setShowAll] = useState(false);
  const [probe, setProbe] = useState("I feel like everyone would be better off without me");
  const [probeOut, setProbeOut] = useState<any>(null);
  const timer = useRef<number | undefined>(undefined);

  useEffect(() => {
    clearTimeout(timer.current);
    timer.current = window.setTimeout(() => {
      const body: Record<string, unknown> = {};
      for (const [k, m] of Object.entries(mods)) if (m.on) body[k] = { distress: m.distress, reliability: m.reliability };
      api.simulate(body).then(setSim).catch(() => {});
    }, 120);
  }, [mods]);

  const NOVELTY: [string, string][] = [
    ["Reliability-weighted multimodal fusion", "Face, voice and text are each scored for how trustworthy they are right now (lighting, head pose, noise, speech length, message length, model confidence, signal age). The estimate leans on whatever is reliable, so it degrades gracefully instead of failing when the camera is dark or the room is noisy."],
    ["Personalised face reading with action units", "Instead of trusting a generic expression network, MindBridge first learns each person's resting face, then measures changes from it, and cross-checks the network with Facial Action Units (FACS) measured from 68 landmarks. A naturally 'smiley' resting face no longer reads as joy, and anger shows up as lowered brows and pressed lips."],
    ["Truly multilingual: emotion, risk and replies", "English, Hindi (Devanagari), Hinglish and Kannada: a multilingual XLM-RoBERTa emotion model, C-SSRS-graded crisis rules with negation and idiom handling, and replies always in the language the student used."],
    ["Explainable, tiered human-in-the-loop escalation", "A deterministic LOW / MEDIUM / HIGH protocol with plain-language reasons. Language alone can trigger HIGH; distress alone only MEDIUM. In HIGH the LLM is switched off in favour of a fixed safety script, helplines and a live counsellor alert."],
    ["A conversation that moves forward", `${companion} never repeats a sentence in a session, recognises short answers ("yes", "no", "I don't know"), and moves through validate, explore, cope and plan, offering each exercise once.`],
    ["A presence that breathes with you", "The companion is a lotus of light whose core breathes at 6 breaths per minute, the slow resonance pace used in breathing therapy, gently pacing the student without any instruction."],
    ["Choice-based modality switching", `If the camera shows the student repeatedly looking away or leaving the frame, ${companion} offers to continue by text. Comfort comes before data.`],
  ];

  const runEval = async () => { setRunning(true); try { setEvalData(await api.evaluate()); } finally { setRunning(false); } };
  const runProbe = async (t = probe) => setProbeOut(await api.analyzeText(t));
  useEffect(() => { runProbe().catch(() => {}); }, []);

  const set = (m: string, k: keyof Mod, v: number | boolean) => { setPreset(""); setMods({ ...mods, [m]: { ...mods[m], [k]: v } }); };
  const c = evalData?.crisis, s = evalData?.safety_filter, e = evalData?.emotion;
  const LANGN: Record<string, string> = { en: "English", hinglish: "Hinglish", hi: "Hindi", kn: "Kannada" };

  return (
    <div>
      <PageHead eyebrow="Project explainer" title={<>How <em className="gold">MindBridge</em> works</>}
        lede="A multimodal AI companion for emotional support and distress-risk triage. Everything on this page runs live against the real system." />

      <div className="hero reveal">
        <div className="grid" style={{ gridTemplateColumns: "minmax(0,1fr) auto", gap: 24, alignItems: "center" }}>
          <div className="grid g-3" style={{ gap: 24 }}>
            <div><div className="eyebrow gold">Problem</div><p style={{ marginTop: 8 }}>Stigma, cost and a shortage of counsellors stop students from seeking help early. Distress often goes unnoticed until it becomes a crisis.</p></div>
            <div><div className="eyebrow gold">Approach</div><p style={{ marginTop: 8 }}>A private, always-available first line of support that listens through text or video, estimates distress from three signals, and escalates to people when needed.</p></div>
            <div><div className="eyebrow gold">Principle</div><p style={{ marginTop: 8 }}>A bridge to professional care, not a replacement. Deterministic safety, explainable decisions, consent for everything.</p></div>
          </div>
          <Orb size={150} />
        </div>
      </div>

      <section className="section">
        <SectionHead num="i." title="Architecture" lede="Signals flow left to right. Each box is a real module in the codebase." />
        <div className="pipeline reveal">
          <div className="pipe-col">
            <div className="pipe-box" style={{ borderLeft: `3px solid ${MOD_COLORS.face}` }}><b>Face</b>SSD-MobileNet + 68 landmarks + expression CNN, in the browser. Personal baseline + action units.</div>
            <div className="pipe-box" style={{ borderLeft: `3px solid ${MOD_COLORS.voice}` }}><b>Voice</b>wav2vec2 (IEMOCAP) + prosody: pauses, pitch flatness, energy, tremor, rate.</div>
            <div className="pipe-box" style={{ borderLeft: `3px solid ${MOD_COLORS.text}` }}><b>Text</b>RoBERTa-GoEmotions (English) · XLM-EMO (Hindi, Kannada, Hinglish) · C-SSRS rules.</div>
          </div>
          <div className="pipe-arrow">→</div>
          <div className="pipe-col">
            <div className="pipe-box"><b>Reliability-weighted fusion</b>w = trust × reliability × freshness → distress, confidence, trajectory.</div>
            <div className="pipe-box"><b>Crisis detector</b>Severity 0-4 in four languages, negation and idiom aware. Runs first.</div>
          </div>
          <div className="pipe-arrow">→</div>
          <div className="pipe-col">
            <div className="pipe-box"><b>Escalation engine</b>Deterministic LOW / MEDIUM / HIGH with reasons. Sticky HIGH until a counsellor resolves it.</div>
            <div className="pipe-box"><b>Conversation engine</b>Free LLM chain (Groq → Gemini → Ollama) or staged offline engine, replying in the user's language. Safety filter on every reply.</div>
          </div>
          <div className="pipe-arrow">→</div>
          <div className="pipe-col">
            <div className="pipe-box"><b>{companion}</b>Text or spoken reply with the breathing-lotus presence; coping exercises.</div>
            <div className="pipe-box"><b>Care team</b>Counsellor console, trusted-contact alert, therapist report.</div>
            <div className="pipe-box"><b>You</b>Home dashboard, mood journal, calm toolkit.</div>
          </div>
        </div>
      </section>

      <section className="section">
        <SectionHead num="ii." title="What is new here" />
        <div className="card reveal">
          {NOVELTY.map(([t, d], i) => (
            <div key={t} className="novel" style={i === 0 ? { borderTop: 0, paddingTop: 4 } : undefined}>
              <span className="n">{i + 1}</span>
              <div><h3>{t}</h3><p className="muted" style={{ marginTop: 4 }}>{d}</p></div>
            </div>
          ))}
        </div>
      </section>

      <section className="section">
        <SectionHead num="iii." title="Fusion playground" lede="Move the sliders or pick a scenario. The weights come from the same fusion code the companion uses." />
        <div className="row wrap" style={{ marginBottom: 14 }}>
          {Object.keys(PRESETS).map((p) => <button key={p} className={`chip toggle ${preset === p ? "on" : ""}`} onClick={() => { setPreset(p); setMods(PRESETS[p]); }}>{p}</button>)}
        </div>
        <div className="grid g-main">
          <div className="card">
            <div className="stack" style={{ gap: 20 }}>
              {(["face", "voice", "text"] as const).map((m) => (
                <div key={m}>
                  <div className="row" style={{ marginBottom: 8 }}>
                    <i className="sw" style={{ background: MOD_COLORS[m] }} /><b style={{ textTransform: "capitalize" }}>{m}</b>
                    <span className="spacer" /><span className="small faint">present</span>
                    <Switch checked={mods[m].on} onChange={(v) => set(m, "on", v)} label={`${m} present`} />
                  </div>
                  <div className="grid g-2" style={{ opacity: mods[m].on ? 1 : 0.4 }}>
                    <label className="field">Distress <span className="num">{pct(mods[m].distress)}</span>
                      <input type="range" min={0} max={1} step={0.01} value={mods[m].distress} disabled={!mods[m].on} onChange={(ev) => set(m, "distress", Number(ev.target.value))} /></label>
                    <label className="field">Reliability <span className="num">{pct(mods[m].reliability)}</span>
                      <input type="range" min={0} max={1} step={0.01} value={mods[m].reliability} disabled={!mods[m].on} onChange={(ev) => set(m, "reliability", Number(ev.target.value))} /></label>
                  </div>
                </div>
              ))}
            </div>
          </div>
          <div className="card">
            <Gauge value={sim?.fused ?? 0} confidence={sim?.confidence ?? 0} />
            <div className="eyebrow" style={{ margin: "10px 0" }}>Weight given to each signal</div>
            <div className="stack" style={{ gap: 10 }}>
              {(["face", "voice", "text"] as const).map((m) => (
                <div key={m} className="row small">
                  <span style={{ width: 46, textTransform: "capitalize" }}>{m}</span>
                  <div style={{ flex: 1 }}><Bar value={sim?.weights?.[m] ?? 0} color={MOD_COLORS[m]} height={9} /></div>
                  <span className="num" style={{ width: 42, textAlign: "right", fontWeight: 700 }}>{pct(sim?.weights?.[m] ?? 0)}</span>
                </div>
              ))}
            </div>
            <p className="small faint" style={{ marginTop: 14 }}>
              Plain averaging would give {pct(Object.values(mods).filter((m) => m.on).reduce((a, m, _, arr) => a + m.distress / arr.length, 0))}.
              Fusion gives {pct(sim?.fused ?? 0)} because it discounts unreliable signals.
            </p>
          </div>
        </div>
      </section>

      <section className="section">
        <SectionHead num="iv." title="How the face is read" lede="Four steps, all inside the browser. Only seven emotion probabilities and a reliability score are ever sent to the server." />
        <div className="grid g-2">
          <div className="card stack" style={{ gap: 14 }}>
            {[["Detect", "SSD-MobileNet finds the face; 68 landmarks map brows, eyes, nose and lips."],
              ["Calibrate", "For the first ~4 seconds the system learns your resting face (expression mix and geometry)."],
              ["Measure", "The expression CNN is read relative to your baseline, and Facial Action Units are measured from the landmarks."],
              ["Combine and smooth", "CNN and action units are blended (less weight on geometry when the head is turned), then smoothed over time."]].map(([t, d], i) => (
              <div key={t} className="row top" style={{ gap: 14 }}>
                <span className="serif italic gold" style={{ fontSize: 26, lineHeight: 1, width: 18 }}>{i + 1}</span>
                <div><b>{t}</b><p className="small muted">{d}</p></div>
              </div>
            ))}
          </div>
          <div className="card">
            <table className="t">
              <thead><tr><th>Action unit</th><th>Muscle movement</th><th>Signals</th></tr></thead>
              <tbody>{AU_TABLE.map(([a, m, s]) => <tr key={a}><td><b>{a}</b></td><td>{m}</td><td className="small muted">{s}</td></tr>)}</tbody>
            </table>
          </div>
        </div>
      </section>

      <section className="section">
        <SectionHead num="v." title="Try the language analysis" lede="Type anything in English, Hinglish, Hindi or Kannada to see the emotion models and the crisis detector at work." />
        <div className="card">
          <div className="row">
            <input className="input" value={probe} onChange={(ev) => setProbe(ev.target.value)} onKeyDown={(ev) => ev.key === "Enter" && runProbe()} />
            <button className="btn primary" onClick={() => runProbe()}><Search size={15} />Analyse</button>
          </div>
          <div className="row wrap" style={{ marginTop: 10 }}>
            {["This exam is killing me", "I would never kill myself, just exhausted", "मुझे बहुत गुस्सा आ रहा है", "ab jeene ka mann nahi karta", "I got placed today!!", "ನನಗೆ ತುಂಬಾ ಭಯವಾಗುತ್ತಿದೆ"].map((t) => (
              <button key={t} className="chip toggle" onClick={() => { setProbe(t); runProbe(t); }}>{t}</button>
            ))}
          </div>
          {probeOut && (
            <div className="grid g-2 fade-in" style={{ marginTop: 18 }}>
              <div>
                <div className="row" style={{ marginBottom: 8 }}><span className="eyebrow">Crisis detector</span><TierBadge tier={probeOut.risk.tier} /></div>
                <p><b>Level {probeOut.risk.level}</b> · {probeOut.risk.level_name}</p>
                <div className="stack" style={{ gap: 4, marginTop: 8 }}>
                  {probeOut.risk.reasons.map((r: any, i: number) => <div key={i} className="reason">{r.rule}: "{r.matched}"{r.negated ? " (negated)" : ""} <span className="faint">[{r.lang}]</span></div>)}
                  {probeOut.risk.idioms_ignored.map((x: string) => <div key={x} className="reason">Idiom ignored: "{x}"</div>)}
                  {!probeOut.risk.reasons.length && !probeOut.risk.idioms_ignored.length && <span className="small faint">No risk language found.</span>}
                </div>
              </div>
              <div>
                <div className="row" style={{ marginBottom: 8 }}><span className="eyebrow">Emotion</span><span className="chip">{probeOut.emotion.engine}</span>
                  <span className="chip gold">{LANGN[probeOut.emotion.language] ?? probeOut.emotion.language}</span></div>
                <div className="stack" style={{ gap: 7 }}>
                  {Object.entries(probeOut.emotion.emotions as Record<string, number>).sort((a, b) => b[1] - a[1]).map(([label, score]) => (
                    <div key={label} className="row small"><span style={{ width: 70, textTransform: "capitalize" }}>{label}</span>
                      <div style={{ flex: 1 }}><Bar value={score} color={`var(--e-${label})`} /></div><span className="num faint" style={{ width: 40, textAlign: "right" }}>{pct(score)}</span></div>
                  ))}
                </div>
                <p className="small muted" style={{ marginTop: 8 }}>Text distress {pct(probeOut.emotion.distress)} · reliability {pct(probeOut.emotion.reliability)}</p>
                {probeOut.emotion.explanations?.map((x: string) => <div key={x} className="reason" style={{ marginTop: 6 }}>{x}</div>)}
              </div>
            </div>
          )}
        </div>
      </section>

      <section className="section">
        <SectionHead num="vi." title="Live evaluation" lede="Runs the labelled crisis set (63 messages, 4 languages, incl. idiom traps), the emotion set (46 sentences, 4 languages) and a red-team set of unsafe replies through the real system." />
        <button className="btn primary lg" onClick={runEval} disabled={running}><Play size={15} />{running ? "Running…" : "Run evaluation"}</button>
        {c && s && (
          <div className="fade-in" style={{ marginTop: 18 }}>
            <div className="grid g-4 reveal">
              <div className="card kpi"><div className="label">High-risk recall</div><div className="value">{pct(c.high_recall, 1)}</div><div className="delta flat">no crisis missed</div></div>
              <div className="card kpi"><div className="label">High-risk precision</div><div className="value">{pct(c.high_precision, 1)}</div><div className="delta flat">false alarms avoided</div></div>
              <div className="card kpi"><div className="label">Text-emotion accuracy</div><div className="value">{e ? pct(e.accuracy, 1) : "n/a"}</div><div className="delta flat">{e ? `${e.total} sentences, 4 languages` : "model still loading"}</div></div>
              <div className="card kpi"><div className="label">Unsafe replies blocked</div><div className="value">{s.unsafe_blocked}/{s.unsafe_total}</div><div className="delta flat">{s.safe_passed}/{s.safe_total} safe replies passed</div></div>
            </div>
            <div className="grid g-3" style={{ marginTop: 18 }}>
              <div className="card">
                <div className="card-head"><h3>Crisis confusion matrix</h3><span className="tiny faint">rows = expected</span></div>
                <table className="t matrix">
                  <thead><tr><th></th>{["LOW", "MEDIUM", "HIGH"].map((t) => <th key={t}>{t}</th>)}</tr></thead>
                  <tbody>{["LOW", "MEDIUM", "HIGH"].map((ex) => (
                    <tr key={ex}><th style={{ textAlign: "left" }}>{ex}</th>
                      {["LOW", "MEDIUM", "HIGH"].map((p) => <td key={p} className={ex === p ? "hit" : c.matrix[ex][p] ? "miss" : ""}>{c.matrix[ex][p]}</td>)}</tr>
                  ))}</tbody>
                </table>
              </div>
              <div className="card">
                <div className="card-head"><h3>Crisis by language</h3></div>
                <table className="t"><thead><tr><th>Language</th><th>Correct</th></tr></thead>
                  <tbody>{Object.entries(c.by_language).map(([l, v]: [string, any]) => <tr key={l}><td>{LANGN[l] ?? l}</td><td className="num">{v.correct} / {v.total}</td></tr>)}</tbody></table>
              </div>
              <div className="card">
                <div className="card-head"><h3>Emotion by language</h3></div>
                {e ? <table className="t"><thead><tr><th>Language</th><th>Correct</th></tr></thead>
                  <tbody>{Object.entries(e.by_language).map(([l, v]: [string, any]) => <tr key={l}><td>{LANGN[l] ?? l}</td><td className="num">{v.correct} / {v.total}</td></tr>)}</tbody></table>
                  : <p className="small faint">Available once the text models have loaded.</p>}
                {e?.holdout && <p className="tiny faint" style={{ marginTop: 10 }}>Held-out set, never used for tuning: <b className="gold">{pct(e.holdout.accuracy, 1)}</b>
                  {" "}({e.holdout.results.filter((r: any) => r.ok).length}/{e.holdout.total}) · previous version scored 50 %</p>}
              </div>
            </div>
            <div className="card" style={{ marginTop: 18 }}>
              <div className="card-head"><h3>Every crisis test case</h3><button className="btn sm" onClick={() => setShowAll(!showAll)}>{showAll ? "Collapse" : "Show all"}</button></div>
              <table className="t">
                <thead><tr><th>Message</th><th>Lang</th><th>Expected</th><th>Predicted</th><th>Why</th></tr></thead>
                <tbody>{(showAll ? c.results : c.results.slice(0, 8)).map((r: any, i: number) => (
                  <tr key={i}><td>{r.text}</td><td className="tiny">{r.lang}</td><td><TierBadge tier={r.expected} /></td>
                    <td><TierBadge tier={r.predicted} /> {r.ok ? "" : "✗"}</td>
                    <td className="small muted">{r.reasons[0] ?? (r.idioms.length ? `idiom ignored: "${r.idioms[0]}"` : "–")}</td></tr>
                ))}</tbody>
              </table>
            </div>
          </div>
        )}
      </section>

      <section className="section">
        <SectionHead num="vii." title="Models and technology" />
        <div className="card">
          <table className="t">
            <thead><tr><th>Component</th><th>Choice</th><th>Why</th></tr></thead>
            <tbody>
              <tr><td>Facial emotion</td><td>SSD-MobileNet v1 + 68-point landmarks + expression CNN (TensorFlow.js, WebGL)</td><td>On-device; personal calibration and FACS action units correct the CNN's neutral/happy bias</td></tr>
              <tr><td>Voice emotion</td><td>wav2vec2-base fine-tuned on IEMOCAP (SUPERB ER) + NumPy prosody</td><td>Self-supervised speech model plus interpretable vocal markers</td></tr>
              <tr><td>Text emotion · English</td><td>RoBERTa-base on GoEmotions (58k comments, 28 labels), noisy-OR grouping</td><td>Fine-grained emotions such as grief, remorse and nervousness</td></tr>
              <tr><td>Text emotion · Indian languages</td><td>XLM-RoBERTa XLM-EMO (19 languages) + Hindi/Hinglish/Kannada lexicon</td><td>Hindi, Hinglish and Kannada went from 0 % to 100 % on the test set</td></tr>
              <tr><td>Crisis detection</td><td>Rule engine, C-SSRS severity levels, 4 languages</td><td>Deterministic, auditable, 100 % recall on the test set</td></tr>
              <tr><td>Dialogue</td><td>Groq / Gemini free tiers → Ollama → staged offline engine (4 languages)</td><td>Zero cost, never goes silent, never loops</td></tr>
              <tr><td>Speech</td><td>Web Speech API + SpeechSynthesis</td><td>Built into Chrome/Edge, multilingual</td></tr>
              <tr><td>Backend / storage</td><td>FastAPI · SQLite · Fernet encryption</td><td>Portable single-folder deployment</td></tr>
              <tr><td>Frontend</td><td>React + TypeScript · Recharts · Cormorant Garamond & Manrope</td><td>Light and dark themes, code-split pages</td></tr>
            </tbody>
          </table>
        </div>
      </section>

      <section className="section">
        <div className="grid g-2">
          <div>
            <SectionHead num="viii." title="Ethics and limitations" />
            <div className="card stack small">
              <p>• Not a diagnostic or therapeutic device; it supports and refers.</p>
              <p>• Emotion models are trained on acted or Western data. Personal calibration and reliability weighting reduce, but do not remove, this bias.</p>
              <p>• The Hindi and Kannada lists need review by native speakers and clinicians before real use.</p>
              <p>• Evaluation uses curated test sets and scripted scenarios, not real at-risk users.</p>
              <p>• Cloud dialogue models (when enabled) receive message text; consent explains this.</p>
            </div>
          </div>
          <div>
            <SectionHead num="ix." title="Future scope" />
            <div className="card stack small">
              <p>• Integration with campus counselling services and Tele-MANAS referral workflows.</p>
              <p>• Fine-tuning the risk classifier on clinically annotated Indian-language data (e.g. with MuRIL).</p>
              <p>• Learning the fusion weights from data and calibrating per user over weeks.</p>
              <p>• A mobile app with on-device speech recognition for low-connectivity regions.</p>
              <p>• A clinical pilot with ethics approval to measure real-world benefit.</p>
            </div>
          </div>
        </div>
      </section>
    </div>
  );
}
