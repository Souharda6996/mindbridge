import { useCallback, useEffect, useRef, useState } from "react";
import { Link } from "react-router-dom";
import {
  Camera, CameraOff, Mic, MessageSquareText, PanelRightClose, PanelRightOpen, RefreshCcw, RotateCcw, Send, Square, Video, Volume2, VolumeX,
} from "lucide-react";
import { api, pct, type FusionOut, type Helpline, type Tier, type TurnOut } from "../api";
import { PageHead, TierBadge } from "../components/ui";
import Inspector, { type FaceLive } from "../components/Inspector";
import CrisisCard from "../components/CrisisCard";
import { ExerciseCard } from "../components/Exercises";
import Orb, { type Expression } from "../components/Orb";
import { useApp } from "../components/Layout";
import { WavRecorder } from "../lib/audio";
import { speak, stopSpeaking, sttSupported, Transcriber } from "../lib/speech";
import type { FaceAnalyzer, FaceReading } from "../lib/face";

interface Msg { role: "user" | "assistant"; text: string; turn?: TurnOut; kind?: "voice" | "text" }

const LANGS: [string, string][] = [["en-IN", "English"], ["hi-IN", "हिन्दी"], ["kn-IN", "ಕನ್ನಡ"]];
const SPEAK_LANG: Record<string, string> = { en: "en-IN", hinglish: "en-IN", hi: "hi-IN", kn: "kn-IN" };
const LANG_NAME: Record<string, string> = { en: "English", hi: "Hindi", hinglish: "Hinglish", kn: "Kannada" };
const FEELINGS: [string, string][] = [["anxious", "Anxious"], ["sad", "Sad"], ["angry", "Angry"], ["lonely", "Lonely"],
  ["overwhelmed", "Overwhelmed"], ["tired", "Tired"], ["happy", "Happy"]];
const PHRASES: Record<string, Record<string, string>> = {
  en: { anxious: "I've been feeling really anxious lately and ", sad: "I've been feeling sad and ", angry: "I'm angry because ",
    lonely: "I've been feeling lonely, ", overwhelmed: "Everything feels like too much right now, ", tired: "I'm exhausted, ", happy: "I'm feeling good today because " },
  hi: { anxious: "मुझे आजकल बहुत घबराहट हो रही है और ", sad: "मैं उदास महसूस कर रहा हूँ और ", angry: "मुझे गुस्सा आ रहा है क्योंकि ",
    lonely: "मुझे अकेलापन महसूस हो रहा है, ", overwhelmed: "अभी सब कुछ बहुत ज़्यादा लग रहा है, ", tired: "मैं बहुत थक गया हूँ, ", happy: "आज मैं खुश हूँ क्योंकि " },
  hinglish: { anxious: "Mujhe aajkal bahut tension ho rahi hai aur ", sad: "Main udaas feel kar raha hoon aur ", angry: "Mujhe gussa aa raha hai kyunki ",
    lonely: "Mujhe akelapan feel ho raha hai, ", overwhelmed: "Abhi sab kuch bahut zyada lag raha hai, ", tired: "Main bahut thak gaya hoon, ", happy: "Aaj main khush hoon kyunki " },
  kn: { anxious: "ನನಗೆ ಈಗ ತುಂಬಾ ಆತಂಕವಾಗುತ್ತಿದೆ ಮತ್ತು ", sad: "ನನಗೆ ಬೇಸರವಾಗಿದೆ ಮತ್ತು ", angry: "ನನಗೆ ಕೋಪ ಬರುತ್ತಿದೆ ಏಕೆಂದರೆ ",
    lonely: "ನನಗೆ ಒಂಟಿತನ ಅನ್ನಿಸುತ್ತಿದೆ, ", overwhelmed: "ಈಗ ಎಲ್ಲವೂ ಅತಿಯಾಗಿದೆ ಅನ್ನಿಸುತ್ತಿದೆ, ", tired: "ನನಗೆ ತುಂಬಾ ದಣಿವಾಗಿದೆ, ", happy: "ಇಂದು ನಾನು ಖುಷಿಯಾಗಿದ್ದೇನೆ ಏಕೆಂದರೆ " },
};
const STARTERS = [
  "I'm stressed about my exams", "I can't sleep properly these days", "I feel lonely in the hostel",
  "मुझे बहुत चिंता हो रही है", "yaar aaj mood off hai", "ನನಗೆ ತುಂಬಾ ಒತ್ತಡವಾಗಿದೆ",
];

