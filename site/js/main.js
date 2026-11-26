import { HexGrid, fmt, short, esc } from "./geo.js";
import { MapView, rampColor } from "./map.js";
import * as ui from "./ui.js";

const $ = (s) => document.querySelector(s);
const cache = new Map();
export function load(name) {
  if (!cache.has(name)) cache.set(name, fetch(`data/${name}.json`).then((r) => (r.ok ? r.json() : null)).catch(() => null));
  return cache.get(name);
}

const app = { lens: null, lensMeta: null, lensValues: null, mode: "present", sel: null, showResources: true };
window.app = app; // handy for debugging in the console

async function main() {
  const [world, lensIdx, cities, nation, states, points, wonders, hexyields] = await Promise.all(
    ["world", "lenses", "cities", "nation", "states", "points", "wonders", "hexyields"].map(load));
  const grid = new HexGrid(world.grid);
  const view = new MapView($("#map"), world, grid);
  Object.assign(app, { world, grid, view, lensIdx, cities, nation, states, points, wonders, hexyields, load });
  load("lines").then((l) => { app.lines = l; view.dirty = true; });
  app.landPos = new Map(world.land.map((c, k) => [c, k]));
  app.cityById = new Map(cities.map((c) => [c.id, c]));
  app.lensById = new Map(lensIdx.lenses.map((l) => [l.id, l]));
  app.stateById = new Map(states.map((s, k) => [s.id, { ...s, idx: world.states.findIndex((x) => x.id === s.id) }]));
  view.cities = cities.filter((c) => c.population).map((c) => ({ ...c, icon: c.specializations?.[0]?.icon, color: bannerColor(c) }));
  view.cities.push(...cities.filter((c) => !c.population && c.capital).map((c) => ({ ...c, icon: c.specializations?.[0]?.icon, color: "#5d6b7a" })));
  view.overlays.push(drawPointsWorld);
  view.screenOverlays.push(drawPointsScreen, drawYieldPips);
  view.onCamera = () => { ui.hideTooltip(); writeHash(); };

  ui.init(app);
  bindMap(view);
  // initial view: India land bounds
  const xs = world.land.map((i) => grid.cx[i]), ys = world.land.map((i) => grid.cy[i]);
  app.home = view.fit(Math.min(...xs), Math.min(...ys) + 150, Math.max(...xs) - 250, Math.max(...ys), 30);
  Object.assign(view.cam, app.home); view.clampCam();
  await readHash();
  if (!app.lens) ui.renderLegend();
  $("#loading").remove();
  window.addEventListener("resize", () => { view.resize(); view.clampCam(); });
}

function bannerColor(c) {
  const s = c.specializations?.[0]?.id;
  return { gold: "#b8862b", production: "#b0582a", science: "#2f6fb0", culture: "#7b4ba0", faith: "#8a7f5a", food: "#4f8a2f", infra: "#4f6a8a", port: "#2a7a8a", campus: "#2f6fb0", wonder: "#7b4ba0" }[s] || "#3d6e5a";
}

// ---------------- lens
export async function setLens(id) {
  const { view } = app;
  if (!id || id === app.lens) {
    app.lens = null; app.lensMeta = null; app.lensValues = null; app.lensSeries = null; stopPlay();
    view.setLens(null); ui.renderLensDock(); ui.renderLegend(); writeHash();
    if (document.getElementById("era-note")) import("./history.js").then((m) => m.overlayNote(app));
    return;
  }
  const meta = app.lensById.get(id); if (!meta) return;
  const data = await load(`lens/${id}`);
  app.lens = id; app.lensMeta = meta; app.lensValues = data.values;
  app.lensSeries = data.series ? data : null; app.yearIdx = data.series ? data.series.length - 1 : null;
  if (app.lensSeries && app.wantYear != null) { const k = data.years.indexOf(app.wantYear); if (k >= 0) { app.yearIdx = k; app.lensValues = data.series[k]; } }
  app.wantYear = null;
  view.setLens(lensColors(meta, app.lensValues));
  ui.renderLensDock(); ui.renderLegend(); writeHash();
  if (document.getElementById("era-note")) import("./history.js").then((m) => m.overlayNote(app));
}

export function setCustomLens(meta, values) {
  app.lensSeries = null; stopPlay();
  app.lens = meta.id; app.lensMeta = meta; app.lensValues = values;
  app.lensById.set(meta.id, meta);
  app.view.setLens(lensColors(meta, values));
  ui.renderLensDock(); ui.renderLegend();
}

