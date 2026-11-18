import { createContext, useCallback, useContext, useEffect, useState } from "react";
import { Link, NavLink, Outlet, useLocation } from "react-router-dom";
import {
  Bell, FileText, Flower2, House, Microscope, MessagesSquare, Moon, NotebookPen, Settings2, ShieldCheck, Sun,
} from "lucide-react";
import { api } from "../api";
import { useTheme } from "../theme";
import ConsentModal from "./ConsentModal";

interface AppState {
  health: any; settings: any; companion: string; newAlerts: number;
  refreshSettings: () => void; toast: (msg: string) => void;
}
const AppCtx = createContext<AppState>({
  health: null, settings: null, companion: "Anvaya", newAlerts: 0, refreshSettings: () => {}, toast: () => {},
});
export const useApp = () => useContext(AppCtx);

export function LotusMark({ size = 34 }: { size?: number }) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" aria-hidden>
      <defs>
        <radialGradient id="lm" cx="40%" cy="35%" r="70%"><stop offset="0" stopColor="#f3dfb4" /><stop offset="1" stopColor="#1f4d43" /></radialGradient>
      </defs>
      <rect width="64" height="64" rx="17" fill="#132a24" />
      <g transform="translate(32 35)" fill="none" stroke="#d4b47c" strokeWidth="2">
        <path d="M0-21C7-13 7-5 0 3C-7-5-7-13 0-21Z" />
        <path d="M0-21C7-13 7-5 0 3C-7-5-7-13 0-21Z" transform="rotate(60)" />
        <path d="M0-21C7-13 7-5 0 3C-7-5-7-13 0-21Z" transform="rotate(-60)" />
      </g>
      <circle cx="32" cy="35" r="8.5" fill="url(#lm)" />
    </svg>
  );
}

const TITLES: Record<string, string> = {
  "/": "Home", "/companion": "Companion", "/journal": "Mood journal", "/toolkit": "Toolkit", "/counselor": "Counsellor console",
  "/report": "Therapist report", "/how-it-works": "How it works", "/settings": "Privacy & settings",
};

