import { useEffect, useState } from "react";
import { Link } from "react-router-dom";
import { FileText, KeyRound, Laptop, Lock, Moon, Sun, Trash2 } from "lucide-react";
import { api } from "../api";
import { PageHead, Switch } from "../components/ui";
import { useApp } from "../components/Layout";
import { useTheme, type ThemePref } from "../theme";

const CONSENTS: [string, string, string][] = [
  ["camera", "Camera", "Facial expression is analysed in the browser; frames are never uploaded."],
  ["microphone", "Microphone", "Audio is analysed in memory and discarded."],
  ["store_history", "Save conversation history", "Encrypted at rest with Fernet (AES + HMAC)."],
  ["counselor_alerts", "Counsellor alerts", "Allow risk alerts (with reasons) to reach a campus counsellor."],
  ["trusted_contact_alerts", "Trusted-contact alerts", "Allow notifying your trusted contact when you agree."],
  ["share_reports", "Shareable therapist report", "Let me generate a summary to share with my therapist."],
];
const THEMES: [ThemePref, string, typeof Sun][] = [["light", "Light", Sun], ["dark", "Dark", Moon], ["system", "Match device", Laptop]];

function LLMCard() {
  const { companion, toast } = useApp();
  const [st, setSt] = useState<any>(null);
  const [provider, setProvider] = useState("groq");
  const [key, setKey] = useState("");
  const [busy, setBusy] = useState(false);
  const [result, setResult] = useState<any>(null);
  useEffect(() => { api.llm().then(setSt).catch(() => {}); }, []);

  const save = async () => {
    setBusy(true);
    try {
      const r = await api.llmSetKey(provider, key.trim());
      setResult(r); setSt(r); setKey("");
      toast(r.ok ? "Connected. Replies will now sound much more natural." : "Key saved, but the test failed");
    } finally { setBusy(false); }
  };
  const active = st?.active ?? "offline";
  return (
    <div className="card">
      <div className="card-head"><h3>Conversation AI</h3>
        <span className={`chip ${active === "offline" ? "" : "gold"}`}>{active === "offline" ? "offline engine" : active}</span></div>
      <p className="small muted" style={{ marginBottom: 12 }}>
        {companion} works fully offline, but a free cloud AI makes conversation feel like talking to a person. Create a <b>free</b> key
        at <a href="https://console.groq.com/keys" target="_blank" rel="noreferrer">console.groq.com/keys</a> (or{" "}
        <a href="https://aistudio.google.com/apikey" target="_blank" rel="noreferrer">Google AI Studio</a>) and paste it here.
      </p>
      <div className="row">
        <select className="select" style={{ width: 120 }} value={provider} onChange={(e) => setProvider(e.target.value)}>
          <option value="groq">Groq</option><option value="gemini">Gemini</option>
        </select>
        <input className="input" type="password" placeholder="Paste API key" value={key} onChange={(e) => setKey(e.target.value)} />
        <button className="btn primary" disabled={busy || key.trim().length < 10} onClick={save}>{busy ? "Testing…" : "Save & test"}</button>
      </div>
      {(["groq", "gemini"] as const).map((p) => st?.[p]?.configured && (
        <div key={p} className="row small" style={{ marginTop: 10 }}>
          <span style={{ textTransform: "capitalize", fontWeight: 600 }}>{p}</span><span className="faint">key {st[p].hint}</span><span className="spacer" />
          <button className="btn sm" onClick={async () => setResult(await api.llmTest(p))}>Test</button>
          <button className="btn sm danger" onClick={async () => setSt(await api.llmRemove(p))}>Remove</button>
        </div>
      ))}
      {result && (
        <p className="small fade-in" style={{ marginTop: 10, color: result.ok ? "var(--accent)" : "var(--clay)" }}>
          {result.ok ? <>Working ({result.model}, {result.latency_ms} ms): “{result.sample}”</> : <>Could not connect: {result.error}</>}
        </p>
      )}
      <p className="tiny faint" style={{ marginTop: 10 }}>The key is stored only in the .env file on this computer. Message text is sent to the provider when enabled.</p>
    </div>
  );
}

