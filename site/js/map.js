// Canvas renderer: terrain / lens hexes, glyphs, rivers, borders, labels, banners, overlays.
import { short } from "./geo.js";

const OCEAN = "#102846";
const hash = (i) => { let x = Math.imul(i ^ 0x9e3779b9, 0x85ebca6b); x ^= x >>> 13; x = Math.imul(x, 0xc2b2ae35); x ^= x >>> 16; return (x >>> 0) / 4294967296; };
const hexToRgb = (h) => [parseInt(h.slice(1, 3), 16), parseInt(h.slice(3, 5), 16), parseInt(h.slice(5, 7), 16)];
const rgb = (c) => `rgb(${c[0] | 0},${c[1] | 0},${c[2] | 0})`;
const mix = (a, b, t) => [a[0] + (b[0] - a[0]) * t, a[1] + (b[1] - a[1]) * t, a[2] + (b[2] - a[2]) * t];

export function rampColor(ramp, t) {
  t = Math.max(0, Math.min(1, t));
  const cs = ramp.map(hexToRgb);
  const p = t * (cs.length - 1), k = Math.min(cs.length - 2, Math.floor(p));
  return mix(cs[k], cs[k + 1], p - k);
}

export class MapView {
  constructor(canvas, world, grid) {
    this.canvas = canvas; this.ctx = canvas.getContext("2d");
    this.w = world; this.g = grid;
    this.cam = { x: 0, y: 0, s: 0.3 };
    this.dirty = true;
    this.overlays = []; // functions (ctx, view) drawn in world space after borders
    this.screenOverlays = []; // functions drawn in screen space
    this.cities = [];
    this.highlight = null; // {cells:Set, color}
    this.hover = -1;
    this.lensColors = null; // Array<string|null> per cell, null => terrain
    this.dimTerrain = false;
    this.sprites = makeSprites();
    this.buildTerrainColors();
    this.buildBorders();
    this.buildRivers();
    this.buildLabels();
    this.rebuildBatches();
    this.resize();
    const loop = () => { if (this.dirty) { this.dirty = false; this.draw(); } requestAnimationFrame(loop); };
    requestAnimationFrame(loop);
  }

  resize() {
    const dpr = Math.min(2, window.devicePixelRatio || 1);
    this.dpr = dpr;
    this.W = this.canvas.clientWidth; this.H = this.canvas.clientHeight;
    this.canvas.width = Math.round(this.W * dpr); this.canvas.height = Math.round(this.H * dpr);
    this.dirty = true;
  }

  // ---------- camera ----------
  toWorld(px, py) { return [(px - this.W / 2) / this.cam.s + this.cam.x, (py - this.H / 2) / this.cam.s + this.cam.y]; }
  toScreen(x, y) { return [(x - this.cam.x) * this.cam.s + this.W / 2, (y - this.cam.y) * this.cam.s + this.H / 2]; }
  clampCam() {
    const g = this.g;
    const minS = Math.min(this.W / (g.hexW * g.cols), (this.H - 40) / (1.5 * g.hexR * g.rows));
    this.cam.s = Math.max(minS, Math.min(9, this.cam.s));
    const x0 = g.x0, x1 = g.x0 + g.hexW * g.cols, y0 = g.y0, y1 = g.y0 + 1.5 * g.hexR * g.rows;
    this.cam.x = Math.max(x0, Math.min(x1, this.cam.x));
    this.cam.y = Math.max(y0, Math.min(y1, this.cam.y));
  }
  fit(x0, y0, x1, y1, pad = 60, right = 0, left = 0) {
    const top = 42, bottom = 62; // top bar and lens dock: keep the fitted area clear of both
    const s = Math.min((this.W - 2 * pad - right - left) / (x1 - x0 || 1), (this.H - top - bottom - 2 * pad) / (y1 - y0 || 1));
    return { x: (x0 + x1) / 2 + (right - left) / 2 / s, y: (y0 + y1) / 2 + (bottom - top) / 2 / s, s };
  }
  animateTo(target, ms = 650) {
    const from = { ...this.cam }, t0 = performance.now();
    const ls0 = Math.log(from.s), ls1 = Math.log(target.s ?? from.s);
    cancelAnimationFrame(this._anim);
    const step = (now) => {
      let t = Math.min(1, (now - t0) / ms); t = t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2;
      this.cam.s = Math.exp(ls0 + (ls1 - ls0) * t);
      this.cam.x = from.x + ((target.x ?? from.x) - from.x) * t;
      this.cam.y = from.y + ((target.y ?? from.y) - from.y) * t;
      this.clampCam(); this.dirty = true;
      if (t < 1) this._anim = requestAnimationFrame(step); else this.onCamera?.();
    };
    this._anim = requestAnimationFrame(step);
  }
  zoomAt(px, py, f) {
    const [wx, wy] = this.toWorld(px, py);
    this.cam.s *= f; this.clampCam();
    const [nx, ny] = this.toWorld(px, py);
    this.cam.x += wx - nx; this.cam.y += wy - ny; this.clampCam();
    this.dirty = true; this.onCamera?.();
  }
  hexPx() { return this.g.hexR * this.cam.s; }