// ---------- time-series lenses: one array per year ----------
export function setYear(k) {
  const s = app.lensSeries; if (!s) return;
  app.yearIdx = Math.max(0, Math.min(s.series.length - 1, k));
  app.lensValues = s.series[app.yearIdx];
  app.view.setLens(lensColors(app.lensMeta, app.lensValues));
  ui.updateYear(); writeHash();
  if (document.getElementById("era-note")) import("./history.js").then((m) => m.overlayNote(app));
}
let playTimer = null;
export function togglePlay() {
  if (playTimer) return stopPlay();
  const s = app.lensSeries; if (!s) return;
  if (app.yearIdx >= s.series.length - 1) setYear(0);
  playTimer = setInterval(() => { if (!app.lensSeries || app.yearIdx >= app.lensSeries.series.length - 1) return stopPlay(); setYear(app.yearIdx + 1); }, 900);
  ui.renderLegend();
}
export function stopPlay() { if (playTimer) { clearInterval(playTimer); playTimer = null; ui.renderLegend?.(); } }
export const isPlaying = () => !!playTimer;

export function lensT(meta, v) {
  if (v == null) return null;
  const st = meta.stats || {};
  if (meta.domain && meta.domain.length === 3) {
    const [a, m, b] = meta.domain; return v < m ? 0.5 * Math.max(0, (v - a) / (m - a)) : 0.5 + 0.5 * Math.min(1, (v - m) / (b - m));
  }
  let lo = meta.domain ? meta.domain[0] : st.p2, hi = meta.domain ? meta.domain[1] : st.p98;
  if (meta.scale === "log") { lo = Math.log(Math.max(lo, 1e-6)); hi = Math.log(Math.max(hi, 1e-6)); v = Math.log(Math.max(v, 1e-6)); }
  return hi > lo ? (v - lo) / (hi - lo) : 0.5;
}

function lensColors(meta, values) {
  const { world, grid } = app;
  const out = new Array(grid.n).fill(null);
  world.land.forEach((cell, k) => {
    const t = lensT(meta, values[k]);
    if (t == null) return;
    const c = rampColor(meta.ramp, Math.round(Math.max(0, Math.min(1, t)) * 40) / 40);
    out[cell] = `rgb(${c[0] | 0},${c[1] | 0},${c[2] | 0})`;
  });
  return out;
}

export function lensValueAt(cell) {
  if (!app.lensValues) return undefined;
  const k = app.landPos.get(cell); return k == null ? undefined : app.lensValues[k];
}

// ---------------- map interaction
function bindMap(view) {
  const cv = view.canvas;
  let drag = null, moved = false, pinch = null;
  const pts = new Map();
  cv.addEventListener("pointerdown", (e) => {
    cv.setPointerCapture(e.pointerId); pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pts.size === 2) { const [a, b] = [...pts.values()]; pinch = { d: Math.hypot(a[0] - b[0], a[1] - b[1]), s: view.cam.s }; }
    drag = { x: e.clientX, y: e.clientY, cx: view.cam.x, cy: view.cam.y }; moved = false;
  });
  cv.addEventListener("pointermove", (e) => {
    if (pts.has(e.pointerId)) pts.set(e.pointerId, [e.clientX, e.clientY]);
    if (pinch && pts.size === 2) {
      const [a, b] = [...pts.values()], d = Math.hypot(a[0] - b[0], a[1] - b[1]);
      view.zoomAt((a[0] + b[0]) / 2, (a[1] + b[1]) / 2, (pinch.s * d / pinch.d) / view.cam.s); moved = true; return;
    }
    if (drag && pts.size) {
      const dx = e.clientX - drag.x, dy = e.clientY - drag.y;
      if (Math.abs(dx) + Math.abs(dy) > 4) { moved = true; cv.classList.add("dragging"); }
      if (moved) { view.cam.x = drag.cx - dx / view.cam.s; view.cam.y = drag.cy - dy / view.cam.s; view.clampCam(); view.dirty = true; ui.hideTooltip(); }
      return;
    }
    hover(e.clientX, e.clientY);
  });
  const end = (e) => {
    pts.delete(e.pointerId); if (pts.size < 2) pinch = null;
    if (!pts.size) { cv.classList.remove("dragging"); if (drag && moved) view.onCamera?.(); drag = null; }
  };
  cv.addEventListener("pointerup", (e) => { const was = moved; end(e); if (!was) click(e.clientX, e.clientY); });
  cv.addEventListener("pointercancel", end);
  cv.addEventListener("pointerleave", () => { view.hover = -1; view.dirty = true; ui.hideTooltip(); });
  cv.addEventListener("wheel", (e) => { e.preventDefault(); view.zoomAt(e.clientX, e.clientY, Math.exp(-e.deltaY * (e.ctrlKey ? 0.01 : 0.0022))); }, { passive: false });
  cv.addEventListener("dblclick", (e) => { const [x, y] = view.toWorld(e.clientX, e.clientY); view.animateTo({ x, y, s: view.cam.s * 2.2 }, 400); });
  document.querySelectorAll("#zoom-ctl button").forEach((b) => b.addEventListener("click", () => view.animateTo({ s: view.cam.s * (b.dataset.z === "in" ? 1.8 : 1 / 1.8) }, 300)));
  $("#brand").addEventListener("click", () => { select(null); view.animateTo(app.home, 700); });
}

