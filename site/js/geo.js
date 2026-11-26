// Projection and hex geometry. Must match pipeline/common.py.
const R_EARTH = 6371.0088, LON0 = 82, LAT0 = 24, SP1 = 12.472944, SP2 = 35.172806;
const rad = (d) => (d * Math.PI) / 180;
const p1 = rad(SP1), p2 = rad(SP2), p0 = rad(LAT0);
const N = Math.log(Math.cos(p1) / Math.cos(p2)) / Math.log(Math.tan(Math.PI / 4 + p2 / 2) / Math.tan(Math.PI / 4 + p1 / 2));
const F = (Math.cos(p1) * Math.tan(Math.PI / 4 + p1 / 2) ** N) / N;
const RHO0 = (R_EARTH * F) / Math.tan(Math.PI / 4 + p0 / 2) ** N;

/** lon/lat -> [x east km, y south km] */
export function project(lon, lat) {
  const rho = (R_EARTH * F) / Math.tan(Math.PI / 4 + rad(lat) / 2) ** N;
  const th = N * rad(lon - LON0);
  return [rho * Math.sin(th), -(RHO0 - rho * Math.cos(th))];
}

export function unproject(x, y) {
  const dy = RHO0 + y;
  const rho = Math.sign(N) * Math.hypot(x, dy);
  const th = Math.atan2(x, dy);
  const lat = (2 * Math.atan((R_EARTH * F / rho) ** (1 / N)) - Math.PI / 2) * 180 / Math.PI;
  return [LON0 + (th / N) * 180 / Math.PI, lat];
}

export class HexGrid {
  constructor(g) {
    Object.assign(this, g); // cols, rows, x0, y0, hexW, hexR
    const n = this.cols * this.rows;
    this.n = n;
    this.cx = new Float32Array(n);
    this.cy = new Float32Array(n);
    for (let i = 0; i < n; i++) {
      const r = (i / this.cols) | 0, c = i % this.cols;
      this.cx[i] = this.x0 + this.hexW * (c + 0.5 * (r & 1));
      this.cy[i] = this.y0 + 1.5 * this.hexR * r;
    }
    this.corners = [];
    for (let k = 0; k < 6; k++) {
      const a = rad(30 + 60 * k);
      this.corners.push([this.hexR * Math.cos(a), this.hexR * Math.sin(a)]);
    }
  }
  neighbors(i) {
    const r = (i / this.cols) | 0, c = i % this.cols;
    const d = r & 1 ? [[-1, 0], [1, 0], [0, -1], [1, -1], [0, 1], [1, 1]] : [[-1, 0], [1, 0], [-1, -1], [0, -1], [-1, 1], [0, 1]];
    const out = [];
    for (const [dc, dr] of d) {
      const cc = c + dc, rr = r + dr;
      out.push(cc >= 0 && cc < this.cols && rr >= 0 && rr < this.rows ? rr * this.cols + cc : -1);
    }
    return out;
  }
  /** cell index at world point, or -1 */
  cellAt(x, y) {
    const r0 = Math.round((y - this.y0) / (1.5 * this.hexR));
    let best = -1, bd = Infinity;
    for (let r = r0 - 1; r <= r0 + 1; r++) {
      if (r < 0 || r >= this.rows) continue;
      const c0 = Math.round((x - this.x0) / this.hexW - 0.5 * (r & 1));
      for (let c = c0 - 1; c <= c0 + 1; c++) {
        if (c < 0 || c >= this.cols) continue;
        const i = r * this.cols + c;
        const d = (this.cx[i] - x) ** 2 + (this.cy[i] - y) ** 2;
        if (d < bd) { bd = d; best = i; }
      }
    }
    return best;
  }
  hexPath(path, i, f = 1) {
    const x = this.cx[i], y = this.cy[i], K = this.corners;
    path.moveTo(x + K[0][0] * f, y + K[0][1] * f);
    for (let k = 1; k < 6; k++) path.lineTo(x + K[k][0] * f, y + K[k][1] * f);
    path.closePath();
  }
  /** shared edge between cell i and its neighbour j as [x1,y1,x2,y2] */
  edge(i, j) {
    const th = Math.atan2(this.cy[j] - this.cy[i], this.cx[j] - this.cx[i]);
    const a1 = th - Math.PI / 6, a2 = th + Math.PI / 6, R = this.hexR;
    return [this.cx[i] + R * Math.cos(a1), this.cy[i] + R * Math.sin(a1), this.cx[i] + R * Math.cos(a2), this.cy[i] + R * Math.sin(a2)];
  }
}

export function fmt(v, digits) {
  if (v == null || Number.isNaN(v)) return "—";
  const a = Math.abs(v);
  if (digits != null) return v.toLocaleString("en-IN", { maximumFractionDigits: digits, minimumFractionDigits: 0 });
  if (a >= 1e7) return (v / 1e7).toLocaleString("en-IN", { maximumFractionDigits: a >= 1e9 ? 0 : 1 }) + " cr";
  if (a >= 1e5) return (v / 1e5).toLocaleString("en-IN", { maximumFractionDigits: 1 }) + " lakh";
  if (a >= 100) return Math.round(v).toLocaleString("en-IN");
  if (a >= 10) return v.toLocaleString("en-IN", { maximumFractionDigits: 1 });
  return v.toLocaleString("en-IN", { maximumFractionDigits: 2 });
}

/** short form for banners: 2.1Cr, 45L, 9.8K */
export function short(v) {
  if (v == null) return "—";
  if (v >= 1e7) return (v / 1e7).toFixed(v >= 1e8 ? 0 : 1) + "Cr";
  if (v >= 1e5) return Math.round(v / 1e5) + "L";
  if (v >= 1e3) return Math.round(v / 1e3) + "K";
  return String(Math.round(v));
}

export const esc = (s) => String(s ?? "").replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" })[c]);
