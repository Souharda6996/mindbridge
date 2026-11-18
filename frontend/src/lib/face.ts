// On-device facial emotion recognition (v2).
//
// Pipeline per frame (all inside the browser - frames never leave the device):
//   SSD-MobileNet face detector  ->  68-point landmarks  ->  expression CNN (7 emotions)
//   + personal baseline calibration + Facial Action Units (see faceLogic.ts)
//   + reliability score (detection confidence x face size x lighting x frontal pose)
//   + exponential smoothing.
import * as faceapi from "@vladmandic/face-api";
import type { FacePayload } from "../api";
import {
  actionUnits, averageGeometry, combine, describeAUs, ema, emotionsFromAUs, geometry, normalize,
  type Geometry, type Probs,
} from "./faceLogic";

let loaded: Promise<void> | null = null;

export function loadFaceModels(): Promise<void> {
  if (!loaded) {
    loaded = (async () => {
      // eslint-disable-next-line @typescript-eslint/no-explicit-any
      await (faceapi.tf as any).ready?.();
      await Promise.all([
        faceapi.nets.ssdMobilenetv1.loadFromUri("/models"),
        faceapi.nets.faceLandmark68Net.loadFromUri("/models"),
        faceapi.nets.faceExpressionNet.loadFromUri("/models"),
      ]);
    })();
  }
  return loaded;
}

const clamp = (x: number) => Math.max(0, Math.min(1, x));
const canvas = document.createElement("canvas");
canvas.width = 64;
canvas.height = 48;

function brightness(video: HTMLVideoElement): number {
  const ctx = canvas.getContext("2d", { willReadFrequently: true });
  if (!ctx) return 128;
  ctx.drawImage(video, 0, 0, 64, 48);
  const d = ctx.getImageData(0, 0, 64, 48).data;
  let sum = 0;
  for (let i = 0; i < d.length; i += 4) sum += 0.299 * d[i] + 0.587 * d[i + 1] + 0.114 * d[i + 2];
  return sum / (d.length / 4);
}

export interface FaceDetails {
  score: number; size: number; light: number; yaw: number; issue: string | null; found: boolean;
  calibrated: boolean; calibration: number; cues: string[]; top: string;
}
export interface FaceReading extends FacePayload {
  details: FaceDetails & Record<string, unknown>;
}

const CALIBRATION_FRAMES = 6;

export class FaceAnalyzer {
  private baseCnn: Probs[] = [];
  private baseGeo: Geometry[] = [];
  private baseline: Probs | null = null;
  private baselineGeo: Geometry | null = null;
  private smoothed: Probs | null = null;

  get calibrated() { return this.baseline !== null; }
  get calibrationProgress() { return this.baseline ? 1 : this.baseCnn.length / CALIBRATION_FRAMES; }

  recalibrate() {
    this.baseCnn = []; this.baseGeo = []; this.baseline = null; this.baselineGeo = null; this.smoothed = null;
  }

  async read(video: HTMLVideoElement): Promise<FaceReading> {
    const lum = brightness(video);
    const det = await faceapi
      .detectSingleFace(video, new faceapi.SsdMobilenetv1Options({ minConfidence: 0.45, maxResults: 1 }))
      .withFaceLandmarks()
      .withFaceExpressions();

    const empty = (issue: string): FaceReading => ({
      probs: { neutral: 1 }, reliability: 0,
      details: { score: 0, size: 0, light: lum, yaw: 0, issue, found: false, calibrated: this.calibrated,
        calibration: this.calibrationProgress, cues: [], top: "no face" },
    });
    if (!det) return empty(lum < 40 ? "too dark" : "no face detected");

    const box = det.detection.box;
    const pts = det.landmarks.positions.map((p) => ({ x: p.x, y: p.y }));
    const eyeL = pts[36], eyeR = pts[45], nose = pts[30];
    const yaw = (nose.x - (eyeL.x + eyeR.x) / 2) / Math.max(1, Math.abs(eyeR.x - eyeL.x));

    const fScore = clamp((det.detection.score - 0.45) / 0.45);
    const fSize = clamp(box.width / video.videoWidth / 0.22);
    const fLight = clamp((lum - 35) / 55);
    const fPose = clamp(1 - Math.abs(yaw) / 0.55);
    const reliability = (fScore * fSize * fLight * fPose) ** 0.6;
    const factors: [string, number][] = [["uncertain detection", fScore], ["face too far", fSize], ["low light", fLight], ["face turned away", fPose]];
    const worst = [...factors].sort((a, b) => a[1] - b[1])[0];

    const raw: Probs = {};
    for (const [k, v] of Object.entries(det.expressions)) if (typeof v === "number") raw[k] = v;
    const cnn = normalize(raw);
    const geo = geometry(pts);

    // personal baseline: only learn from steady, frontal, well-lit frames
    if (!this.baseline && reliability >= 0.45 && Math.abs(yaw) < 0.2) {
      this.baseCnn.push(cnn);
      this.baseGeo.push(geo);
      if (this.baseCnn.length >= CALIBRATION_FRAMES) {
        const avg: Probs = {};
        for (const p of this.baseCnn) for (const [k, v] of Object.entries(p)) avg[k] = (avg[k] ?? 0) + v / this.baseCnn.length;
        this.baseline = normalize(avg);
        this.baselineGeo = averageGeometry(this.baseGeo);
      }
    }

    let au = null;
    let cues: string[] = [];
    if (this.baselineGeo) {
      const units = actionUnits(geo, this.baselineGeo);
      au = emotionsFromAUs(units);
      cues = describeAUs(units);
    }
    // action units are geometric - trust them less when the head is turned
    const auWeight = 0.45 * fPose;
    const estimate = combine(cnn, { baseline: this.baseline, au, auWeight });
    this.smoothed = ema(this.smoothed, estimate, 0.45);
    const top = Object.entries(this.smoothed).sort((a, b) => b[1] - a[1])[0][0];

    return {
      probs: this.smoothed,
      reliability: Number(reliability.toFixed(3)),
      details: {
        score: det.detection.score, size: box.width / video.videoWidth, light: lum, yaw,
        issue: worst[1] < 0.5 ? worst[0] : null, found: true,
        calibrated: this.calibrated, calibration: this.calibrationProgress, cues, top,
      },
    };
  }
}

/** Diagnostic used by the test checklist: loads the models and runs one detection on a canvas. */
export async function selfTest(): Promise<{ backend: string; ranDetection: boolean; ms: number }> {
  const t0 = performance.now();
  await loadFaceModels();
  const c = document.createElement("canvas");
  c.width = 320; c.height = 240;
  const ctx = c.getContext("2d")!;
  ctx.fillStyle = "#ccc"; ctx.fillRect(0, 0, 320, 240);
  await faceapi.detectSingleFace(c, new faceapi.SsdMobilenetv1Options({ minConfidence: 0.45 })).withFaceLandmarks().withFaceExpressions();
  // eslint-disable-next-line @typescript-eslint/no-explicit-any
  const backend = (faceapi.tf as any).getBackend?.() ?? "unknown";
  return { backend, ranDetection: true, ms: Math.round(performance.now() - t0) };
}
// eslint-disable-next-line @typescript-eslint/no-explicit-any
(window as any).__mindbridgeFaceSelfTest = selfTest;
