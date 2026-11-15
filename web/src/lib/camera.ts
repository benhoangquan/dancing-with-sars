// Camera interpolation along flyover waypoints. Mirrors pipeline/src/sarstory/flyover/camera.py;
// both follow docs/data_contract.md and both are tested against schema/golden/camera_interp.json.
import type { Camera, Waypoint } from "@/types/chapter";

const mod = (x: number, m: number) => ((x % m) + m) % m;

/** Bearing in degrees mapped into [-180, 180). */
export const normalizeBearing = (x: number) => mod(x + 180, 360) - 180;

/** Signed shortest rotation from b0 to b1 in [-180, 180). Exactly 180 degrees resolves to -180. */
export const shortestArc = (b0: number, b1: number) => mod(b1 - b0 + 540, 360) - 180;

export const smoothstep = (u: number) => u * u * (3 - 2 * u);

const lerp = (a: number, b: number, s: number) => a + (b - a) * s;

/** Camera at time `t` seconds; `t` is clamped to the waypoint range. */
export function cameraAt(waypoints: readonly Waypoint[], t: number): Camera {
  if (waypoints.length < 2) throw new Error("cameraAt needs at least two waypoints");
  const first = waypoints[0];
  const last = waypoints[waypoints.length - 1];
  const tc = Math.min(Math.max(t, first.t), last.t);
  let seg = waypoints.length - 2;
  for (let i = 0; i < waypoints.length - 1; i++) {
    if (waypoints[i].t <= tc && tc <= waypoints[i + 1].t) {
      seg = i;
      break;
    }
  }
  const w0 = waypoints[seg];
  const w1 = waypoints[seg + 1];
  const span = w1.t - w0.t;
  const s = smoothstep(span <= 0 ? 1 : (tc - w0.t) / span);
  const c0 = w0.camera;
  const c1 = w1.camera;
  return {
    center: [lerp(c0.center[0], c1.center[0], s), lerp(c0.center[1], c1.center[1], s)],
    zoom: lerp(c0.zoom, c1.zoom, s),
    pitch: lerp(c0.pitch, c1.pitch, s),
    bearing: normalizeBearing(c0.bearing + shortestArc(c0.bearing, c1.bearing) * s),
  };
}