  // ---------- static geometry ----------
  buildTerrainColors() {
    const { w, g } = this;
    const cover = w.tables.cover;
    const n = g.n;
    this.terrain = new Array(n);
    for (let i = 0; i < n; i++) {
      const k = w.kind[i];
      const j = hash(i) * 0.08 - 0.04;
      if (k === 0 || k === 3) {
        const e = w.elev[i] ?? -2000;
        const wt = w.water[i];
        let c = wt === 3 ? [58, 128, 176] : wt === 2 ? mix([45, 109, 151], [27, 66, 102], Math.min(1, Math.max(0, -e / 600))) : mix([27, 66, 102], [16, 40, 70], Math.min(1, -e / 4500));
        c = c.map((v) => v * (1 + j * 0.5));
        this.terrain[i] = rgb(c.map((v) => Math.round(v / 3) * 3));
        continue;
      }
      let c = hexToRgb(cover[w.cover[i]]?.color || "#7f8a55");
      if (w.cover[i] === 0) c = [140, 140, 110];
      const rel = w.relief[i], e = w.elev[i] ?? 0;
      if (rel === 1) c = mix(c, [120, 100, 70], 0.18);
      if (rel === 2) c = mix(c, [128, 116, 100], 0.42);
      if (rel === 3) c = mix(c, [226, 232, 238], 0.55);
      c = mix(c, [210, 205, 190], Math.min(0.25, Math.max(0, e - 1500) / 12000));
      c = c.map((v) => v * (1 + j));
      if (k === 2) { const gr = (c[0] + c[1] + c[2]) / 3; c = mix(c, [gr, gr, gr], 0.55).map((v) => v * 0.62); }
      this.terrain[i] = rgb(c.map((v) => Math.round(v / 4) * 4));
    }
  }

  rebuildBatches() {
    const { g, w } = this;
    const batches = new Map();
    const add = (col, i) => { let p = batches.get(col); if (!p) batches.set(col, (p = new Path2D())); g.hexPath(p, i, 1.012); };
    const lc = this.lensColors;
    for (let i = 0; i < g.n; i++) {
      const k = w.kind[i];
      if (k === 0 && w.water[i] === 1 && w.elev[i] < -3500) { add(OCEAN, i); continue; }
      let col = this.terrain[i];
      if (lc && lc.all && (k === 1 || k === 2)) col = lc[i] || col;
      else if (lc && k === 1) col = lc[i] || "nodata";
      else if (lc && this.dimTerrain && k !== 0) col = dimColor(col);
      add(col, i);
    }
    this.batches = batches;
    this.noData = batches.get("nodata"); batches.delete("nodata");
    this.dirty = true;
  }

