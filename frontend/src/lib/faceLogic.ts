// Pure facial-expression logic (no browser APIs) so it can be unit-tested with Node.
//
// Three accuracy techniques on top of the CNN in face-api.js:
//  1. Prior correction   - FER-style expression CNNs over-predict "neutral" and "happy";
//                          until the person is calibrated we rebalance class priors.
//  2. Personal baseline  - the first ~4 s of good-quality frames learn THIS person's resting
//                          face; afterwards expressions are measured as CHANGES from it, so a
//                          resting face that the CNN calls "happy" no longer reads as joy.
//  3. Facial Action Units (FACS) - geometric measurements from the 68 landmarks (brow lowerer
//                          AU4, inner-brow raiser AU1, lip-corner puller AU12, depressor AU15,
//                          lip press AU24, jaw drop AU26, lid widen/tighten AU5/AU7, upper-lip
//                          raiser AU10) mapped to Ekman's emotion prototypes. Anger in particular
//                          is clearer in geometry (lowered brows + pressed lips) than in the CNN.

export type Pt = { x: number; y: number };
export type Probs = Record<string, number>;
export const EMOTIONS = ["neutral", "happy", "sad", "angry", "fearful", "disgusted", "surprised"] as const;

const clamp = (x: number) => Math.max(0, Math.min(1, x));
const dist = (a: Pt, b: Pt) => Math.hypot(a.x - b.x, a.y - b.y);
const mean = (pts: Pt[]): Pt => ({ x: pts.reduce((s, p) => s + p.x, 0) / pts.length, y: pts.reduce((s, p) => s + p.y, 0) / pts.length });

export function normalize(p: Probs): Probs {
  const s = Object.values(p).reduce((a, b) => a + b, 0) || 1;
  const out: Probs = {};
  for (const k of EMOTIONS) out[k] = (p[k] ?? 0) / s;
  return out;
}

// 1. ---------------------------------------------------------------- prior correction
const PRIOR = { neutral: 0.75, happy: 0.85, sad: 1.45, angry: 1.6, fearful: 1.6, disgusted: 1.5, surprised: 1.05 } as Record<string, number>;
export function priorCorrect(p: Probs): Probs {
  const out: Probs = {};
  for (const k of EMOTIONS) out[k] = (p[k] ?? 0) * PRIOR[k];
  return normalize(out);
}

// 2. ---------------------------------------------------------------- baseline-relative CNN
/** Positive change from the person's own resting distribution; no change -> neutral. */
export function relativeToBaseline(p: Probs, base: Probs, gain = 1.7): Probs {
  const out: Probs = {};
  let total = 0;
  for (const k of EMOTIONS) {
    if (k === "neutral") continue;
    out[k] = Math.max(0, (p[k] ?? 0) - (base[k] ?? 0)) * gain;
    total += out[k];
  }
  out.neutral = Math.max(0.05, 1 - total);
  return normalize(out);
}

// 3. ---------------------------------------------------------------- geometry / action units
export interface Geometry {
  browHeight: number; innerBrow: number; browGap: number; eyeOpen: number;
  mouthWidth: number; cornerLift: number; mouthOpen: number; lipThickness: number; noseLip: number;
}

/** Scale-free measurements from the 68-point iBUG landmark layout, in inter-ocular units. */
export function geometry(pts: Pt[]): Geometry {
  const eyeR = mean(pts.slice(36, 42)), eyeL = mean(pts.slice(42, 48));
  const iod = Math.max(1e-6, dist(eyeR, eyeL));
  const eyeY = (eyeR.y + eyeL.y) / 2;
  const ear = (e: Pt[]) => (dist(e[1], e[5]) + dist(e[2], e[4])) / (2 * Math.max(1e-6, dist(e[0], e[3])));
  const innerLipCenterY = (pts[62].y + pts[66].y) / 2;
  return {
    browHeight: (eyeY - mean(pts.slice(17, 27)).y) / iod,
    innerBrow: (eyeY - (pts[21].y + pts[22].y) / 2) / iod,
    browGap: dist(pts[21], pts[22]) / iod,
    eyeOpen: (ear(pts.slice(36, 42)) + ear(pts.slice(42, 48))) / 2,
    mouthWidth: dist(pts[48], pts[54]) / iod,
    cornerLift: (innerLipCenterY - (pts[48].y + pts[54].y) / 2) / iod,
    mouthOpen: dist(pts[62], pts[66]) / iod,
    lipThickness: (dist(pts[51], pts[62]) + dist(pts[57], pts[66])) / iod,
    noseLip: dist(pts[33], pts[51]) / iod,
  };
}

export function averageGeometry(gs: Geometry[]): Geometry {
  const out = {} as Geometry;
  (Object.keys(gs[0]) as (keyof Geometry)[]).forEach((k) => { out[k] = gs.reduce((s, g) => s + g[k], 0) / gs.length; });
  return out;
}

