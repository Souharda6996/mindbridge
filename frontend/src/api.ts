// Typed client for the MindBridge FastAPI backend (same origin).

export type Tier = "LOW" | "MEDIUM" | "HIGH";
export type Emotions = Record<string, number>;

export interface FacePayload {
  probs: Record<string, number>;
  reliability: number;
  details?: Record<string, unknown>;
}

export interface FusionOut {
  fused: number;
  confidence: number;
  smoothed: number;
  weights: Record<string, number>;
  contributions: Record<string, number>;
  emotions: Emotions;
  dominant_emotion: string;
  dominant_modality: string | null;
  explanations: string[];
  modalities: Record<string, { distress: number; reliability: number; age_s: number }>;
}

export interface Helpline { name: string; number: string; alt: string | null; languages: string }

export interface TurnOut {
  reply: string;
  provider: string;
  language: string;
  safety_flags: string[];
  llm_errors: string[];
  tier: Tier;
  urgency: string;
  reasons: string[];
  actions: { type: string; id?: string }[];
  alert_id: number | null;
  expression: string;
  risk: { level: number; level_name: string; tier: Tier; score: number; reasons: { rule: string; matched: string; negated: boolean }[]; idioms_ignored: string[] };
  text_emotion: { engine: string; top: { label: string; score: number }[]; emotions: Emotions; distress: number; reliability: number };
  voice: null | { engine: string; distress: number; reliability: number; emotions: Emotions; explanations: string[]; prosody?: { features?: Record<string, number | null> } };
  fusion: FusionOut;
  trajectory: { t: string; smoothed: number; fused: number; tier: Tier }[];
  helplines: Helpline[];
  latency_ms: number;
}
async function req<T>(method: string, url: string, body?: unknown): Promise<T> {
  const init: RequestInit = { method, headers: {} };
  if (body instanceof FormData) init.body = body;
  else if (body !== undefined) {
    init.body = JSON.stringify(body);
    (init.headers as Record<string, string>)["Content-Type"] = "application/json";
  }
  const res = await fetch(url, init);
  if (!res.ok) {
    let msg = `${res.status}`;
    try { msg = (await res.json()).detail ?? msg; } catch { /* ignore */ }
    throw new Error(String(msg));
  }
  return res.json() as Promise<T>;
}

export const api = {
  health: () => req<any>("GET", "/api/health"),
  startSession: (mode: string) => req<{ session_id: string; greeting: string; helplines: Helpline[]; companion: string; language: string }>("POST", "/api/session", { mode }),
  endSession: (sid: string) => req<any>("POST", `/api/session/${sid}/end`),
  chat: (session_id: string, text: string, face?: FacePayload | null) =>
    req<TurnOut>("POST", "/api/chat", { session_id, text, face: face ?? null }),
  voice: (fd: FormData) => req<TurnOut>("POST", "/api/voice", fd),
  face: (sid: string, face: FacePayload) => req<{ fusion: FusionOut }>("POST", `/api/session/${sid}/face`, face),
  simulate: (body: unknown) => req<FusionOut>("POST", "/api/fusion/simulate", body),
  analyzeText: (text: string) => req<any>("POST", "/api/analyze/text", { text }),
  dashboard: (days = 30) => req<any>("GET", `/api/dashboard?days=${days}`),
  checkins: () => req<any[]>("GET", "/api/checkins"),
  addCheckin: (body: unknown) => req<any>("POST", "/api/checkins", body),
  alerts: () => req<any[]>("GET", "/api/alerts"),
  updateAlert: (id: number, status: string, note?: string) => req<any>("POST", `/api/alerts/${id}`, { status, note }),
  requestCounselor: (session_id?: string | null) => req<any>("POST", "/api/counselor/request", { session_id }),
  notifyContact: (session_id?: string | null, alert_id?: number | null) =>
    req<any>("POST", "/api/trusted-contact/notify", { session_id, alert_id }),
  notifications: () => req<any[]>("GET", "/api/notifications"),
  settings: () => req<any>("GET", "/api/settings"),
  putSetting: (key: string, value: unknown) => req<any>("PUT", `/api/settings/${key}`, value),
  deleteAll: () => req<any>("DELETE", "/api/data"),
  reseed: () => req<any>("POST", "/api/demo/seed"),
  clearDemo: () => req<any>("DELETE", "/api/demo"),
  report: (days = 30) => req<any>("GET", `/api/report?days=${days}`),
  evaluate: () => req<any>("GET", "/api/eval"),
  llm: () => req<any>("GET", "/api/llm"),
  llmSetKey: (provider: string, api_key: string) => req<any>("POST", "/api/llm", { provider, api_key }),
  llmTest: (provider: string) => req<any>("POST", `/api/llm/test/${provider}`),
  llmRemove: (provider: string) => req<any>("DELETE", `/api/llm/${provider}`),
};

export const EMO_COLORS: Record<string, string> = {
  joy: "var(--e-joy)", sadness: "var(--e-sadness)", fear: "var(--e-fear)",
  anger: "var(--e-anger)", surprise: "var(--e-surprise)", neutral: "var(--e-neutral)",
};
export const EMO_HEX: Record<string, string> = {
  joy: "#c9962c", sadness: "#4b6f95", fear: "#7a5476", anger: "#b0502c", surprise: "#6c8a3e", neutral: "#9a9488",
};
export const MOD_COLORS: Record<string, string> = { face: "var(--m-face)", voice: "var(--m-voice)", text: "var(--m-text)" };

export function pct(x: number | null | undefined, digits = 0) {
  if (x === null || x === undefined || Number.isNaN(x)) return "-";
  return `${(x * 100).toFixed(digits)}%`;
}
export function timeAgo(iso: string) {
  const d = (Date.now() - new Date(iso).getTime()) / 1000;
  if (d < 60) return "just now";
  if (d < 3600) return `${Math.floor(d / 60)} min ago`;
  if (d < 86400) return `${Math.floor(d / 3600)} h ago`;
  return `${Math.floor(d / 86400)} d ago`;
}