  buildBorders() {
    const { g, w } = this;
    const st = new Path2D(), dist = new Path2D(), intl = new Path2D(), coast = new Path2D(), disp = new Path2D(), dispCells = new Path2D(), grid = new Path2D();
    for (let i = 0; i < g.n; i++) {
      const k = w.kind[i];
      if (k === 1 || k === 3) g.hexPath(grid, i, 1);
      if (k !== 1) continue;
      if (w.disputed[i] >= 0) g.hexPath(dispCells, i, 1);
      const nb = g.neighbors(i);
      for (const j of nb) {
        if (j < 0) continue;
        const kj = w.kind[j];
        const e = g.edge(i, j);
        const seg = (p) => { p.moveTo(e[0], e[1]); p.lineTo(e[2], e[3]); };
        if (kj === 0) seg(coast);
        else if (kj === 2) seg(intl);
        else if (kj === 1 && j > i) {
          if ((w.disputed[i] >= 0) !== (w.disputed[j] >= 0)) seg(disp);
          else if (w.state[i] !== w.state[j]) seg(st);
          else if (w.district[i] !== w.district[j]) seg(dist);
        }
      }
    }
    Object.assign(this, { pStates: st, pDistricts: dist, pIntl: intl, pCoast: coast, pDisp: disp, pDispCells: dispCells, pGrid: grid });
    const pc = document.createElement("canvas"); pc.width = pc.height = 8;
    const x = pc.getContext("2d"); x.strokeStyle = "rgba(255,255,255,.35)"; x.lineWidth = 1.2;
    x.beginPath(); x.moveTo(0, 8); x.lineTo(8, 0); x.stroke();
    this.hatch = this.ctx.createPattern(pc, "repeat");
    const nc = document.createElement("canvas"); nc.width = nc.height = 8;
    const y = nc.getContext("2d"); y.fillStyle = "#2a2f36"; y.fillRect(0, 0, 8, 8); y.strokeStyle = "rgba(255,255,255,.12)"; y.beginPath(); y.moveTo(0, 8); y.lineTo(8, 0); y.stroke();
    this.noDataPattern = this.ctx.createPattern(nc, "repeat");
  }

  buildRivers() {
    this.rivers = [[], [], []];
    for (const r of this.w.rivers) {
      const p = new Path2D(); const a = r.pts;
      p.moveTo(a[0], a[1]); for (let k = 2; k < a.length; k += 2) p.lineTo(a[k], a[k + 1]);
      this.rivers[r.rank <= 4 ? 0 : r.rank <= 6 ? 1 : 2].push(p);
    }
  }

  buildLabels() {
    const { g, w } = this;
    const acc = new Map();
    for (const i of w.land) {
      const s = w.state[i]; if (s < 0 || w.disputed[i] >= 0) continue;
      const a = acc.get(s) || { x: 0, y: 0, n: 0, cells: [] };
      a.x += g.cx[i]; a.y += g.cy[i]; a.n++; a.cells.push(i); acc.set(s, a);
    }
    this.stateLabels = [];
    for (const [s, a] of acc) {
      const mx = a.x / a.n, my = a.y / a.n;
      let best = a.cells[0], bd = Infinity;
      for (const i of a.cells) { const d = (g.cx[i] - mx) ** 2 + (g.cy[i] - my) ** 2; if (d < bd) { bd = d; best = i; } }
      this.stateLabels.push({ s, x: g.cx[best], y: g.cy[best], n: a.n, name: w.states[s].name });
    }
    const dacc = new Map();
    for (const i of w.land) { const d = w.district[i]; if (d < 0) continue; const a = dacc.get(d) || { x: 0, y: 0, n: 0, c: [] }; a.x += g.cx[i]; a.y += g.cy[i]; a.n++; a.c.push(i); dacc.set(d, a); }
    this.districtLabels = [];
    this.districtCells = dacc;
    for (const [d, a] of dacc) {
      const mx = a.x / a.n, my = a.y / a.n; let best = a.c[0], bd = Infinity;
      for (const i of a.c) { const dd = (g.cx[i] - mx) ** 2 + (g.cy[i] - my) ** 2; if (dd < bd) { bd = dd; best = i; } }
      this.districtLabels.push({ d, x: g.cx[best], y: g.cy[best], n: a.n, name: w.districts[d].name });
    }
  }

  setLens(colors, dim = false) { this.lensColors = colors; this.dimTerrain = dim; this.rebuildBatches(); }