function pickAt(px, py) {
  const { view } = app;
  const c = view.bannerAt(px, py); if (c) return { type: "city", c };
  const p = app.pointHits?.find((h) => (px - h.x) ** 2 + (py - h.y) ** 2 <= h.r * h.r);
  if (p) return { type: "point", p: p.item };
  const [x, y] = view.toWorld(px, py); const cell = app.grid.cellAt(x, y);
  return { type: "cell", cell };
}

function hover(px, py) {
  const { view } = app;
  const hit = pickAt(px, py);
  const cell = hit.type === "cell" ? hit.cell : -1;
  if (cell !== view.hover) { view.hover = cell; view.dirty = true; }
  if (app.mode === "history" && app.history?.hover(px, py)) return;
  ui.tooltip(hit, px, py);
}

function click(px, py) {
  if (app.mode === "history" && app.history?.click(px, py)) return;
  const hit = pickAt(px, py);
  if (hit.type === "city") return select({ type: "city", id: hit.c.id });
  if (hit.type === "point") return select({ type: "point", item: hit.p });
  const k = app.world.kind[hit.cell];
  if (k !== 1) return select(null);
  select({ type: "cell", cell: hit.cell });
}

// ---------------- selection
export function select(sel, { fly = false } = {}) {
  const { view, world, grid } = app;
  app.sel = sel; view.selectedCity = null;
  if (!sel) { view.setHighlight(null); ui.closePanel(); writeHash(); return; }
  let cells = null;
  if (sel.type === "city") {
    const c = app.cityById.get(sel.id); view.selectedCity = view.cities.find((x) => x.id === sel.id) || null;
    cells = c.cells || [];
    if (fly) view.animateTo({ x: c.x + 120 / Math.max(view.cam.s, 1.6), y: c.y, s: Math.max(view.cam.s, 1.6) });
  } else if (sel.type === "district") {
    const d = world.districts.findIndex((x) => x.key === sel.key);
    cells = world.land.filter((i) => world.district[i] === d);
  } else if (sel.type === "district11") {
    const d = world.districts11.findIndex((x) => x.key === sel.key);
    cells = world.land.filter((i) => world.district11[i] === d);
  } else if (sel.type === "state") {
    const s = world.states.findIndex((x) => x.id === sel.id);
    cells = world.land.filter((i) => world.state[i] === s && world.disputed[i] < 0);
  } else if (sel.type === "cell") cells = [sel.cell];
  else if (sel.type === "point") cells = [];
  if (cells?.length && sel.type !== "cell") view.setHighlight(cells, { fill: "rgba(255,230,160,.10)" });
  else if (sel.type === "cell") view.setHighlight(cells, { fill: "rgba(255,230,160,.22)" });
  else view.setHighlight(null);
  if (fly && cells?.length && sel.type !== "city") flyToCells(cells);
  if (fly && sel.type === "point") view.animateTo({ x: sel.item.x, y: sel.item.y, s: Math.max(view.cam.s, 2.5) });
  ui.openPanel(sel);
  writeHash();
}

export function flyToCells(cells) {
  const { grid, view } = app;
  let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
  for (const i of cells) { x0 = Math.min(x0, grid.cx[i]); x1 = Math.max(x1, grid.cx[i]); y0 = Math.min(y0, grid.cy[i]); y1 = Math.max(y1, grid.cy[i]); }
  const pad = grid.hexR * 2;
  const drawer = document.querySelector("#strengths:not([hidden])");
  const t = view.fit(x0 - pad, y0 - pad, x1 + pad, y1 + pad, 60, view.W > 900 ? 400 : 0, view.W > 900 && drawer ? drawer.offsetWidth + 10 : 0);
  t.s = Math.min(t.s, 3.2); // district-level context, not single hexes
  view.animateTo(t);
}