export default function Companion() {
  const { companion } = useApp();
  const [mode, setMode] = useState<"text" | "video">("text");
  const [sid, setSid] = useState<string | null>(null);
  const [msgs, setMsgs] = useState<Msg[]>([]);
  const [input, setInput] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [fusion, setFusion] = useState<FusionOut | null>(null);
  const [tier, setTier] = useState<Tier>("LOW");
  const [traj, setTraj] = useState<{ smoothed: number }[]>([]);
  const [reasons, setReasons] = useState<string[]>([]);
  const [last, setLast] = useState<TurnOut | null>(null);
  const [helplines, setHelplines] = useState<Helpline[]>([]);
  const [counselorMsg, setCounselorMsg] = useState<string | null>(null);
  const [showPanel, setShowPanel] = useState(true);
  const [convLang, setConvLang] = useState<string>("en");

  const videoRef = useRef<HTMLVideoElement>(null);
  const streamRef = useRef<MediaStream | null>(null);
  const analyzer = useRef<FaceAnalyzer | null>(null);
  const faceRef = useRef<FaceReading | null>(null);
  const discomfort = useRef<boolean[]>([]);
  const [camOn, setCamOn] = useState(false);
  const [camStatus, setCamStatus] = useState("Camera off");
  const [faceLive, setFaceLive] = useState<FaceLive | null>(null);
  const [suggestText, setSuggestText] = useState(false);
  const [suggestDismissed, setSuggestDismissed] = useState(false);
  const [recording, setRecording] = useState(false);
  const recorder = useRef<WavRecorder | null>(null);
  const transcriber = useRef<Transcriber | null>(null);
  const dictator = useRef<Transcriber | null>(null);
  const [dictating, setDictating] = useState(false);
  const [heard, setHeard] = useState("");
  // "auto" = the server (Whisper) detects the spoken language; listenLocale is what the browser's
  // recogniser listens in, and is updated from the server's detection, never from the last reply.
  const [langMode, setLangMode] = useState<string>("auto");
  const [listenLocale, setListenLocale] = useState("en-IN");
  const lang = langMode === "auto" ? listenLocale : langMode;
  const [speaking, setSpeaking] = useState(false);
  const [voiceOn, setVoiceOn] = useState(true);
  const [expression, setExpression] = useState<Expression>("neutral");
  const [typedVoice, setTypedVoice] = useState("");
  const threadRef = useRef<HTMLDivElement>(null);


  const newSession = useCallback(async (m: "text" | "video") => {
    setError(null);
    try {
      const s = await api.startSession(m);
      setSid(s.session_id);
      setMsgs([{ role: "assistant", text: s.greeting }]);
      setConvLang(s.language ?? "en");
      setFusion(null); setTier("LOW"); setTraj([]); setReasons([]); setLast(null); setHelplines([]);
      setCounselorMsg(null); setExpression("neutral");
    } catch (e) {
      setError(`Cannot reach the MindBridge server (${(e as Error).message}). Is run.bat running?`);
    }
  }, []);

  useEffect(() => { newSession("text"); }, [newSession]);
  useEffect(() => {
    const box = threadRef.current;
    if (box) box.scrollTo({ top: box.scrollHeight, behavior: "smooth" });
  }, [msgs, busy]);

  const applyTurn = (t: TurnOut) => {
    setFusion(t.fusion); setTier(t.tier); setTraj(t.trajectory); setReasons(t.reasons); setLast(t);
    setExpression((t.expression as Expression) || "neutral");
    setConvLang(t.language);
    if (t.helplines?.length) setHelplines(t.helplines);
  };
  const say = (t: TurnOut) => {
    if (mode !== "video" || !voiceOn) return;
    speak(t.reply, SPEAK_LANG[t.language] ?? lang, () => setSpeaking(true), () => setSpeaking(false));
  };

  const send = async (textArg?: string) => {
    const text = (textArg ?? input).trim();
    if (!text || !sid || busy) return;
    setInput("");
    setMsgs((m) => [...m, { role: "user", text, kind: "text" }]);
    setBusy(true);
    setError(null);
    try {
      const t = await api.chat(sid, text, faceRef.current);
      setMsgs((m) => [...m.slice(0, -1), { role: "user", text, turn: t, kind: "text" }, { role: "assistant", text: t.reply, turn: t }]);
      applyTurn(t);
      say(t);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  };

  // ---------------- camera + on-device face analysis ----------------
  const startCam = async () => {
    try {
      setCamStatus("Loading face models…");
      const face = await import("../lib/face");
      const [stream] = await Promise.all([navigator.mediaDevices.getUserMedia({ video: { width: 640, height: 480 } }), face.loadFaceModels()]);
      analyzer.current = analyzer.current ?? new face.FaceAnalyzer();
      streamRef.current = stream;
      if (videoRef.current) { videoRef.current.srcObject = stream; await videoRef.current.play(); }
      setCamOn(true);
      setCamStatus("Relax your face for a moment");
    } catch (e) {
      setCamStatus(`Camera unavailable: ${(e as Error).message}`);
    }
  };
  const stopCam = () => {
    streamRef.current?.getTracks().forEach((t) => t.stop());
    streamRef.current = null; faceRef.current = null;
    setCamOn(false); setFaceLive(null); setCamStatus("Camera off");
  };
  useEffect(() => () => { stopCam(); stopSpeaking(); }, []);

  useEffect(() => {
    if (!camOn) return;
    let alive = true, tick = 0;
    const loop = async () => {
      const v = videoRef.current;
      if (!alive || !v || v.readyState < 2 || !analyzer.current) { if (alive) setTimeout(loop, 400); return; }
      try {
        const r = await analyzer.current.read(v);
        faceRef.current = r.details.found ? r : null;
        setFaceLive({ reliability: r.reliability, issue: r.details.issue, top: r.details.top, cues: r.details.cues,
          calibrated: r.details.calibrated, calibration: r.details.calibration });
        discomfort.current.push(!r.details.found || Math.abs(r.details.yaw) > 0.32);
        if (discomfort.current.length > 28) discomfort.current.shift();
        const ratio = discomfort.current.filter(Boolean).length / discomfort.current.length;
        if (discomfort.current.length >= 20 && ratio > 0.6) setSuggestText(true);
        tick++;
        if (sid && r.details.calibrated && r.details.found && tick % 2 === 0) api.face(sid, r).then((res) => setFusion(res.fusion)).catch(() => {});
      } catch { /* skip frame */ }
      if (alive) setTimeout(loop, 650);
    };
    loop();
    return () => { alive = false; };
  }, [camOn, sid]);

  const switchMode = async (m: "text" | "video") => {
    setMode(m);
    if (m === "video" && !camOn) await startCam();
    if (m === "text") { stopCam(); stopSpeaking(); setSpeaking(false); }
  };

  // ---------------- voice turn (video mode) ----------------
  const startRec = async () => {
    setError(null); stopSpeaking();
    try {
      recorder.current = new WavRecorder();
      await recorder.current.start();
      if (sttSupported) {
        transcriber.current = new Transcriber();
        transcriber.current.onUpdate = (f, i) => setHeard(`${f} ${i}`.trim());
        transcriber.current.start(lang);
      }
      setHeard(""); setRecording(true);
    } catch (e) { setError(`Microphone unavailable: ${(e as Error).message}`); }
  };
  const stopRec = async () => {
    if (!recorder.current || !sid) return;
    setRecording(false); setBusy(true);
    try {
      const [wav, said] = await Promise.all([recorder.current.stop(), transcriber.current?.stop() ?? Promise.resolve("")]);
      const transcript = (said || heard || typedVoice).trim();
      setTypedVoice("");
      const fd = new FormData();
      fd.append("session_id", sid); fd.append("transcript", transcript); fd.append("audio", wav, "voice.wav");
      fd.append("browser_locale", lang); fd.append("lang_mode", langMode === "auto" ? "auto" : langMode.split("-")[0]);
      if (faceRef.current) fd.append("face", JSON.stringify(faceRef.current));
      const t = (await api.voice(fd)) as TurnOut & { needs_repeat?: boolean; stt?: { locale: string; language: string; text?: string } };
      if (t.stt?.locale && langMode === "auto") setListenLocale(t.stt.locale);   // listen in what was actually spoken
      if (t.needs_repeat) {
        setMsgs((m) => [...m, { role: "assistant", text: t.reply }]);
        if (voiceOn) speak(t.reply, t.stt?.locale ?? lang, () => setSpeaking(true), () => setSpeaking(false));
      } else {
        setMsgs((m) => [...m, { role: "user", text: transcript || t.stt?.text || "(voice only)", turn: t, kind: "voice" }, { role: "assistant", text: t.reply, turn: t }]);
        applyTurn(t); say(t);
      }
    } catch (e) { setError((e as Error).message); } finally { setBusy(false); setHeard(""); }
  };

  // ---------------- dictation (text mode) ----------------
  const toggleDictation = async () => {
    if (dictating) {
      const said = await dictator.current?.stop();
      setDictating(false);
      if (said) setInput((x) => `${x} ${said}`.trim());
      return;
    }
    dictator.current = new Transcriber();
    dictator.current.onUpdate = (f, i) => setHeard(`${f} ${i}`.trim());
    dictator.current.start(lang);
    setHeard(""); setDictating(true);
  };

  const requestCounselor = async () => { const r = await api.requestCounselor(sid); setCounselorMsg(r.message); };
  const lastAssistant = [...msgs].reverse().find((m) => m.role === "assistant");
  const onlyGreeting = msgs.length <= 1;

  const thread = (
    <div className="thread" ref={threadRef}>
      {tier === "HIGH" && (
        <div className="banner high fade-in"><strong>Safety mode is on.</strong> {companion} is following a fixed support protocol and a counsellor has been alerted.</div>
      )}
      {mode === "text" && onlyGreeting && (
        <div className="empty-hero fade-in">
          <Orb size={170} expression="neutral" thinking={busy} />
          <h2 style={{ marginTop: 4 }}>Hi, I'm <em className="gold">{companion}</em></h2>
          <p className="muted" style={{ marginTop: 8 }}>A private space to think out loud. Write in English, हिन्दी, Hinglish or ಕನ್ನಡ, and I'll reply the same way.</p>
          <div className="starters" style={{ marginTop: 18 }}>
            {STARTERS.map((s) => <button key={s} className="chip toggle" onClick={() => send(s)}>{s}</button>)}
          </div>
        </div>
      )}
      {msgs.map((m, i) => (mode === "text" && onlyGreeting && i === 0) ? null : (
        <div key={i} className={`msg ${m.role} fade-in`}>
          {m.role === "assistant" ? (
            <div className="row top" style={{ gap: 10 }}>
              <span style={{ flex: "none", marginTop: 2 }}><MiniOrb /></span>
              <div className="stack" style={{ gap: 6 }}>
                <div className="bubble">{m.text}</div>
                {m.turn && <div className="msg-meta"><span>{m.turn.provider}</span>{m.turn.safety_flags.length > 0 && <span className="chip">safety filter applied</span>}</div>}
              </div>
            </div>
          ) : (
            <>
              <div className="bubble">{m.text}</div>
              {m.turn && (
                <div className="msg-meta">
                  {m.kind === "voice" && <span className="chip"><Mic size={11} /> voice</span>}
                  <span>{LANG_NAME[m.turn.language] ?? m.turn.language}</span>·
                  <span style={{ textTransform: "capitalize" }}>{m.turn.fusion.dominant_emotion}</span>·
                  <span className="num">distress {pct(m.turn.fusion.fused)}</span>
                  <TierBadge tier={m.turn.tier} />
                </div>
              )}
            </>
          )}
          {m.role === "assistant" && m.turn?.actions.some((a) => a.type === "crisis_card") && (
            <div style={{ marginTop: 10, marginLeft: 38 }}><CrisisCard helplines={helplines} sessionId={sid} alertId={m.turn.alert_id} reasons={m.turn.reasons} /></div>
          )}
          {m.role === "assistant" && m.turn?.actions.filter((a) => a.type === "exercise").map((a) => (
            <div key={a.id} style={{ marginTop: 10, marginLeft: 38 }}><ExerciseCard id={a.id!} /></div>
          ))}
          {m.role === "assistant" && m.turn?.tier === "MEDIUM" && i === msgs.length - 1 && (
            <div className="row wrap" style={{ marginTop: 10, marginLeft: 38 }}>
              <Link className="btn sm" to="/journal">Do a 30-second check-in</Link>
              <button className="btn sm primary" onClick={requestCounselor}>Talk to a counsellor</button>
              {counselorMsg && <span className="small muted" style={{ width: "100%" }}>{counselorMsg}</span>}
            </div>
          )}
        </div>
      ))}
      {busy && <div className="msg assistant"><div className="row top" style={{ gap: 10 }}><MiniOrb /><div className="bubble typing"><i /><i /><i /></div></div></div>}
    </div>
  );

  return (
    <div>
      <PageHead eyebrow="Companion" title={<>Talk to <em className="gold">{companion}</em></>}
        lede="Type or simply talk. Your words, voice and expression shape how gently it responds. In a crisis, real people are brought in."
        right={<>
          <div className="seg">
            <button className={mode === "text" ? "on" : ""} onClick={() => switchMode("text")}><MessageSquareText size={15} />Text</button>
            <button className={mode === "video" ? "on" : ""} onClick={() => switchMode("video")}><Video size={15} />Video</button>
          </div>
          <button className="btn" onClick={() => setShowPanel(!showPanel)}>
            {showPanel ? <PanelRightClose size={15} /> : <PanelRightOpen size={15} />}{showPanel ? "Hide" : "Show"} analysis
          </button>
          <button className="btn" onClick={() => newSession(mode)}><RotateCcw size={15} />New conversation</button>
        </>} />
      {error && <div className="banner medium" style={{ marginBottom: 12 }}>{error}</div>}

      <div className={`companion ${showPanel ? "" : "wide"}`}>
        <div className="card chat-card fade-in">
          {mode === "video" && (
            <div style={{ padding: 16, display: "flex", flexDirection: "column", gap: 12, borderBottom: "1px solid var(--line-2)" }}>
              {suggestText && !suggestDismissed && (
                <div className="banner info fade-in">
                  <span style={{ flex: 1 }}>It's completely okay if being on camera feels uncomfortable. Would you rather continue by text?</span>
                  <button className="btn sm" onClick={() => { setSuggestDismissed(true); switchMode("text"); }}>Switch to text</button>
                  <button className="btn sm ghost" onClick={() => setSuggestDismissed(true)}>I'm fine</button>
                </div>
              )}
              <div className="stage">
                <Orb expression={expression} speaking={speaking} listening={recording} thinking={busy} size={260} name={companion} />
                <div className="cam">
                  <video ref={videoRef} muted playsInline />
                  {camOn && faceLive && !faceLive.calibrated && (
                    <div className="calib"><div><b style={{ fontSize: 12 }}>Calibrating</b><br />Look at the camera with a relaxed face<br />
                      <span className="num">{Math.round(faceLive.calibration * 100)}%</span></div></div>
                  )}
                  <div className="cam-label">
                    {camOn && faceLive ? (faceLive.calibrated ? `${faceLive.top} · reliability ${pct(faceLive.reliability)}${faceLive.cues.length ? " · " + faceLive.cues[0] : ""}` : "calibrating…") : camStatus}
                  </div>
                </div>
                {(recording || speaking || lastAssistant) && (
                  <div className="caption">
                    {recording ? (heard || (sttSupported ? "Listening…" : "Recording - type what you said below if captions are unavailable.")) : lastAssistant?.text}
                  </div>
                )}
              </div>
              <div className="row wrap" style={{ justifyContent: "center", gap: 12 }}>
                <button className="btn" onClick={camOn ? stopCam : startCam}>{camOn ? <><CameraOff size={15} />Camera off</> : <><Camera size={15} />Camera on</>}</button>
                {camOn && <button className="btn" onClick={() => analyzer.current?.recalibrate()} title="Learn your resting face again"><RefreshCcw size={15} />Recalibrate</button>}
                <button className={`mic ${recording ? "rec" : ""}`} onClick={recording ? stopRec : startRec} disabled={busy} aria-label={recording ? "Stop and send" : "Start talking"}>
                  {recording ? <Square size={22} /> : <Mic size={24} />}
                </button>
                <button className="btn" onClick={() => { setVoiceOn(!voiceOn); stopSpeaking(); setSpeaking(false); }}>
                  {voiceOn ? <><Volume2 size={15} />Voice on</> : <><VolumeX size={15} />Voice off</>}
                </button>
                <select className="select" style={{ width: 150 }} value={langMode} onChange={(e) => setLangMode(e.target.value)} aria-label="Speech language">
                  <option value="auto">Auto-detect</option>
                  {LANGS.map(([v, l]) => <option key={v} value={v}>{l}</option>)}
                </select>
              </div>
              {recording && !sttSupported && (
                <input className="input" placeholder="Live captions are not supported in this browser - type what you said" value={typedVoice} onChange={(e) => setTypedVoice(e.target.value)} />
              )}
            </div>
          )}
          {thread}
          <div className="row wrap" style={{ padding: "10px 16px 0", gap: 8, background: "var(--surface)" }}>
            <span className="eyebrow">I feel</span>
            {FEELINGS.map(([key, label]) => (
              <button key={key} className="chip toggle" disabled={busy}
                onClick={() => setInput((PHRASES[convLang] ?? PHRASES.en)[key])}>{label}</button>
            ))}
          </div>
          <div className="composer">
            {sttSupported && (
              <button className={`icon-btn ${dictating ? "on" : ""}`} onClick={toggleDictation} title="Dictate" aria-label="Dictate"
                style={dictating ? { background: "var(--clay)", color: "#fff", borderColor: "var(--clay)" } : undefined}>
                {dictating ? <Square size={15} /> : <Mic size={16} />}
              </button>
            )}
            <textarea placeholder={dictating ? (heard || "Listening…") : `Message ${companion}…`} value={input} rows={1}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter" && !e.shiftKey) { e.preventDefault(); send(); } }} />
            <button className="btn primary lg" onClick={() => send()} disabled={busy || !input.trim()}><Send size={16} />Send</button>
          </div>
        </div>
        {showPanel && (
          <Inspector fusion={fusion} tier={tier} trajectory={traj} reasons={reasons} provider={last?.provider} latency={last?.latency_ms}
            faceLive={camOn ? faceLive : null} language={convLang} onClose={() => setShowPanel(false)} />
        )}
      </div>
    </div>
  );
}

function MiniOrb() {
  return (
    <svg width="28" height="28" viewBox="-14 -14 28 28" aria-hidden>
      <defs><radialGradient id="mo" cx="38%" cy="32%" r="75%"><stop offset="0%" stopColor="#fffaf0" /><stop offset="35%" stopColor="#f3dfb4" /><stop offset="100%" stopColor="var(--accent)" /></radialGradient></defs>
      <circle r="13" fill="none" stroke="var(--gold)" strokeOpacity="0.5" />
      <circle r="9" fill="url(#mo)" />
    </svg>
  );
}