  // ---------- draw ----------
  draw() {
    const { ctx, cam, dpr, g } = this;
    const s = cam.s, hp = this.hexPx();
    ctx.setTransform(1, 0, 0, 1, 0, 0);
    ctx.fillStyle = OCEAN; ctx.fillRect(0, 0, this.canvas.width, this.canvas.height);
    ctx.setTransform(dpr * s, 0, 0, dpr * s, dpr * (this.W / 2 - cam.x * s), dpr * (this.H / 2 - cam.y * s));
    for (const [col, p] of this.batches) { ctx.fillStyle = col; ctx.fill(p); }
    if (this.noData) {
      ctx.save(); ctx.fillStyle = this.noDataPattern; ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
      ctx.translate(this.W / 2 - cam.x * s, this.H / 2 - cam.y * s); ctx.scale(s, s);
      // pattern in screen space: draw path scaled
      ctx.restore();
      ctx.fillStyle = "#2b3038"; ctx.fill(this.noData);
    }
    const px = 1 / s;
    this.drawEdgeFog(ctx);
    if (hp > 7) { ctx.strokeStyle = `rgba(0,0,0,${Math.min(0.22, (hp - 7) / 40)})`; ctx.lineWidth = px; ctx.stroke(this.pGrid); }
    // glyphs
    if (hp > 13 && !this.lensColors) this.drawGlyphs(hp);
    // rivers
    ctx.lineCap = ctx.lineJoin = "round";
    const rc = this.lensColors ? "rgba(140,200,240,.55)" : "#3d86bb";
    const rw = [Math.max(1.4, Math.min(5, hp * 0.16)), Math.max(1, Math.min(3.5, hp * 0.11)), Math.max(0.7, Math.min(2.4, hp * 0.07))];
    for (let k = 0; k < 3; k++) {
      if (k === 2 && hp < 5) continue;
      ctx.strokeStyle = rc; ctx.lineWidth = rw[k] * px;
      for (const p of this.rivers[k]) ctx.stroke(p);
    }
    // disputed hatch
    ctx.save(); ctx.clip(this.pDispCells); ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    ctx.fillStyle = this.hatch; ctx.fillRect(0, 0, this.W, this.H); ctx.restore();
    // borders
    if (this.historyMode) { ctx.strokeStyle = "rgba(60,40,20,.25)"; ctx.lineWidth = 1.2 * px; ctx.stroke(this.pStates); ctx.strokeStyle = "rgba(230,240,250,.35)"; ctx.stroke(this.pCoast); for (const o of this.overlays) o(ctx, this); ctx.setTransform(dpr, 0, 0, dpr, 0, 0); for (const o of this.screenOverlays) o(ctx, this); this.drawVignette(); return; }
    if (hp > 9) { ctx.strokeStyle = `rgba(20,14,6,${Math.min(0.5, (hp - 9) / 20)})`; ctx.lineWidth = Math.min(1.6, hp / 14) * px; ctx.setLineDash([4 * px, 3 * px]); ctx.stroke(this.pDistricts); ctx.setLineDash([]); }
    ctx.strokeStyle = "rgba(15,10,4,.75)"; ctx.lineWidth = Math.max(1.6, Math.min(3.6, hp / 6)) * px; ctx.stroke(this.pStates);
    ctx.strokeStyle = "rgba(236,208,142,.55)"; ctx.lineWidth = Math.max(0.6, Math.min(1.4, hp / 14)) * px; ctx.stroke(this.pStates);
    ctx.strokeStyle = "rgba(236,208,142,.9)"; ctx.lineWidth = Math.max(1.4, Math.min(3, hp / 8)) * px; ctx.stroke(this.pIntl);
    ctx.setLineDash([5 * px, 4 * px]); ctx.strokeStyle = "rgba(236,208,142,.75)"; ctx.stroke(this.pDisp); ctx.setLineDash([]);
    ctx.strokeStyle = "rgba(230,240,250,.35)"; ctx.lineWidth = Math.max(0.8, Math.min(2, hp / 10)) * px; ctx.stroke(this.pCoast);
    for (const o of this.overlays) o(ctx, this);
    // highlight
    if (this.highlight?.path) {
      ctx.fillStyle = this.highlight.fill || "rgba(255,230,160,.18)"; ctx.fill(this.highlight.path);
      ctx.strokeStyle = this.highlight.color || "#ffe39a"; ctx.lineWidth = 2.2 * px; ctx.stroke(this.highlight.edge || this.highlight.path);
    }
    if (this.hover >= 0) { const p = new Path2D(); g.hexPath(p, this.hover); ctx.strokeStyle = "rgba(255,245,210,.9)"; ctx.lineWidth = 1.5 * px; ctx.stroke(p); }
    // screen space
    ctx.setTransform(dpr, 0, 0, dpr, 0, 0);
    this.drawLabels(hp);
    for (const o of this.screenOverlays) o(ctx, this);
    this.drawBanners(hp);
    this.drawVignette();
  }

