import { useEffect, useState } from "react";
import { useLocation, useNavigate } from "react-router-dom";
import { Clock, X } from "lucide-react";
import { EXERCISES, ExerciseCard } from "../components/Exercises";
import { PageHead } from "../components/ui";

export default function Toolkit() {
  const loc = useLocation();
  const nav = useNavigate();
  const [open, setOpen] = useState<string | null>(null);
  useEffect(() => {
    const id = loc.hash.replace("#", "");
    if (id && EXERCISES[id]) setOpen(id);
  }, [loc.hash]);
  const close = () => { setOpen(null); nav("/toolkit", { replace: true }); };

  return (
    <div>
      <PageHead eyebrow="Calm toolkit" title={<>Small practices, <em className="gold">real relief</em></>}
        lede="Evidence-based exercises from CBT, breathing science and positive psychology. Each takes a few minutes and works offline." />
      <div className="grid g-3 reveal">
        {Object.entries(EXERCISES).map(([id, m]) => (
          <button key={id} className="card lift tool-card" onClick={() => setOpen(id)}>
            <div className="row"><span className={`icon-tile ${m.tone}`}>{m.icon}</span><span className="spacer" />
              <span className="chip"><Clock size={12} />{m.minutes}</span></div>
            <h3>{m.title}</h3>
            <p className="muted small" style={{ flex: 1 }}>{m.desc}</p>
            <div className="tiny faint"><b style={{ color: "var(--gold)" }}>Helps with</b> · {m.best}</div>
          </button>
        ))}
      </div>
      {open && (
        <div className="overlay" onClick={close}>
          <div className="modal" style={{ maxWidth: 620, padding: 22 }} onClick={(e) => e.stopPropagation()}>
            <div className="row" style={{ marginBottom: 10 }}><span className="eyebrow gold">Practice</span><span className="spacer" />
              <button className="icon-btn" onClick={close} aria-label="Close"><X size={16} /></button></div>
            <ExerciseCard id={open} />
          </div>
        </div>
      )}
    </div>
  );
}
