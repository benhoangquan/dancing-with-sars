// CSS-style cubic-bezier easing, for camera moves that match the site's spring curve.

/** Returns f(x) for a cubic Bezier through (0,0), (x1,y1), (x2,y2), (1,1), like CSS `cubic-bezier()`. */
export function cubicBezier(x1: number, y1: number, x2: number, y2: number): (x: number) => number {
  const cx = 3 * x1;
  const bx = 3 * (x2 - x1) - cx;
  const ax = 1 - cx - bx;
  const cy = 3 * y1;
  const by = 3 * (y2 - y1) - cy;
  const ay = 1 - cy - by;
  const sampleX = (t: number) => ((ax * t + bx) * t + cx) * t;
  const sampleY = (t: number) => ((ay * t + by) * t + cy) * t;
  const slopeX = (t: number) => (3 * ax * t + 2 * bx) * t + cx;

  return (x) => {
    if (x <= 0) return 0;
    if (x >= 1) return 1;
    let t = x;
    for (let i = 0; i < 8; i++) {
      const err = sampleX(t) - x;
      if (Math.abs(err) < 1e-7) return sampleY(t);
      const slope = slopeX(t);
      if (Math.abs(slope) < 1e-7) break;
      t -= err / slope;
    }
    let lo = 0;
    let hi = 1;
    t = x;
    for (let i = 0; i < 40 && lo < hi; i++) {
      const v = sampleX(t);
      if (Math.abs(v - x) < 1e-7) break;
      if (x > v) lo = t;
      else hi = t;
      t = (hi - lo) / 2 + lo;
    }
    return sampleY(t);
  };
}

/** The site's spring curve, cubic-bezier(0.22, 1, 0.36, 1). */
export const springEase = cubicBezier(0.22, 1, 0.36, 1);