  drawEdgeFog(ctx) {
    const g = this.g, x0 = g.x0 - g.hexW, x1 = g.x0 + g.hexW * (g.cols + 0.5), y0 = g.y0 - g.hexR, y1 = g.y0 + 1.5 * g.hexR * (g.rows - 1) + g.hexR;
    const F = 260, bg = OCEAN, tr = "rgba(16,40,70,0)";
    const band = (ax, ay, bx, by, rx, ry, rw, rh) => { const gr = ctx.createLinearGradient(ax, ay, bx, by); gr.addColorStop(0, bg); gr.addColorStop(1, tr); ctx.fillStyle = gr; ctx.fillRect(rx, ry, rw, rh); };
    band(x0, 0, x0 + F, 0, x0 - 2000, y0 - 2000, F + 2000, y1 - y0 + 4000);
    band(x1, 0, x1 - F, 0, x1 - F, y0 - 2000, F + 2000, y1 - y0 + 4000);
    band(0, y0, 0, y0 + F, x0 - 2000, y0 - 2000, x1 - x0 + 4000, F + 2000);
    band(0, y1, 0, y1 - F, x0 - 2000, y1 - F, x1 - x0 + 4000, F + 2000);
  }

  visibleRange() {
    const [x0, y0] = this.toWorld(-40, -40), [x1, y1] = this.toWorld(this.W + 40, this.H + 40);
    const g = this.g;
    return {
      r0: Math.max(0, Math.floor((y0 - g.y0) / (1.5 * g.hexR))), r1: Math.min(g.rows - 1, Math.ceil((y1 - g.y0) / (1.5 * g.hexR))),
      c0: Math.max(0, Math.floor((x0 - g.x0) / g.hexW) - 1), c1: Math.min(g.cols - 1, Math.ceil((x1 - g.x0) / g.hexW)),
    };
  }

  drawGlyphs(hp) {
    const { ctx, g, w, sprites } = this;
    const v = this.visibleRange();
    const sz = g.hexR * 1.25;
    ctx.globalAlpha = Math.min(1, (hp - 13) / 8);
    for (let r = v.r0; r <= v.r1; r++) for (let c = v.c0; c <= v.c1; c++) {
      const i = r * g.cols + c; const k = w.kind[i];
      if (k !== 1 && k !== 2) continue;
      const rel = w.relief[i], cov = w.cover[i];
      let sp = null;
      if (rel === 3) sp = sprites.peak; else if (rel === 2) sp = sprites.mountain; else if (rel === 1) sp = sprites.hill;
      else if (cov === 1) sp = sprites.jungle; else if (cov === 2 || cov === 3) sp = sprites.forest;
      else if (cov === 9) sp = sprites.dune; else if (cov === 8) sp = sprites.marsh; else if (cov === 12) sp = sprites.urban;
      if (!sp) continue;
      const jx = (hash(i) - 0.5) * g.hexR * 0.25, jy = (hash(i + 7) - 0.5) * g.hexR * 0.2;
      if (k === 2) ctx.globalAlpha = 0.35; else ctx.globalAlpha = Math.min(1, (hp - 13) / 8);
      ctx.drawImage(sp, g.cx[i] - sz / 2 + jx, g.cy[i] - sz / 2 + jy, sz, sz);
    }
    ctx.globalAlpha = 1;
  }

