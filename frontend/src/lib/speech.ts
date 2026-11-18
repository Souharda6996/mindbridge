// Browser speech: live transcription (Web Speech API) and spoken replies (SpeechSynthesis).
// Both are free and built into Chrome / Edge.

/* eslint-disable @typescript-eslint/no-explicit-any */
const SR: any = (window as any).SpeechRecognition || (window as any).webkitSpeechRecognition;
export const sttSupported = Boolean(SR);
export const ttsSupported = "speechSynthesis" in window;

export class Transcriber {
  private rec: any = null;
  private finalText = "";
  onUpdate: (text: string, interim: string) => void = () => {};

  start(lang: string) {
    if (!SR) return;
    this.finalText = "";
    this.rec = new SR();
    this.rec.lang = lang;
    this.rec.continuous = true;
    this.rec.interimResults = true;
    this.rec.onresult = (e: any) => {
      let interim = "";
      for (let i = e.resultIndex; i < e.results.length; i++) {
        const r = e.results[i];
        if (r.isFinal) this.finalText += r[0].transcript + " ";
        else interim += r[0].transcript;
      }
      this.onUpdate(this.finalText.trim(), interim);
    };
    this.rec.onerror = () => {};
    try { this.rec.start(); } catch { /* already started */ }
  }

  stop(): Promise<string> {
    return new Promise((resolve) => {
      if (!this.rec) return resolve(this.finalText.trim());
      const done = () => resolve(this.finalText.trim());
      this.rec.onend = done;
      try { this.rec.stop(); } catch { done(); }
      setTimeout(done, 1200);
    });
  }
}

export function speak(text: string, lang: string, onStart: () => void, onEnd: () => void, onWord?: () => void) {
  if (!ttsSupported) { onEnd(); return; }
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  const voices = window.speechSynthesis.getVoices();
  const base = lang.split("-")[0];
  const preferred = voices.find((v) => v.lang === lang && /female|zira|heera|swara|neerja|google/i.test(v.name))
    || voices.find((v) => v.lang === lang) || voices.find((v) => v.lang.startsWith(base));
  if (preferred) u.voice = preferred;
  u.lang = preferred?.lang ?? lang;
  u.rate = 0.96;
  u.pitch = 1.02;
  u.onstart = onStart;
  u.onend = onEnd;
  u.onerror = onEnd;
  if (onWord) u.onboundary = onWord;
  window.speechSynthesis.speak(u);
}

export function stopSpeaking() {
  if (ttsSupported) window.speechSynthesis.cancel();
}