export function highlightCells(cells, color) {
  app.view.setHighlight(cells, { fill: color || "rgba(255,230,160,.16)" });
}

// ---------------- resources and wonders
// Rail and road corridors (Natural Earth major lines), drawn with the resources layer.
function drawPointsWorld(ctx, view) {
  if (!app.showResources || app.mode === "history" || !app.lines) return;
  if (!app.linePaths) {
    app.linePaths = { road: new Path2D(), xway: new Path2D(), rail: new Path2D() };
    for (const l of app.lines.lines) {
      const p = app.linePaths[l.t === "rail" ? "rail" : l.e ? "xway" : "road"], a = l.pts;
      p.moveTo(a[0], a[1]); for (let k = 2; k < a.length; k += 2) p.lineTo(a[k], a[k + 1]);
    }
  }
  const hp = view.hexPx(), px = 1 / view.cam.s, P = app.linePaths;
  if (hp < 3) return;
  ctx.lineCap = ctx.lineJoin = "round";
  ctx.strokeStyle = "rgba(196,160,104,.8)"; ctx.lineWidth = Math.min(2.6, hp / 10) * px; ctx.stroke(P.road);
  ctx.strokeStyle = "rgba(232,196,120,.95)"; ctx.lineWidth = Math.min(3.4, hp / 8) * px; ctx.stroke(P.xway);
  ctx.strokeStyle = "rgba(28,22,18,.85)"; ctx.lineWidth = Math.min(3, hp / 9) * px; ctx.stroke(P.rail);
  if (hp > 9) { ctx.setLineDash([1.2 * px, 3.5 * px]); ctx.lineCap = "butt"; ctx.strokeStyle = "rgba(225,215,195,.8)"; ctx.lineWidth = Math.min(5, hp / 5) * px; ctx.stroke(P.rail); ctx.setLineDash([]); ctx.lineCap = "round"; }
}

function drawPointsScreen(ctx, view) {
  app.pointHits = [];
  if (app.mode === "history") return;
  const hp = view.hexPx();
  const W = view.W, H = view.H;
  // wonders
  const wonders = app.wonders?.items || [];
  if (hp > 2.2) {
    const r = hp > 10 ? 13 : hp > 5 ? 10 : 7; // small at national zoom, so wonders do not hide state names
    for (const w of wonders) {
      const [x, y] = view.toScreen(w.x, w.y);
      if (x < -20 || x > W + 20 || y < -20 || y > H + 20) continue;
      ctx.fillStyle = "rgba(0,0,0,.55)"; ctx.beginPath(); ctx.arc(x + 1, y + 2, r, 0, 7); ctx.fill();
      const g = ctx.createLinearGradient(x, y - r, x, y + r); g.addColorStop(0, "#f6dd94"); g.addColorStop(1, "#9a7428");
      ctx.fillStyle = g; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
      ctx.strokeStyle = "#2a1d08"; ctx.lineWidth = 1.2; ctx.stroke();
      ctx.font = `${r * 1.05}px sans-serif`; ctx.textAlign = "center"; ctx.textBaseline = "middle";
      ctx.fillText(w.rule === "unesco" ? (w.category === "Natural" ? "🌿" : "🏛️") : w.rule === "nirf10" ? "🎓" : "⚡", x, y + 1);
      app.pointHits.push({ x, y, r, item: { ...w, t: "wonder", n: w.name } });
    }
  }
  if (!app.showResources || !app.points) return;
  if (hp < 4.5) return;
  const types = new Map(app.points.types.map((t) => [t.id, t]));
  const r = Math.max(7, Math.min(12, hp * 0.32));
  ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.font = `${r * 1.15}px sans-serif`;
  const hiddenTypes = app.hiddenTypes || new Set(["medical"]);
  for (const it of app.points.items) {
    if (hiddenTypes.has(it.t)) continue;
    if (it.t === "monument" && hp < 16) continue;
    if (it.t === "mine" && hp < 7) continue;
    if (hp < 9 && it.t === "campus" && !(it.nirf_rank <= 50 || ["IIT", "IISc", "IIM"].includes(it.c))) continue;
    if (hp < 9 && it.t === "airport" && !(it.v > 2e6)) continue;
    const [x, y] = view.toScreen(it.x, it.y);
    if (x < -20 || x > W + 20 || y < -20 || y > H + 20) continue;
    ctx.fillStyle = "rgba(0,0,0,.35)"; ctx.beginPath(); ctx.arc(x + 1, y + 1.5, r, 0, 7); ctx.fill();
    ctx.fillStyle = "#efe4c6"; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
    ctx.strokeStyle = "#5a4520"; ctx.lineWidth = 1.2; ctx.stroke();
    ctx.fillText(types.get(it.t)?.emoji || "•", x, y + 1);
    app.pointHits.push({ x, y, r, item: it });
  }
}