  drawLabels(hp) {
    const ctx = this.ctx;
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    // state labels fade out when districts take over
    const sa = hp < 3 ? 0.55 : hp < 16 ? 0.8 : Math.max(0, 0.8 - (hp - 16) / 14);
    if (sa > 0.02 && !this.hideStateLabels) {
      for (const L of this.stateLabels) {
        const size = Math.max(9, Math.min(30, Math.sqrt(L.n) * hp * 0.32));
        if (size < 9.5 && L.n < 40) continue;
        const [x, y] = this.toScreen(L.x, L.y);
        if (x < -200 || x > this.W + 200 || y < -50 || y > this.H + 50) continue;
        ctx.font = `bold ${size}px ${getComputedStyle(document.body).getPropertyValue("--serif")}`;
        const t = L.name.toUpperCase().split("").join(String.fromCharCode(8202));
        ctx.globalAlpha = sa;
        ctx.lineWidth = 3; ctx.strokeStyle = "rgba(20,14,6,.55)"; ctx.strokeText(t, x, y);
        ctx.fillStyle = "rgba(250,240,215,.92)"; ctx.fillText(t, x, y);
      }
      ctx.globalAlpha = 1;
    }
    if (hp >= 14) {
      const da = Math.min(0.9, (hp - 14) / 10);
      ctx.font = `600 ${Math.min(14, 9 + hp / 12)}px ${getComputedStyle(document.body).getPropertyValue("--serif")}`;
      ctx.globalAlpha = da;
      for (const L of this.districtLabels) {
        const [x, y] = this.toScreen(L.x, L.y);
        if (x < -80 || x > this.W + 80 || y < -20 || y > this.H + 20) continue;
        ctx.lineWidth = 3; ctx.strokeStyle = "rgba(0,0,0,.6)"; ctx.strokeText(L.name, x, y + hp * 0.55);
        ctx.fillStyle = "#f3ead2"; ctx.fillText(L.name, x, y + hp * 0.55);
      }
      ctx.globalAlpha = 1;
    }
  }

  drawBanners(hp) {
    const { ctx } = this;
    if (!this.cities.length || this.hideBanners) return;
    const serif = getComputedStyle(document.body).getPropertyValue("--serif");
    const maxN = hp < 2.5 ? 12 : hp < 4 ? 22 : hp < 7 ? 40 : hp < 12 ? 70 : 200;
    const placed = [];
    this.bannerHits = [];
    let n = 0;
    for (const c of this.cities) {
      if (n >= maxN) break;
      const [x, y] = this.toScreen(c.x, c.y);
      if (x < -150 || x > this.W + 150 || y < -30 || y > this.H + 30) continue;
      const big = hp > 6;
      ctx.font = `bold ${big ? 12 : 11}px ${serif}`;
      const name = c.name.toUpperCase();
      const tw = ctx.measureText(name).width;
      const pop = short(c.population);
      ctx.font = `bold 11px ${getComputedStyle(document.body).getPropertyValue("--sans")}`;
      const pw = ctx.measureText(pop).width + 10;
      const h = big ? 22 : 19, w = pw + tw + 16 + (c.icon ? 18 : 0);
      let bx = 0, by = 0, ok = false;
      for (const [ox, oy] of [[-w / 2, -h - 6], [-w / 2, 6], [-w + 10, -h - 6], [-10, -h - 6], [8, -h / 2], [-w - 8, -h / 2]]) {
        bx = x + ox; by = y + oy;
        if (!placed.some((r) => bx < r[2] && bx + w > r[0] && by < r[3] && by + h > r[1])) { ok = true; break; }
      }
      if (!ok) continue;
      placed.push([bx - 3, by - 3, bx + w + 3, by + h + 3]);
      n++;
      // pin
      ctx.fillStyle = "rgba(0,0,0,.6)"; ctx.beginPath(); ctx.arc(x, y, 3.5, 0, 7); ctx.fill();
      ctx.fillStyle = c.capital === "national" ? "#ffd86b" : "#f3ead2"; ctx.beginPath(); ctx.arc(x, y, 2.3, 0, 7); ctx.fill();
      // body
      ctx.shadowColor = "rgba(0,0,0,.55)"; ctx.shadowBlur = 6; ctx.shadowOffsetY = 2;
      ctx.fillStyle = "rgba(14,20,28,.94)"; roundRect(ctx, bx, by, w, h, 4); ctx.fill();
      ctx.shadowColor = "transparent";
      ctx.fillStyle = c.color || "#3f7f9f"; roundRect(ctx, bx, by, pw, h, 4, [4, 0, 0, 4]); ctx.fill();
      ctx.strokeStyle = c === this.selectedCity ? "#ffe39a" : "rgba(201,164,92,.75)"; ctx.lineWidth = c === this.selectedCity ? 2 : 1;
      roundRect(ctx, bx, by, w, h, 4); ctx.stroke();
      ctx.textBaseline = "middle"; ctx.textAlign = "center";
      ctx.fillStyle = "#fff"; ctx.fillText(pop, bx + pw / 2, by + h / 2 + 0.5);
      ctx.font = `bold ${big ? 12 : 11}px ${serif}`; ctx.textAlign = "left";
      ctx.fillStyle = "#f6ecd0"; ctx.fillText((c.capital === "national" ? "★ " : "") + name, bx + pw + 7, by + h / 2 + 0.5);
      if (c.icon) { ctx.font = "12px sans-serif"; ctx.fillText(c.icon, bx + w - 19, by + h / 2 + 1); }
      // yield underline
      if (c.bar != null) { ctx.fillStyle = "rgba(255,255,255,.12)"; ctx.fillRect(bx + pw + 7, by + h - 4, tw, 2); ctx.fillStyle = "#7fd07a"; ctx.fillRect(bx + pw + 7, by + h - 4, tw * c.bar, 2); }
      this.bannerHits.push({ c, x0: bx, y0: by, x1: bx + w, y1: by + h + 8 });
    }
  }

