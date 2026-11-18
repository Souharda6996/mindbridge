import { useEffect, useState, type ReactElement } from "react";
import { Footprints, MoonStar, NotebookPen, Sparkles, Sprout, Wind } from "lucide-react";

function BoxBreathing() {
  const phases = ["Breathe in", "Hold", "Breathe out", "Hold"];
  const [running, setRunning] = useState(false);
  const [i, setI] = useState(0);
  const [count, setCount] = useState(4);
  const [cycles, setCycles] = useState(0);

  useEffect(() => {
    if (!running) return;
    const id = setInterval(() => {
      setCount((c) => {
        if (c > 1) return c - 1;
        setI((p) => { const n = (p + 1) % 4; if (n === 0) setCycles((x) => x + 1); return n; });
        return 4;
      });
    }, 1000);
    return () => clearInterval(id);
  }, [running]);
  useEffect(() => { if (cycles >= 4) setRunning(false); }, [cycles]);
  const scale = i <= 1 ? 1.75 : 1;

  return (
    <div>
      <div className="breath-wrap"><div className="breath" style={{ transform: `scale(${running ? scale : 1})` }} /></div>
      <div className="row" style={{ justifyContent: "center", gap: 14 }}>
        <span className="serif" style={{ fontSize: 22, fontWeight: 600 }}>{running ? phases[i] : cycles >= 4 ? "Well done" : "Ready when you are"}</span>
        {running && <span className="num faint" style={{ fontSize: 18 }}>{count}</span>}
        <span className="faint small">cycle {Math.min(cycles + (running ? 1 : 0), 4)}/4</span>
        <button className="btn sm" onClick={() => { setCycles(0); setI(0); setCount(4); setRunning(!running); }}>{running ? "Stop" : "Begin"}</button>
      </div>
    </div>
  );
}

function Checklist({ items }: { items: [string, string][] }) {
  const [done, setDone] = useState<number[]>([]);
  return (
    <div className="stack" style={{ gap: 8 }}>
      {items.map(([n, t], k) => (
        <label key={k} className="row" style={{ cursor: "pointer", padding: "6px 0" }}>
          <input type="checkbox" checked={done.includes(k)} style={{ accentColor: "var(--accent)" }}
            onChange={() => setDone(done.includes(k) ? done.filter((x) => x !== k) : [...done, k])} />
          <span className="serif" style={{ width: 22, fontSize: 18, fontWeight: 600, color: "var(--gold)" }}>{n}</span>
          <span style={{ textDecoration: done.includes(k) ? "line-through" : "none", opacity: done.includes(k) ? 0.6 : 1 }}>{t}</span>
        </label>
      ))}
      {done.length === items.length && <p className="small" style={{ color: "var(--accent)" }}>Beautifully done. Notice how you feel now.</p>}
    </div>
  );
}

function ThoughtRecord() {
  const [v, setV] = useState({ thought: "", for: "", against: "", balanced: "" });
  const f = (k: keyof typeof v, label: string, ph: string) => (
    <label className="field">{label}
      <textarea className="textarea" style={{ minHeight: 52 }} placeholder={ph} value={v[k]} onChange={(e) => setV({ ...v, [k]: e.target.value })} />
    </label>
  );
  return (
    <div className="grid g-2" style={{ gap: 12 }}>
      {f("thought", "The thought", "e.g. I'm going to fail everything")}
      {f("for", "Evidence for it", "What supports this?")}
      {f("against", "Evidence against it", "What doesn't fit?")}
      {f("balanced", "A kinder, balanced view", "What would you tell a friend?")}
      <p className="faint small" style={{ gridColumn: "1 / -1" }}>Stays on this screen only - nothing here is sent or saved.</p>
    </div>
  );
}

