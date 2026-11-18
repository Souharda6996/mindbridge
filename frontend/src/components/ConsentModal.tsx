import { useState } from "react";
import { api } from "../api";
import { Switch } from "./ui";
import { LotusMark } from "./Layout";

const ITEMS: [string, string, string][] = [
  ["camera", "Camera (video mode)", "Analysed on this device only. Frames are never uploaded or recorded."],
  ["microphone", "Microphone (voice mode)", "Audio is analysed in memory and discarded immediately."],
  ["store_history", "Save my conversations", "Stored encrypted. Turn off to use MindBridge without history."],
  ["counselor_alerts", "Alert a campus counsellor if I may be at risk", "Includes the reason for the alert so they can help."],
  ["trusted_contact_alerts", "Allow alerts to my trusted contact", "Only when I agree at that moment. No chat content is shared."],
];

export default function ConsentModal({ initial, onDone, companion }: { initial: any; onDone: () => void; companion: string }) {
  const [c, setC] = useState({ ...initial });
  const save = async () => {
    await api.putSetting("consent", { ...c, accepted: true });
    onDone();
  };
  return (
    <div className="overlay">
      <div className="modal">
        <div className="row" style={{ gap: 14 }}>
          <LotusMark size={44} />
          <div>
            <div className="eyebrow gold">Before we begin</div>
            <h2 style={{ marginTop: 2 }}>Your space, your choices</h2>
          </div>
        </div>
        <p className="muted" style={{ marginTop: 14 }}>
          {companion} is a supportive AI companion built as a student research prototype. It is <b>not a substitute for
          professional care</b> and cannot diagnose. If you are in danger, call <b>112</b> or Tele-MANAS on <b>14416</b>.
        </p>
        <div className="stack" style={{ marginTop: 18, gap: 0 }}>
          {ITEMS.map(([k, title, desc]) => (
            <div key={k} className="row" style={{ padding: "12px 0", borderTop: "1px solid var(--line-2)" }}>
              <div style={{ flex: 1 }}>
                <div style={{ fontWeight: 600 }}>{title}</div>
                <div className="small faint">{desc}</div>
              </div>
              <Switch checked={!!c[k]} onChange={(v) => setC({ ...c, [k]: v })} label={title} />
            </div>
          ))}
        </div>
        <div className="row" style={{ marginTop: 22 }}>
          <span className="small faint">You can change these any time in Privacy & settings.</span>
          <span className="spacer" />
          <button className="btn primary lg" onClick={save}>I understand, continue</button>
        </div>
      </div>
    </div>
  );
}