  drawVignette() {
    const { ctx, W, H } = this;
    const gr = ctx.createRadialGradient(W / 2, H / 2, Math.min(W, H) * 0.45, W / 2, H / 2, Math.max(W, H) * 0.8);
    gr.addColorStop(0, "rgba(0,0,0,0)"); gr.addColorStop(1, "rgba(0,8,16,.45)");
    ctx.fillStyle = gr; ctx.fillRect(0, 0, W, H);
  }

  bannerAt(px, py) { return this.bannerHits?.find((b) => px >= b.x0 && px <= b.x1 && py >= b.y0 && py <= b.y1)?.c || null; }

  cellsPath(cells) { const p = new Path2D(); for (const i of cells) this.g.hexPath(p, i, 1.0); return p; }
  outlinePath(cells) {
    const set = cells instanceof Set ? cells : new Set(cells), p = new Path2D();
    for (const i of set) for (const j of this.g.neighbors(i)) if (j < 0 || !set.has(j)) { const e = this.g.edge(i, j); p.moveTo(e[0], e[1]); p.lineTo(e[2], e[3]); }
    return p;
  }
  setHighlight(cells, opts = {}) {
    if (!cells || !cells.length && !cells.size) { this.highlight = null; this.dirty = true; return; }
    this.highlight = { path: this.cellsPath(cells), edge: this.outlinePath(cells), ...opts };
    this.dirty = true;
  }
}

function dimColor(c) {
  const m = c.match(/\d+/g); if (!m) return c;
  const g = (+m[0] + +m[1] + +m[2]) / 3;
  return `rgb(${(g * 0.45) | 0},${(g * 0.47) | 0},${(g * 0.5) | 0})`;
}

function roundRect(ctx, x, y, w, h, r, radii) {
  ctx.beginPath();
  if (ctx.roundRect) ctx.roundRect(x, y, w, h, radii || r); else ctx.rect(x, y, w, h);
}

