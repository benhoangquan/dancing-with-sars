// The flyover clock: turns beat progress into a smooth flyover time `t` in seconds.
import { type Beat, playHoldTime, scrubTime } from "./beats";

export interface SpringState {
  /** Current position. */
  x: number;
  /** Current velocity. */
  v: number;
}

/** One step of a critically damped spring toward `target`. Never overshoots from rest; exact for any dt. */
export function springStep(s: SpringState, target: number, dt: number, omega = 10): SpringState {
  const rel = s.x - target;
  const decay = Math.exp(-omega * dt);
  const k = s.v + omega * rel;
  return { x: target + (rel + k * dt) * decay, v: (s.v - omega * k * dt) * decay };
}

export class FlyoverClock {
  state: SpringState = { x: 0, v: 0 };
  /** Snap to the target instead of easing (prefers-reduced-motion). */
  reduced = false;
  private playKey = "";
  private playStart = 0;

  /** Advance by `dtSec`. `nowMs` is a monotonic clock, `beatKey` identifies the active beat. */
  update(nowMs: number, dtSec: number, beatKey: string, beat: Beat, p: number): number {
    const f = beat.stage.flyover;
    let target: number;
    if (f.playback === "scrub") {
      this.playKey = ""; // entering a play-hold beat later starts it from the beginning again
      target = scrubTime(f, p);
    } else {
      if (this.playKey !== beatKey) {
        this.playKey = beatKey;
        this.playStart = nowMs;
      }
      target = playHoldTime(f, (nowMs - this.playStart) / 1000);
    }
    this.state = this.reduced ? { x: target, v: 0 } : springStep(this.state, target, dtSec);
    return this.state.x;
  }
}
