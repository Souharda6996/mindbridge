// Unit tests for the facial-expression logic. Run:  node frontend/tests/faceLogic.test.ts
// (Node 22.6+ strips TypeScript types natively.)
import {
  actionUnits, combine, describeAUs, emotionsFromAUs, geometry, priorCorrect, relativeToBaseline, type Pt,
} from "../src/lib/faceLogic.ts";

let failed = 0;
const check = (name: string, cond: boolean, info: unknown = "") => {
  console.log(`${cond ? "PASS" : "FAIL"}  ${name}${cond ? "" : "  " + JSON.stringify(info)}`);
  if (!cond) failed++;
};
const top = (p: Record<string, number>) => Object.entries(p).sort((a, b) => b[1] - a[1])[0][0];

// Neutral 68-point face in inter-ocular units (eye centres at x = -0.5 and 0.5).
function neutralFace(): Pt[] {
  const p: Pt[] = [];
  for (let i = 0; i <= 16; i++) { const t = (i / 16) * Math.PI; p.push({ x: -0.95 * Math.cos(t), y: 0.2 + 0.95 * Math.sin(t) }); }
  p.push({ x: -0.85, y: -0.3 }, { x: -0.7, y: -0.38 }, { x: -0.55, y: -0.41 }, { x: -0.38, y: -0.4 }, { x: -0.15, y: -0.36 });
  p.push({ x: 0.15, y: -0.36 }, { x: 0.38, y: -0.4 }, { x: 0.55, y: -0.41 }, { x: 0.7, y: -0.38 }, { x: 0.85, y: -0.3 });
  p.push({ x: 0, y: -0.05 }, { x: 0, y: 0.15 }, { x: 0, y: 0.3 }, { x: 0, y: 0.45 }, { x: -0.15, y: 0.55 }, { x: -0.08, y: 0.57 },
    { x: 0, y: 0.58 }, { x: 0.08, y: 0.57 }, { x: 0.15, y: 0.55 });
  p.push({ x: -0.7, y: 0 }, { x: -0.57, y: -0.06 }, { x: -0.43, y: -0.06 }, { x: -0.3, y: 0 }, { x: -0.43, y: 0.06 }, { x: -0.57, y: 0.06 });
  p.push({ x: 0.3, y: 0 }, { x: 0.43, y: -0.06 }, { x: 0.57, y: -0.06 }, { x: 0.7, y: 0 }, { x: 0.57, y: 0.06 }, { x: 0.43, y: 0.06 });
  p.push({ x: -0.4, y: 0.85 }, { x: -0.25, y: 0.78 }, { x: -0.1, y: 0.75 }, { x: 0, y: 0.76 }, { x: 0.1, y: 0.75 }, { x: 0.25, y: 0.78 },
    { x: 0.4, y: 0.85 }, { x: 0.25, y: 0.93 }, { x: 0.1, y: 0.96 }, { x: 0, y: 0.97 }, { x: -0.1, y: 0.96 }, { x: -0.25, y: 0.93 });
  p.push({ x: -0.35, y: 0.85 }, { x: -0.1, y: 0.83 }, { x: 0, y: 0.83 }, { x: 0.1, y: 0.83 }, { x: 0.35, y: 0.85 }, { x: 0.1, y: 0.87 },
    { x: 0, y: 0.87 }, { x: -0.1, y: 0.87 });
  return p;
}
const move = (pts: Pt[], idx: number[], dx: number, dy: number) => idx.forEach((i) => { pts[i] = { x: pts[i].x + dx, y: pts[i].y + dy }; });
const scale = (pts: Pt[], s: number) => pts.map((p) => ({ x: p.x * s + 120, y: p.y * s + 80 }));

const base = geometry(neutralFace());

// --- smile: corners out and up
const smile = neutralFace(); move(smile, [48, 60], -0.08, -0.06); move(smile, [54, 64], 0.08, -0.06);
const auSmile = actionUnits(geometry(smile), base);
check("smile -> happy", top(emotionsFromAUs(auSmile)) === "happy", emotionsFromAUs(auSmile));

// --- anger: brows down and together, lips pressed
const angry = neutralFace();
move(angry, [17, 18, 19, 20, 21, 22, 23, 24, 25, 26], 0, 0.07); move(angry, [21], 0.05, 0.03); move(angry, [22], -0.05, 0.03);
move(angry, [51], 0, 0.05); move(angry, [57], 0, -0.05);
const auAngry = actionUnits(geometry(angry), base);
check("lowered brows + pressed lips -> angry", top(emotionsFromAUs(auAngry)) === "angry", emotionsFromAUs(auAngry));
check("anger cues described", describeAUs(auAngry).includes("brows lowered"), describeAUs(auAngry));

// --- sadness: inner brows up, mouth corners down
const sad = neutralFace(); move(sad, [21, 22], 0, -0.06); move(sad, [48, 54, 60, 64], 0, 0.05);
check("inner brows up + corners down -> sad", top(emotionsFromAUs(actionUnits(geometry(sad), base))) === "sad",
  emotionsFromAUs(actionUnits(geometry(sad), base)));

// --- surprise: brows up, eyes wide, jaw dropped
const sur = neutralFace(); move(sur, [17, 18, 19, 20, 21, 22, 23, 24, 25, 26], 0, -0.1);
move(sur, [37, 38, 43, 44], 0, -0.04); move(sur, [40, 41, 46, 47], 0, 0.04); move(sur, [65, 66, 67, 55, 56, 57, 58, 59], 0, 0.3);
check("brows up + wide eyes + open mouth -> surprised", top(emotionsFromAUs(actionUnits(geometry(sur), base))) === "surprised",
  emotionsFromAUs(actionUnits(geometry(sur), base)));

// --- the resting face itself is neutral, and geometry is scale/translation invariant
check("resting face -> neutral", top(emotionsFromAUs(actionUnits(base, base))) === "neutral");
const g2 = geometry(scale(neutralFace(), 87));
check("geometry is scale-invariant", Math.abs(g2.mouthWidth - base.mouthWidth) < 1e-9 && Math.abs(g2.browHeight - base.browHeight) < 1e-9);

// --- the "always joy" bug: a person whose RESTING face the CNN reads as 60 % happy
const restingCnn = { neutral: 0.36, happy: 0.6, sad: 0.01, angry: 0.01, fearful: 0.01, disgusted: 0.005, surprised: 0.005 };
check("calibrated resting face is NOT joy", top(relativeToBaseline(restingCnn, restingCnn)) === "neutral");
const angryCnn = { neutral: 0.4, happy: 0.22, sad: 0.06, angry: 0.28, fearful: 0.02, disgusted: 0.01, surprised: 0.01 };
check("uncalibrated CNN alone says neutral for this angry frame", top(angryCnn) === "neutral");
check("calibration + action units -> angry", top(combine(angryCnn, { baseline: restingCnn, au: emotionsFromAUs(auAngry) })) === "angry",
  combine(angryCnn, { baseline: restingCnn, au: emotionsFromAUs(auAngry) }));
check("prior correction lifts under-predicted classes", priorCorrect(angryCnn).angry > angryCnn.angry);

console.log(failed ? `\n${failed} FAILED` : "\nall face-logic tests passed");
process.exit(failed ? 1 : 0);