function makeSprites() {
  const S = 64;
  const mk = (fn) => { const c = document.createElement("canvas"); c.width = c.height = S; fn(c.getContext("2d")); return c; };
  const mountain = (snow, scale = 1) => (x) => {
    const peak = (cx, base, hw, h, sh) => {
      x.fillStyle = "rgba(0,0,0,.22)"; x.beginPath(); x.moveTo(cx - hw + 3, base + 2); x.lineTo(cx + 2, base - h + 2); x.lineTo(cx + hw + 3, base + 2); x.fill();
      x.fillStyle = "#8b7e6c"; x.beginPath(); x.moveTo(cx - hw, base); x.lineTo(cx, base - h); x.lineTo(cx + hw, base); x.fill();
      x.fillStyle = "#5e5446"; x.beginPath(); x.moveTo(cx, base - h); x.lineTo(cx + hw, base); x.lineTo(cx + hw * 0.15, base); x.fill();
      if (sh) { x.fillStyle = "#f4f6f8"; x.beginPath(); x.moveTo(cx - hw * sh, base - h * (1 - sh)); x.lineTo(cx, base - h); x.lineTo(cx + hw * sh, base - h * (1 - sh)); x.lineTo(cx + hw * sh * 0.3, base - h * (1 - sh * 0.7)); x.lineTo(cx - hw * sh * 0.2, base - h * (1 - sh * 1.1)); x.fill(); }
    };
    peak(24, 50, 15 * scale, 30 * scale, snow ? 0.42 : 0.2);
    peak(40, 54, 13 * scale, 24 * scale, snow ? 0.38 : 0);
  };
  const tree = (x, cx, cy, r, c1, c2) => {
    x.fillStyle = "rgba(0,0,0,.25)"; x.beginPath(); x.ellipse(cx + 2, cy + r * 0.9, r * 0.9, r * 0.35, 0, 0, 7); x.fill();
    x.fillStyle = c1; x.beginPath(); x.arc(cx, cy, r, 0, 7); x.fill();
    x.fillStyle = c2; x.beginPath(); x.arc(cx - r * 0.3, cy - r * 0.3, r * 0.55, 0, 7); x.fill();
  };
  return {
    peak: mk(mountain(true, 1.15)),
    mountain: mk(mountain(false)),
    hill: mk((x) => {
      for (const [cx, cy, r] of [[24, 44, 14], [42, 46, 11]]) {
        x.fillStyle = "rgba(0,0,0,.18)"; x.beginPath(); x.ellipse(cx + 2, cy + 1, r, r * 0.6, 0, Math.PI, 0); x.fill();
        x.fillStyle = "rgba(120,104,70,.85)"; x.beginPath(); x.ellipse(cx, cy, r, r * 0.6, 0, Math.PI, 0); x.fill();
        x.fillStyle = "rgba(170,150,100,.6)"; x.beginPath(); x.ellipse(cx - r * 0.25, cy - 1, r * 0.55, r * 0.35, 0, Math.PI, 0); x.fill();
      }
    }),
    forest: mk((x) => { tree(x, 22, 30, 9, "#2d5a26", "#4b7f3a"); tree(x, 40, 34, 8, "#2a5223", "#467a36"); tree(x, 30, 44, 8, "#305f28", "#4d843c"); }),
    jungle: mk((x) => { tree(x, 20, 28, 10, "#1d4a22", "#2f6b32"); tree(x, 40, 30, 10, "#1a4520", "#2c6830"); tree(x, 30, 44, 10, "#1f4f24", "#33723a"); tree(x, 48, 46, 7, "#1d4a22", "#2f6b32"); }),
    dune: mk((x) => { x.strokeStyle = "rgba(150,110,60,.55)"; x.lineWidth = 3; for (const y of [30, 40, 50]) { x.beginPath(); x.moveTo(12, y); x.quadraticCurveTo(30, y - 9, 50, y); x.stroke(); } }),
    marsh: mk((x) => { x.strokeStyle = "rgba(40,80,70,.8)"; x.lineWidth = 2; for (const cx of [20, 28, 36, 44]) { x.beginPath(); x.moveTo(cx, 48); x.lineTo(cx - 2, 32); x.stroke(); } x.fillStyle = "rgba(70,130,170,.5)"; x.fillRect(12, 48, 40, 4); }),
    urban: mk((x) => { for (const [bx, bw, bh] of [[16, 9, 22], [27, 10, 32], [39, 9, 18], [49, 7, 14]]) { x.fillStyle = "rgba(0,0,0,.3)"; x.fillRect(bx + 2, 54 - bh + 2, bw, bh); x.fillStyle = "#cfc6b2"; x.fillRect(bx, 54 - bh, bw, bh); x.fillStyle = "#8a8170"; x.fillRect(bx + bw - 3, 54 - bh, 3, bh); } }),
  };
}