function Picker({ ideas, after }: { ideas: string[]; after: string }) {
  const [pick, setPick] = useState<string | null>(null);
  return (
    <div className="row wrap">
      {ideas.map((i) => <button key={i} className={`chip toggle ${pick === i ? "on" : ""}`} onClick={() => setPick(i)}>{i}</button>)}
      {pick && <p className="small muted fade-in" style={{ width: "100%", marginTop: 6 }}>{after}</p>}
    </div>
  );
}

function Gratitude() {
  const [items, setItems] = useState(["", "", ""]);
  return (
    <div className="stack" style={{ gap: 8 }}>
      {items.map((v, i) => (
        <input key={i} className="input" placeholder={["Something small that went well", "Someone who helped, even a little", "Something you did for yourself"][i]}
          value={v} onChange={(e) => setItems(items.map((x, j) => (j === i ? e.target.value : x)))} />
      ))}
      {items.every((x) => x.trim()) && <p className="small fade-in" style={{ color: "var(--accent)" }}>Three good things. Your mind will notice more of these over time.</p>}
    </div>
  );
}

export interface ExerciseMeta { title: string; desc: string; minutes: string; tone: string; icon: ReactElement; body: ReactElement; best: string }

export const EXERCISES: Record<string, ExerciseMeta> = {
  box_breathing: { title: "Box breathing", desc: "4 in · 4 hold · 4 out · 4 hold. Calms the body's alarm system.", minutes: "1 min",
    tone: "accent", best: "Panic, racing heart, before an exam", icon: <Wind size={19} />, body: <BoxBreathing /> },
  grounding: { title: "5-4-3-2-1 grounding", desc: "Bring attention back to the present using your senses.", minutes: "2 min",
    tone: "blue", best: "Overwhelm, spiralling thoughts", icon: <Footprints size={19} />,
    body: <Checklist items={[["5", "things you can see"], ["4", "things you can feel"], ["3", "things you can hear"], ["2", "things you can smell"], ["1", "thing you can taste"]]} /> },
  thought_record: { title: "CBT thought record", desc: "Look at a harsh thought the way a fair friend would.", minutes: "5 min",
    tone: "plum", best: "Self-criticism, overthinking", icon: <NotebookPen size={19} />, body: <ThoughtRecord /> },
  small_step: { title: "One small step", desc: "Behavioural activation: a tiny action can shift a low mood.", minutes: "2 min",
    tone: "gold", best: "Low mood, low energy", icon: <Sprout size={19} />,
    body: <Picker ideas={["Drink a glass of water", "Step outside for 5 minutes", "Text one friend 'hey'", "Take a warm shower", "Tidy one small corner", "Play one song you love"]}
      after="Nice choice. Small actions build momentum - come back and say how it went." /> },
  sleep_winddown: { title: "Sleep wind-down", desc: "A gentle 20-minute routine that tells your body the day is over.", minutes: "20 min",
    tone: "blue", best: "Trouble falling asleep", icon: <MoonStar size={19} />,
    body: <Checklist items={[["1", "Dim the lights and put the phone across the room"], ["2", "Write tomorrow's worries on paper"], ["3", "Warm drink without caffeine"], ["4", "Ten slow breaths, longer out than in"], ["5", "Read something light on paper"]]} /> },
  gratitude: { title: "Three good things", desc: "A well-studied practice from positive psychology.", minutes: "3 min",
    tone: "gold", best: "End of a hard day", icon: <Sparkles size={19} />, body: <Gratitude /> },
};

export function ExerciseCard({ id }: { id: string }) {
  const m = EXERCISES[id];
  if (!m) return null;
  return (
    <div className="exercise fade-in">
      <div className="row" style={{ marginBottom: 6, color: "var(--accent)" }}>{m.icon}<h3 style={{ fontSize: 20 }}>{m.title}</h3>
        <span className="spacer" /><span className="chip">{m.minutes}</span></div>
      <p className="small muted" style={{ marginBottom: 12 }}>{m.desc}</p>
      {m.body}
    </div>
  );
}