function drawYieldPips(ctx, view) {
  const hp = view.hexPx();
  if (!app.showPips || hp < 30 || app.mode === "history" || !app.hexyields) return;
  const { grid, world } = app;
  const ys = app.hexyields.yields, P = app.hexyields.pips;
  const meta = new Map(app.nation.yields_meta.map((y) => [y.id, y]));
  const colors = { food: "#8bc34a", production: "#e0884a", gold: "#f2c94c", science: "#5ab0f0", culture: "#c58af0", faith: "#f3efe0", health: "#ef6f7a", infra: "#9fb4c8" };
  const v = view.visibleRange();
  ctx.font = "bold 10px sans-serif"; ctx.textAlign = "center"; ctx.textBaseline = "middle";
  for (let r = v.r0; r <= v.r1; r++) for (let c = v.c0; c <= v.c1; c++) {
    const i = r * grid.cols + c; const k = app.landPos.get(i); if (k == null) continue;
    const top = ys.map((y) => [y, P[y][k]]).filter(([y, p]) => p >= 3 && y !== "health").sort((a, b) => b[1] - a[1]).slice(0, 3);
    if (!top.length) continue;
    const [x, y] = view.toScreen(grid.cx[i], grid.cy[i]);
    const w = 15, x0 = x - (top.length * w) / 2 + w / 2, yy = y + hp * 0.42;
    top.forEach(([yid, p], j) => {
      ctx.fillStyle = "rgba(10,14,20,.8)"; ctx.beginPath(); ctx.arc(x0 + j * w, yy, 7, 0, 7); ctx.fill();
      ctx.strokeStyle = colors[yid]; ctx.lineWidth = 1.5; ctx.stroke();
      ctx.fillStyle = colors[yid]; ctx.fillText(String(p), x0 + j * w, yy + 0.5);
    });
  }
}

// ---------------- URL state
let hashTimer = 0;
function writeHash() {
  clearTimeout(hashTimer);
  hashTimer = setTimeout(() => {
    const { cam } = app.view; const p = new URLSearchParams();
    if (app.mode !== "present") p.set("mode", app.mode);
    if (app.lens) p.set("lens", app.lens);
    if (app.lensSeries && app.yearIdx !== app.lensSeries.series.length - 1) p.set("year", app.lensSeries.years[app.yearIdx]);
    if (app.mode === "history" && app.history?.era) p.set("era", app.history.era);
    if (app.mode === "history" && app.history?.compare) p.set("cmp", app.history.compare);
    const s = app.sel;
    if (s) p.set("sel", s.type === "city" ? `city:${s.id}` : s.type === "state" ? `state:${s.id}` : s.type === "district" ? `district:${s.key}` : s.type === "district11" ? `district11:${s.key}` : s.type === "cell" ? `cell:${s.cell}` : "");
    p.set("v", `${cam.x.toFixed(0)},${cam.y.toFixed(0)},${cam.s.toFixed(3)}`);
    history.replaceState(null, "", "#" + p.toString());
  }, 250);
}
async function readHash() {
  const p = new URLSearchParams(location.hash.slice(1));
  const v = p.get("v")?.split(",").map(Number);
  if (v?.length === 3 && v.every(Number.isFinite)) { Object.assign(app.view.cam, { x: v[0], y: v[1], s: v[2] }); app.view.clampCam(); }
  app.wantYear = p.get("year");
  if (p.get("lens")) await setLens(p.get("lens"));
  const sel = p.get("sel");
  if (sel) {
    const [t, ...rest] = sel.split(":"); const k = rest.join(":");
    if (t === "city" && app.cityById.has(k)) select({ type: "city", id: k });
    else if (t === "state") select({ type: "state", id: k });
    else if (t === "district" || t === "district11") select({ type: t, key: k });
    else if (t === "cell") select({ type: "cell", cell: +k });
  }
  app.wantCmp = p.get("cmp");
  if (p.get("mode") === "history") ui.setMode("history", p.get("era"));
}

export { app, writeHash };
main().catch((e) => { console.error(e); $("#loading").textContent = "Could not load the map data: " + e.message; });