export default function Settings() {
  const { health, companion, toast, refreshSettings } = useApp();
  const { pref, setPref } = useTheme();
  const [s, setS] = useState<any>(null);
  const [confirm, setConfirm] = useState(false);

  const load = () => api.settings().then(setS);
  useEffect(() => { load(); }, []);
  if (!s) return <div className="skeleton" style={{ height: 420 }} />;

  const put = async (key: string, value: unknown) => {
    const r = await api.putSetting(key, value);
    setS({ ...s, [key]: r.value });
    refreshSettings();
    toast("Saved");
  };

  return (
    <div>
      <PageHead eyebrow="Privacy & settings" title={<>You stay <em className="gold">in control</em></>}
        lede="Every sensor is optional, everything you write is encrypted, and you can erase all of it in one step." />

      <div className="grid g-2 reveal" style={{ alignItems: "start" }}>
        <div className="stack" style={{ gap: 18 }}>
          <div className="card">
            <div className="card-head"><h3>Appearance</h3></div>
            <div className="grid g-3" style={{ gap: 10 }}>
              {THEMES.map(([v, label, Icon]) => (
                <button key={v} className={`mood-pill ${pref === v ? "on" : ""}`} onClick={() => setPref(v)} style={{ padding: "16px 8px" }}>
                  <Icon size={20} />{label}
                </button>
              ))}
            </div>
          </div>

          <LLMCard />

          <div className="card">
            <div className="card-head"><h3>Profile</h3></div>
            <div className="grid g-2">
              <label className="field">Name {companion} uses
                <input className="input" defaultValue={s.profile.name} onBlur={(e) => put("profile", { name: e.target.value })} />
              </label>
              <label className="field">Preferred language
                <select className="select" value={s.profile.language} onChange={(e) => put("profile", { language: e.target.value })}>
                  <option value="en-IN">English</option><option value="hi-IN">हिन्दी (Hindi)</option><option value="kn-IN">ಕನ್ನಡ (Kannada)</option>
                </select>
              </label>
            </div>
            <p className="tiny faint" style={{ marginTop: 10 }}>{companion} always replies in the language you write in; this sets the greeting and voice language.</p>
          </div>

          <div className="card">
            <div className="card-head"><h3>Consent</h3><span className="tiny faint">change any time</span></div>
            {CONSENTS.map(([k, title, desc]) => (
              <div key={k} className="row" style={{ padding: "12px 0", borderTop: "1px solid var(--line-2)" }}>
                <div style={{ flex: 1 }}><div style={{ fontWeight: 600 }}>{title}</div><div className="small faint">{desc}</div></div>
                <Switch checked={!!s.consent[k]} onChange={(v) => put("consent", { [k]: v })} label={title} />
              </div>
            ))}
            <div className="row" style={{ padding: "12px 0", borderTop: "1px solid var(--line-2)" }}>
              <div style={{ flex: 1 }}><div style={{ fontWeight: 600 }}>Incognito mode</div>
                <div className="small faint">Nothing from new conversations is saved. Safety alerts still work.</div></div>
              <Switch checked={!!s.incognito} onChange={(v) => put("incognito", v)} label="Incognito" />
            </div>
          </div>

          <div className="card">
            <div className="card-head"><h3>Trusted contact</h3></div>
            <div className="grid g-3">
              {(["name", "phone", "email"] as const).map((f) => (
                <label key={f} className="field" style={{ textTransform: "capitalize" }}>{f}
                  <input className="input" defaultValue={s.trusted_contact[f]} onBlur={(e) => put("trusted_contact", { [f]: e.target.value })} />
                </label>
              ))}
            </div>
            <p className="small faint" style={{ marginTop: 10 }}>Contacted only if you agree in that moment, and only with a short "please check on them" message - never your conversations.</p>
          </div>
        </div>

        <div className="stack" style={{ gap: 18 }}>
          <div className="card">
            <div className="card-head"><h3>How your data is protected</h3></div>
            <div className="stack" style={{ gap: 14 }}>
              <div className="row top"><span className="icon-tile accent"><Lock size={18} /></span><span><b>Encrypted at rest.</b><br /><span className="small muted">{health?.encryption}. The key lives only on this computer.</span></span></div>
              <div className="row top"><span className="icon-tile plum"><KeyRound size={18} /></span><span><b>On-device vision.</b><br /><span className="small muted">The face models run in your browser with TensorFlow.js. Only seven emotion probabilities leave the page.</span></span></div>
              <div className="row top"><span className="icon-tile gold"><FileText size={18} /></span><span><b>Local storage.</b><br /><span className="small muted">{health?.database} database on this computer. Message text is sent to a third party only if a cloud dialogue model is enabled.</span></span></div>
            </div>
          </div>

          <div className="card">
            <div className="card-head"><h3>Your data</h3></div>
            <div className="stack">
              <Link className="btn" to="/report"><FileText size={15} />Generate therapist report</Link>
              <div className="row">
                <button className="btn" style={{ flex: 1 }} onClick={async () => { await api.reseed(); toast("Sample history reloaded"); }}>Reload sample history</button>
                <button className="btn" style={{ flex: 1 }} onClick={async () => { await api.clearDemo(); toast("Sample history removed"); }}>Clear sample history</button>
              </div>
              {!confirm ? (
                <button className="btn danger" onClick={() => setConfirm(true)}><Trash2 size={15} />Delete all my data</button>
              ) : (
                <div className="crisis fade-in">
                  <p style={{ marginBottom: 12 }}>This permanently deletes every conversation, journal entry, alert and setting, and rotates the encryption key. It cannot be undone.</p>
                  <div className="row">
                    <button className="btn danger solid" onClick={async () => { const r = await api.deleteAll(); setConfirm(false); toast(r.message); load(); refreshSettings(); }}>Yes, delete everything</button>
                    <button className="btn" onClick={() => setConfirm(false)}>Cancel</button>
                  </div>
                </div>
              )}
            </div>
          </div>

          <div className="card tint">
            <div className="card-head"><h3>Important</h3></div>
            <p className="small muted">MindBridge is a final-year student research prototype. It offers supportive conversation, not therapy, and cannot diagnose or prescribe.
              In an emergency call <b>112</b>. For free, confidential support call Tele-MANAS on <b>14416</b> (24x7, 20+ languages).</p>
          </div>
        </div>
      </div>
    </div>
  );
}