export interface ActionUnits {
  AU4_browLower: number; AU1_innerBrowRaise: number; AU2_browRaise: number; AU12_smile: number;
  AU15_cornerDepress: number; AU24_lipPress: number; AU26_jawDrop: number; AU5_lidRaise: number;
  AU7_lidTighten: number; AU10_upperLipRaise: number;
}

/** Action-unit intensities (0-1) from the change between the current face and the baseline. */
export function actionUnits(g: Geometry, b: Geometry): ActionUnits {
  const d = (k: keyof Geometry) => g[k] - b[k];
  return {
    AU4_browLower: clamp((-d("browHeight") - 0.012) / 0.05) * 0.6 + clamp((-d("browGap") - 0.015) / 0.07) * 0.4,
    AU1_innerBrowRaise: clamp((d("innerBrow") - 0.015) / 0.05),
    AU2_browRaise: clamp((d("browHeight") - 0.02) / 0.06),
    AU12_smile: clamp((d("mouthWidth") - 0.025) / 0.12) * 0.6 + clamp((d("cornerLift") - 0.008) / 0.05) * 0.4,
    AU15_cornerDepress: clamp((-d("cornerLift") - 0.008) / 0.035),
    AU24_lipPress: clamp((-d("lipThickness") - 0.02) / 0.06),
    AU26_jawDrop: clamp((d("mouthOpen") - 0.06) / 0.25),
    AU5_lidRaise: clamp((d("eyeOpen") - 0.03) / 0.08),
    AU7_lidTighten: clamp((-d("eyeOpen") - 0.03) / 0.08),
    AU10_upperLipRaise: clamp((-d("noseLip") - 0.02) / 0.06),
  };
}

/** Ekman / FACS emotion prototypes as weighted combinations of action units. */
export function emotionsFromAUs(a: ActionUnits): Probs {
  const happy = a.AU12_smile * 0.85 + a.AU7_lidTighten * 0.15 * a.AU12_smile;
  const angry = Math.max(0, a.AU4_browLower * 0.5 + a.AU24_lipPress * 0.25 + Math.max(a.AU5_lidRaise, a.AU7_lidTighten) * 0.25 - a.AU12_smile * 0.6);
  const sad = Math.max(0, a.AU1_innerBrowRaise * 0.35 + a.AU15_cornerDepress * 0.45 + a.AU4_browLower * 0.2 - a.AU12_smile * 0.6);
  const surprised = a.AU2_browRaise * 0.35 + a.AU5_lidRaise * 0.25 + a.AU26_jawDrop * 0.4;
  const fearful = Math.max(0, a.AU1_innerBrowRaise * 0.3 + a.AU5_lidRaise * 0.3 + a.AU4_browLower * 0.15 + a.AU26_jawDrop * 0.25 - a.AU12_smile * 0.5) * 0.85;
  const disgusted = Math.max(0, a.AU10_upperLipRaise * 0.6 + a.AU15_cornerDepress * 0.2 + a.AU4_browLower * 0.2 - a.AU12_smile * 0.5) * 0.9;
  const strongest = Math.max(happy, angry, sad, surprised, fearful, disgusted);
  return normalize({ neutral: Math.max(0.08, 1 - strongest * 1.15), happy, sad, angry, fearful, disgusted, surprised });
}

/** Human-readable cues for the strongest action units (shown in the UI). */
export function describeAUs(a: ActionUnits): string[] {
  const names: [keyof ActionUnits, string][] = [
    ["AU4_browLower", "brows lowered"], ["AU1_innerBrowRaise", "inner brows raised"], ["AU2_browRaise", "brows raised"],
    ["AU12_smile", "smiling"], ["AU15_cornerDepress", "mouth corners down"], ["AU24_lipPress", "lips pressed"],
    ["AU26_jawDrop", "mouth open"], ["AU5_lidRaise", "eyes widened"], ["AU7_lidTighten", "eyes narrowed"],
    ["AU10_upperLipRaise", "upper lip raised"],
  ];
  return names.filter(([k]) => a[k] >= 0.4).sort((x, y) => a[y[0]] - a[x[0]]).slice(0, 3).map(([, n]) => n);
}

/** Final estimate: calibrated CNN blended with action-unit evidence. */
export function combine(cnn: Probs, opts: { baseline?: Probs | null; au?: Probs | null; auWeight?: number }): Probs {
  const cnnPart = opts.baseline ? relativeToBaseline(cnn, opts.baseline) : priorCorrect(cnn);
  if (!opts.au) return cnnPart;
  const w = opts.auWeight ?? 0.45;
  const out: Probs = {};
  for (const k of EMOTIONS) out[k] = (1 - w) * cnnPart[k] + w * opts.au[k];
  return normalize(out);
}

/** Exponential moving average for steady readings. */
export function ema(prev: Probs | null, next: Probs, alpha = 0.45): Probs {
  if (!prev) return next;
  const out: Probs = {};
  for (const k of EMOTIONS) out[k] = alpha * next[k] + (1 - alpha) * (prev[k] ?? 0);
  return normalize(out);
}