export default function Layout() {
  const [health, setHealth] = useState<any>(null);
  const [settings, setSettings] = useState<any>(null);
  const [newAlerts, setNewAlerts] = useState(0);
  const [toastMsg, setToastMsg] = useState<string | null>(null);
  const { resolved, toggle } = useTheme();
  const loc = useLocation();

  useEffect(() => {
    const load = () => {
      api.health().then(setHealth).catch(() => setHealth(null));
      api.alerts().then((a) => setNewAlerts(a.filter((x) => x.status === "new").length)).catch(() => {});
    };
    load();
    const id = setInterval(load, 5000);
    return () => clearInterval(id);
  }, []);

  const refreshSettings = useCallback(() => { api.settings().then(setSettings).catch(() => {}); }, []);
  useEffect(() => { refreshSettings(); }, [refreshSettings, loc.pathname]);
  useEffect(() => { window.scrollTo({ top: 0 }); }, [loc.pathname]);

  const toast = useCallback((msg: string) => {
    setToastMsg(msg);
    window.setTimeout(() => setToastMsg(null), 2600);
  }, []);

  const companion = health?.companion ?? "Anvaya";
  const rawName = (settings?.profile?.name ?? "").trim();
  const name = rawName ? rawName[0].toUpperCase() + rawName.slice(1) : "";
  const modelDot = (s?: string) => (s === "ready" ? "ok" : s === "loading" || s === "pending" ? "warn" : "off");
  const llm = health?.llm?.order?.[0] ?? "offline";

  return (
    <AppCtx.Provider value={{ health, settings, companion, newAlerts, refreshSettings, toast }}>
      <div className="app">
        <aside className="sidebar">
          <Link to="/" className="brand" style={{ color: "inherit" }}>
            <LotusMark />
            <div>
              <div className="brand-name">Mind<em>Bridge</em></div>
              <div className="brand-sub">care · connection</div>
            </div>
          </Link>
          <nav className="nav">
            <div className="nav-label eyebrow" style={{ marginTop: 0 }}>You</div>
            <NavLink to="/" end><House size={18} />Home</NavLink>
            <NavLink to="/companion"><MessagesSquare size={18} />Talk to {companion}</NavLink>
            <NavLink to="/journal"><NotebookPen size={18} />Mood journal</NavLink>
            <NavLink to="/toolkit"><Flower2 size={18} />Calm toolkit</NavLink>
            <div className="nav-label eyebrow">Care team</div>
            <NavLink to="/counselor"><ShieldCheck size={18} />Counsellor console
              {newAlerts > 0 && <span className="badge">{newAlerts}</span>}</NavLink>
            <NavLink to="/report"><FileText size={18} />Therapist report</NavLink>
            <div className="nav-label eyebrow">Project</div>
            <NavLink to="/how-it-works"><Microscope size={18} />How it works</NavLink>
            <NavLink to="/settings"><Settings2 size={18} />Privacy & settings</NavLink>
          </nav>
          <div className="sidebar-foot">
            <div className="status-box">
              <div className="eyebrow" style={{ marginBottom: 8 }}>System</div>
              <div className="status-row"><span><i className={`dot ${health ? "ok" : "off"}`} />Server</span><span className="faint">{health ? "online" : "offline"}</span></div>
              <div className="status-row"><span><i className={`dot ${modelDot(health?.models?.text?.state)}`} />Text · English</span><span className="faint">{health?.models?.text?.state ?? "-"}</span></div>
              <div className="status-row"><span><i className={`dot ${modelDot(health?.models?.text_multi?.state)}`} />Text · Indic</span><span className="faint">{health?.models?.text_multi?.state ?? "-"}</span></div>
              <div className="status-row"><span><i className={`dot ${modelDot(health?.models?.voice?.state)}`} />Voice</span><span className="faint">{health?.models?.voice?.state ?? "-"}</span></div>
              <div className="status-row"><span><i className="dot ok" />Face</span><span className="faint">on-device</span></div>
              <div className="status-row"><span><i className={`dot ${llm === "offline" ? "warn" : "ok"}`} />Dialogue</span><span className="faint">{llm === "offline" ? "offline engine" : llm}</span></div>
            </div>
            <div className="helpline-box">
              <div style={{ opacity: 0.8 }}>Need a person right now?</div>
              <div>Tele-MANAS <strong>14416</strong> · <strong>112</strong></div>
            </div>
          </div>
        </aside>

        <div className="main">
          <header className="topbar">
            <div className="crumbs">MindBridge <span>/</span> <b>{TITLES[loc.pathname] ?? "Home"}</b></div>
            <span className="spacer" />
            <button className="icon-btn" onClick={toggle} title={`Switch to ${resolved === "dark" ? "light" : "dark"} mode`}
              aria-label="Toggle colour theme">
              {resolved === "dark" ? <Sun size={17} /> : <Moon size={17} />}
            </button>
            <Link className="icon-btn" to="/counselor" title="Alerts" aria-label="Alerts">
              <Bell size={17} />{newAlerts > 0 && <i className="pip" />}
            </Link>
            <Link to="/settings" className="user-chip" style={{ color: "inherit" }}>
              <span className="avatar-initials">{(name || "U").slice(0, 1).toUpperCase()}</span>
              <span style={{ lineHeight: 1.2 }}>
                <span style={{ display: "block", fontWeight: 700, fontSize: 13 }}>{name || "Student"}</span>
                <span className="tiny faint">Student · demo</span>
              </span>
            </Link>
          </header>
          <div className="page" key={loc.pathname}>
            <Outlet />
          </div>
        </div>
        {settings?.consent && !settings.consent.accepted && <ConsentModal initial={settings.consent} onDone={refreshSettings} companion={companion} />}
        {toastMsg && <div className="toast">{toastMsg}</div>}
      </div>
    </AppCtx.Provider>
  );
}
