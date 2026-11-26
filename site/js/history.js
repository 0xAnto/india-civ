// History mode: a separate timeline. Extents are approximate single-year snapshots.
import { project, fmt, esc } from "./geo.js";
import { load } from "./main.js";

const $ = (s) => document.querySelector(s);
const PAL = ["#d4a24a", "#b8584a", "#5a8ab8", "#7aa04a", "#a46ab8", "#c47a3a", "#4aa09a", "#b84a7a"];
const TYPE_ICON = { capital: "★", settlement: "●", monument: "▲", port: "⚓", university: "📜", battle: "⚔", trade_hub: "◆", religious_centre: "☸" };
const yr = (y) => (y == null ? "?" : y < 0 ? `${-y} BCE` : `${y} CE`);

export function prepareData(data) {
  if (data._prepared) return; data._prepared = true;
  for (const e of data.eras) {
    (e.polities || []).forEach((p, k) => {
      p._color = PAL[k % PAL.length];
      const g = p.extent?.geometry;
      if (!g) return;
      const path = new Path2D();
      const polys = g.type === "Polygon" ? [g.coordinates] : g.type === "MultiPolygon" ? g.coordinates : [];
      let bestA = 0, best = null;
      for (const poly of polys) for (const ring of poly) {
        let a = 0, cx = 0, cy = 0;
        ring.forEach(([lon, lat], j) => { const [x, y] = project(lon, lat); j ? path.lineTo(x, y) : path.moveTo(x, y); cx += x; cy += y; });
        path.closePath();
        for (let j = 0; j < ring.length - 1; j++) { const [x1, y1] = project(...ring[j]), [x2, y2] = project(...ring[j + 1]); a += x1 * y2 - x2 * y1; }
        if (Math.abs(a) > bestA) { bestA = Math.abs(a); best = [cx / ring.length, cy / ring.length]; }
      }
      p._path = path; p._label = best;
    });
    for (const pl of e.places || []) [pl._x, pl._y] = project(pl.lon, pl.lat);
    for (const p of e.polities || []) for (const c of p.capitals || []) [c._x, c._y] = project(c.lon, c.lat);
    for (const r of e.routes || []) { const path = new Path2D(); r.coords.forEach(([lon, lat], j) => { const [x, y] = project(lon, lat); j ? path.lineTo(x, y) : path.moveTo(x, y); }); r._path = path; }
  }
}

const probe = new OffscreenCanvas(1, 1).getContext("2d");
// Hexes (land, India or foreign) whose centre lies inside the polity's outline. Cached on the polity.
function cellsOf(app, p) {
  if (p._cells) return p._cells;
  const { world: w, grid: g } = app; const out = [];
  for (let i = 0; i < w.kind.length; i++) if ((w.kind[i] === 1 || w.kind[i] === 2) && probe.isPointInPath(p._path, g.cx[i], g.cy[i])) out.push(i);
  return (p._cells = out);
}
const HEX_KM2 = 346.4;
const B_FILL = "rgba(110,170,255,.24)", B_LINE = "#bcd8ff";
function badge(ctx, letter, x, y, color) {
  ctx.save(); ctx.beginPath(); ctx.arc(x, y, 9, 0, 7); ctx.fillStyle = "rgba(15,10,5,.85)"; ctx.fill();
  ctx.lineWidth = 1.5; ctx.strokeStyle = color; ctx.stroke();
  ctx.font = "bold 11px sans-serif"; ctx.fillStyle = color; ctx.textAlign = "center"; ctx.textBaseline = "middle"; ctx.fillText(letter, x, y + 0.5); ctx.restore();
}
export function eraCells(app, e) { const s = new Set(); for (const p of e?.polities || []) if (p._path) for (const i of cellsOf(app, p)) s.add(i); return s; }
// Approximate footprint of an era's mapped extents against today's map.
export function eraStats(app, e) {
  const w = app.world, cells = eraCells(app, e);
  let india = 0; const st = new Map();
  for (const i of cells) if (w.kind[i] === 1 && w.disputed[i] < 0) { india++; const s = w.state[i]; if (s >= 0) st.set(s, (st.get(s) || 0) + 1); }
  const top = [...st.entries()].sort((a, b) => b[1] - a[1]).slice(0, 4).map(([s]) => w.states[s].name);
  return { cells, km2: cells.size * HEX_KM2, indiaShare: cells.size ? india / cells.size : 0, states: st.size, top };
}
const short = (e) => e.name.split(/,| and | \(/)[0].trim(); // "Chola Empire, Chalukya and …" -> "Chola Empire"
const km = (v) => `${fmt(Math.round(v / 1000) * 1000)} km²`;

export class History {
  constructor(app) {
    this.app = app; this.era = null; this.data = null; this.hits = [];
    app.view.overlays.push((ctx, v) => this.drawWorld(ctx, v));
    app.view.screenOverlays.push((ctx, v) => this.drawScreen(ctx, v));
  }
  async enter(era) {
    this.data ||= await load("history");
    const v = this.app.view;
    this.saved = { lens: this.app.lens };
    v.hideBanners = true; v.hideStateLabels = true; v.historyMode = true;
    v.setLens(this.sepia(), false);
    this.prepare();
    $("#timeline").hidden = false;
    const cmp = this.app.wantCmp; this.app.wantCmp = null;
    if (cmp && this.data.eras.some((e) => e.id === cmp)) this.compare = cmp;
    this.select(era && this.data.eras.some((e) => e.id === era) ? era : this.data.eras[3]?.id || this.data.eras[0].id);
    if (this.compare) setTimeout(() => this.fitPair(), 350); // after the timeline and the card have their final size
    document.getElementById("panel").hidden = true;
    document.getElementById("era-note")?.setAttribute("hidden", "");
  }
  exit() {
    const v = this.app.view;
    if (!v.historyMode) return;
    v.hideBanners = false; v.hideStateLabels = false; v.historyMode = false;
    $("#timeline").hidden = true;
    document.getElementById("cmp-card")?.setAttribute("hidden", "");
    v.setLens(null);
    if (ov) overlayNote(this.app);
    import("./main.js").then((m) => { const l = this.saved?.lens; this.app.lens = null; if (l) m.setLens(l); });
  }
  sepia() {
    const v = this.app.view, w = this.app.world;
    const out = new Array(this.app.grid.n).fill(null);
    for (let i = 0; i < out.length; i++) {
      const k = w.kind[i]; if (k !== 1 && k !== 2) continue;
      const m = v.terrain[i].match(/\d+/g).map(Number);
      const g = 0.3 * m[0] + 0.59 * m[1] + 0.11 * m[2];
      const r = Math.min(255, g * 1.05 + 38), gg = Math.min(255, g * 0.92 + 28), b = Math.min(255, g * 0.7 + 10);
      out[i] = `rgb(${(r / 4 | 0) * 4},${(gg / 4 | 0) * 4},${(b / 4 | 0) * 4})`;
    }
    out.all = true;
    return out;
  }
  prepare() { prepareData(this.data); }
  select(id) {
    if (this.compare === id) this.compare = this.era; // picking B as A swaps the pair
    this.era = id;
    const e = this.data.eras.find((x) => x.id === id);
    const tl = $("#timeline");
    const mapped = (x) => (x.polities || []).some((p) => p._path);
    const cmpOn = this.picking || !!this.compare;
    tl.classList.toggle("picking", !!this.picking);
    tl.innerHTML = `<div class="tl-head">
        <button class="btn cmp-btn" id="cmp-toggle" aria-pressed="${cmpOn}" title="Compare two eras on one map (C)">${cmpOn ? "✕ Stop comparing" : "⇄ Compare eras"}</button>
        <span class="tl-hint">${this.picking ? `Pick an era to compare with <b>${esc(e.name)}</b>. Eras without a mapped outline are dimmed.` : this.compare ? "Click an era to change A. Shift-click an era to change B." : "Click an era to see its map."}</span>
      </div>
      <div class="eras">${this.data.eras.map((x) => {
        const role = x.id === id ? "a" : x.id === this.compare ? "b" : "";
        const off = this.picking && !mapped(x) && x.id !== id;
        return `<button class="era ${role ? "role-" + role : ""}" data-era="${x.id}" aria-pressed="${x.id === id}" ${off ? 'aria-disabled="true"' : ""} title="${mapped(x) ? "" : "No mapped outline for this era"}"><b>${role ? `<i class="badge ${role}">${role.toUpperCase()}</i> ` : ""}${esc(x.name)}</b><span>${yr(x.start)} – ${yr(x.end)}</span></button>`;
      }).join("")}</div>
      <div class="note"><b>${esc(e.name)}</b> (${yr(e.start)} – ${yr(e.end)}). ${esc(e.summary)}
      ${(e.polities || []).filter((p) => p.extent?.geometry).map((p) => `<span class="chip" style="border-color:${p._color}">${esc(p.name)} · map of ${yr(p.extent.year)} · ${esc(p.extent.confidence)} confidence</span>`).join("")}
      ${(e.polities || []).filter((p) => !p.extent?.geometry).map((p) => `<span class="chip faint" title="${esc(p.extent?.note || "No published polygon")}">${esc(p.name)} · no outline</span>`).join("")}
      <span class="faint">Sources: ${(e.sources || []).map((s) => `<a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.title)}</a>`).join(", ")}. Extents: historical-basemaps (approximate, single-year snapshots).</span></div>`;
    tl.querySelectorAll("[data-era]").forEach((btn) => btn.onclick = (ev) => {
      const x = btn.dataset.era;
      if (this.picking || (ev.shiftKey && this.compare)) {
        if (btn.getAttribute("aria-disabled") === "true" || x === this.era) return;
        return this.setCompare(x);
      }
      this.select(x);
    });
    tl.querySelector("#cmp-toggle").onclick = () => this.toggleCompare();
    tl.querySelector('[aria-pressed="true"]')?.scrollIntoView({ inline: "center", block: "nearest" });
    this.card();
    this.app.view.dirty = true;
    import("./main.js").then((m) => m.writeHash());
  }
  toggleCompare() {
    if (this.picking || this.compare) { this.picking = false; this.compare = null; }
    else this.picking = true;
    this.select(this.era);
  }
  setCompare(id) {
    this.picking = false; this.compare = id && id !== this.era ? id : null;
    this.select(this.era);
    if (this.compare) this.fitPair();
  }
  swap() { if (!this.compare) return; const a = this.era; this.era = this.compare; this.compare = a; this.select(this.era); }
  fitPair() {
    const g = this.app.grid, v = this.app.view;
    let x0 = Infinity, y0 = Infinity, x1 = -Infinity, y1 = -Infinity;
    for (const e of [this.current(), this.other()]) for (const i of eraCells(this.app, e)) { x0 = Math.min(x0, g.cx[i]); x1 = Math.max(x1, g.cx[i]); y0 = Math.min(y0, g.cy[i]); y1 = Math.max(y1, g.cy[i]); }
    if (!isFinite(x0)) return;
    // free screen area: below the compare card, above the timeline
    const top = (document.getElementById("cmp-card")?.getBoundingClientRect().bottom || 42) + 16;
    const bottom = ($("#timeline")?.getBoundingClientRect().top || v.H - 62) - 16;
    const s = Math.min((v.W - 80) / (x1 - x0 || 1), Math.max(60, bottom - top) / (y1 - y0 || 1));
    v.animateTo({ x: (x0 + x1) / 2, y: (y0 + y1) / 2 - ((top + bottom) / 2 - v.H / 2) / s, s });
  }
  current() { return this.data?.eras.find((x) => x.id === this.era); }
  other() { return this.compare ? this.data?.eras.find((x) => x.id === this.compare) : null; }
  // Floating "A vs B" card: keys, numbers side by side, and an overlap bar.
  card() {
    let el = document.getElementById("cmp-card");
    const a = this.current(), b = this.other();
    if (!b || this.app.mode !== "history") { if (el) el.hidden = true; return; }
    if (!el) { el = document.createElement("div"); el.id = "cmp-card"; el.className = "panel cmp-card"; document.body.appendChild(el); }
    const hasA = (a.polities || []).some((p) => p._path);
    const sa = hasA ? eraStats(this.app, a) : null, sb = eraStats(this.app, b);
    let both = 0; if (sa) for (const i of sa.cells) if (sb.cells.has(i)) both++;
    const nA = sa ? sa.cells.size : 0, nB = sb.cells.size, onlyA = nA - both, onlyB = nB - both, tot = Math.max(1, onlyA + both + onlyB);
    const pct = (x, n) => (n ? Math.round((x / n) * 100) + "%" : "—");
    const maps = (e) => (e.polities || []).filter((p) => p._path).map((p) => `${yr(p.extent.year)}, ${p.extent.confidence}`).filter((v, i, arr) => arr.indexOf(v) === i).join("; ");
    const col = (e, st, k) => `<div class="cc-col"><div class="cc-name"><i class="badge ${k}">${k.toUpperCase()}</i><span class="sw ${k}"></span><b>${esc(e.name)}</b></div><div class="faint">${yr(e.start)} – ${yr(e.end)} · map of ${esc(maps(e) || "—")} confidence</div></div>`;
    const row = (label, va, vb) => `<tr><th>${label}</th><td>${va}</td><td>${vb}</td></tr>`;
    el.innerHTML = `<div class="cc-head">${col(a, sa, "a")}<button class="icon-btn" id="cc-swap" title="Swap A and B" aria-label="Swap A and B">⇆</button>${col(b, sb, "b")}
        <button class="icon-btn cc-close" id="cc-close" aria-label="Stop comparing">✕</button></div>
      ${sa ? `<table class="cc-t"><tbody>
        ${row("Mapped area", km(sa.km2), km(sb.km2))}
        ${row("Inside today's India", pct(sa.indiaShare * 100, 100), pct(sb.indiaShare * 100, 100))}
        ${row("Today's states touched", `<span title="Most: ${esc(sa.top.join(", "))}">${sa.states} of 36</span>`, `<span title="Most: ${esc(sb.top.join(", "))}">${sb.states} of 36</span>`)}
      </tbody></table>
      <div class="cc-bar" role="img" aria-label="Only A ${km(onlyA * HEX_KM2)}, shared ${km(both * HEX_KM2)}, only B ${km(onlyB * HEX_KM2)}">
        <span class="a" style="flex:${onlyA / tot}"></span><span class="ab" style="flex:${both / tot}"></span><span class="b" style="flex:${onlyB / tot}"></span></div>
      <div class="cc-legend"><span><i class="sw a"></i>Only A ${km(onlyA * HEX_KM2)}</span><span><i class="sw ab"></i>Shared ${km(both * HEX_KM2)}</span><span><i class="sw b"></i>Only B ${km(onlyB * HEX_KM2)}</span></div>
      <p class="cc-sum"><b>${pct(both, nA)}</b> of the ${esc(short(a))} outline lies inside the ${esc(short(b))} outline; <b>${pct(both, nB)}</b> of the ${esc(short(b))} outline lies inside the ${esc(short(a))} outline.</p>`
      : `<p class="cc-sum">${esc(a.name)} has no mapped outline, so only ${esc(b.name)} is drawn (${km(sb.km2)}).</p>`}
      <p class="faint cc-foot">Areas count 346 km² hexes inside approximate single-year outlines (historical-basemaps).</p>`;
    el.hidden = false;
    el.querySelector("#cc-swap").onclick = () => this.swap();
    el.querySelector("#cc-close").onclick = () => this.setCompare(null);
  }
  drawWorld(ctx, v) {
    if (this.app.mode !== "history") return;
    const e = this.current(); if (!e) return;
    const px = 1 / v.cam.s;
    const ext = [...(e.polities || []), ...(this.other()?.polities || [])].filter((p) => p._path);
    if (ext.length) {
      const g = this.app.grid, all = new Path2D();
      all.rect(g.x0 - 500, g.y0 - 500, g.hexW * g.cols + 1000, 1.5 * g.hexR * g.rows + 1000);
      for (const p of ext) all.addPath(p._path);
      ctx.fillStyle = "rgba(25,14,4,.38)"; ctx.fill(all, "evenodd");
    }
    for (const p of e.polities || []) {
      if (!p._path) continue;
      ctx.save();
      ctx.fillStyle = p._color + (p.extent.confidence === "low" ? "38" : "50"); ctx.fill(p._path);
      ctx.shadowColor = p._color; ctx.shadowBlur = 14;
      ctx.setLineDash([7 * px, 5 * px]); ctx.strokeStyle = p._color; ctx.lineWidth = 2.8 * px; ctx.stroke(p._path);
      ctx.restore();
    }
    for (const p of this.other()?.polities || []) {
      if (!p._path) continue;
      ctx.save(); ctx.fillStyle = B_FILL; ctx.fill(p._path);
      ctx.strokeStyle = "rgba(10,10,20,.7)"; ctx.lineWidth = 4.5 * px; ctx.stroke(p._path);
      ctx.strokeStyle = B_LINE; ctx.lineWidth = 2.2 * px; ctx.stroke(p._path); ctx.restore();
    }
    for (const r of e.routes || []) {
      ctx.save(); ctx.setLineDash([2 * px, 5 * px]); ctx.lineCap = "round";
      ctx.strokeStyle = "rgba(60,30,10,.85)"; ctx.lineWidth = 3.2 * px; ctx.stroke(r._path);
      ctx.strokeStyle = "#f2d38a"; ctx.lineWidth = 1.8 * px; ctx.stroke(r._path); ctx.restore();
    }
  }
  drawScreen(ctx, v) {
    this.hits = [];
    if (this.app.mode !== "history") return;
    const e = this.current(); if (!e) return;
    const serif = getComputedStyle(document.body).getPropertyValue("--serif");
    ctx.textAlign = "center"; ctx.textBaseline = "middle";
    const placed = []; // screen boxes shared by polity and place labels
    const hitsBox = (bx) => placed.some((q) => bx[0] < q[2] && bx[2] > q[0] && bx[1] < q[3] && bx[3] > q[1]);
    const cmp = !!this.compare;
    // polity labels: A then B. In compare mode a label that collides is skipped (the card names every polity).
    const label = (p, letter) => {
      if (!p._label) return;
      const [x, y] = v.toScreen(...p._label);
      const isA = letter !== "B";
      ctx.font = isA ? `italic bold ${Math.max(13, Math.min(cmp ? 20 : 26, v.cam.s * 40))}px ${serif}` : `bold ${Math.max(12, Math.min(18, v.cam.s * 28))}px ${serif}`;
      const t = isA ? p.name.toUpperCase() : p.name, w = ctx.measureText(t).width + (cmp ? 22 : 0);
      const yy = isA || !cmp ? y : y + 22;
      const box = [x - w / 2, yy - 11, x + w / 2, yy + (isA && !cmp ? 26 : 11)];
      if (cmp && hitsBox(box)) return;
      placed.push(box);
      ctx.lineWidth = 4; ctx.strokeStyle = isA ? "rgba(30,18,6,.7)" : "rgba(10,10,20,.75)";
      const tx = x + (cmp ? 11 : 0);
      ctx.strokeText(t, tx, yy); ctx.fillStyle = isA ? "#fff1cf" : B_LINE; ctx.fillText(t, tx, yy);
      if (cmp) badge(ctx, letter, tx - ctx.measureText(t).width / 2 - 12, yy, isA ? "#f2c46a" : B_LINE);
      if (isA && !cmp) {
        ctx.font = `11px ${serif}`; ctx.fillStyle = "rgba(255,241,207,.85)";
        const sub = `map of ${yr(p.extent.year)} · ${p.extent.confidence} confidence`;
        ctx.strokeText(sub, x, y + 18); ctx.fillText(sub, x, y + 18);
      }
    };
    for (const p of e.polities || []) label(p, "A");
    for (const p of this.other()?.polities || []) label(p, "B");
    const hp = v.hexPx();
    const caps = [];
    for (const p of e.polities || []) for (const c of p.capitals || []) caps.push({ ...c, type: "capital", polity: p.name, color: p._color, _x: c._x, _y: c._y });
    const capNames = new Set(caps.map((c) => c.name));
    const items = [...caps, ...(e.places || []).filter((pl) => !(pl.type === "capital" && capNames.has(pl.name)))];
    for (const it of items) {
      const [x, y] = v.toScreen(it._x, it._y);
      if (x < -40 || x > v.W + 40 || y < -20 || y > v.H + 20) continue;
      const cap = it.type === "capital";
      const r = cap ? 8 : 5.5;
      ctx.fillStyle = "rgba(20,12,4,.8)"; ctx.beginPath(); ctx.arc(x, y, r + 1.5, 0, 7); ctx.fill();
      ctx.fillStyle = cap ? (it.color || "#f2d38a") : "#e8d6a8"; ctx.beginPath(); ctx.arc(x, y, r, 0, 7); ctx.fill();
      ctx.font = `${cap ? 11 : 8}px sans-serif`; ctx.fillStyle = "#24160a"; ctx.fillText(TYPE_ICON[it.type] || "●", x, y + 0.5);
      this.hits.push({ x, y, r: r + 3, it });
      const showLabel = cap || (hp > 4 && !cmp);
      if (!showLabel) continue;
      ctx.font = `${cap ? "bold 13px" : "11px"} ${serif}`;
      const w = ctx.measureText(it.name).width;
      const box = [x + r + 3, y - 8, x + r + 3 + w, y + 8];
      if (placed.some((b) => box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1])) continue;
      placed.push(box);
      ctx.textAlign = "left"; ctx.lineWidth = 3; ctx.strokeStyle = "rgba(20,12,4,.75)"; ctx.strokeText(it.name, x + r + 4, y); ctx.fillStyle = cap ? "#fff1cf" : "#efe0bb"; ctx.fillText(it.name, x + r + 4, y); ctx.textAlign = "center";
    }
  }
  hit(px, py) { return this.hits.find((h) => (px - h.x) ** 2 + (py - h.y) ** 2 <= h.r * h.r)?.it; }
  hover(px, py) {
    const it = this.hit(px, py); if (!it) return false;
    const el = $("#tooltip");
    el.innerHTML = `<b>${esc(it.name)}</b><div class="tl">${esc(it.type.replace("_", " "))}${it.polity ? " of " + esc(it.polity) : ""} · ${yr(it.start)} – ${yr(it.end)}</div>${it.note ? `<div>${esc(it.note)}</div>` : ""}`;
    el.hidden = false; el.style.left = px + 14 + "px"; el.style.top = py + 14 + "px";
    return true;
  }
  click(px, py) {
    const it = this.hit(px, py); if (!it) return false;
    const el = $("#panel"); el.hidden = false;
    el.innerHTML = `<header><button class="close icon-btn" aria-label="Close">✕</button><h2>${esc(it.name)}</h2><div class="sub">${esc(it.type.replace("_", " "))}${it.polity ? " of " + esc(it.polity) : ""}</div></header>
      <section><div class="kv"><span class="k">Period</span><span class="v">${yr(it.start)} – ${yr(it.end)}</span><span class="k">Coordinates</span><span class="v">${it.lat.toFixed(2)}°N ${it.lon.toFixed(2)}°E</span></div>
      ${it.note ? `<p>${esc(it.note)}</p>` : ""}
      <p>${it.wikipedia ? `<a href="${esc(it.wikipedia)}" target="_blank" rel="noopener">Wikipedia</a> · ` : ""}${it.qid ? `<a href="https://www.wikidata.org/wiki/${esc(it.qid)}" target="_blank" rel="noopener">Wikidata ${esc(it.qid)}</a>` : ""}</p>
      <div class="src"><span class="kind-badge kind-historical">historical</span> Coordinates and dates from Wikidata; dates are approximate.</div></section>`;
    el.querySelector(".close").onclick = () => (el.hidden = true);
    return true;
  }
}

// ---------- Present mode: a historical extent over a modern lens ----------
let ov = null; // { data, era }
export async function overlayMenu(app, anchor) {
  const data = await load("history"); prepareData(data);
  let pop = document.getElementById("era-pop");
  if (pop && !pop.hidden) { pop.hidden = true; return; }
  if (!pop) { pop = document.createElement("div"); pop.id = "era-pop"; pop.className = "panel era-pop"; document.body.appendChild(pop); }
  const mapped = data.eras.filter((x) => (x.polities || []).some((p) => p.extent?.geometry));
  pop.innerHTML = `<h4>Historical extent over today's map</h4>
    ${mapped.map((x) => `<button data-era="${x.id}" aria-pressed="${ov?.era.id === x.id}"><b>${esc(x.name)}</b><span>${yr(x.start)} – ${yr(x.end)}</span></button>`).join("")}
    <button data-era="" ${ov ? "" : "disabled"}>Remove overlay</button>
    <p class="faint">Outlines are approximate single-year maps (historical-basemaps). A pattern inside an old border is a description, not a cause.</p>`;
  const r = anchor.getBoundingClientRect();
  pop.style.left = Math.max(8, Math.min(innerWidth - 330, r.left - 140)) + "px"; pop.style.bottom = innerHeight - r.top + 8 + "px";
  pop.hidden = false;
  pop.onclick = (ev) => {
    const b = ev.target.closest("button[data-era]"); if (!b) return;
    const era = data.eras.find((x) => x.id === b.dataset.era);
    ov = era ? { data, era } : null; pop.hidden = true;
    if (!app._ovHooked) { app._ovHooked = true; app.view.overlays.push(drawOverlay); app.view.screenOverlays.push(drawOverlayLabels); }
    app.view.dirty = true; overlayNote(app);
  };
}
export function overlayActive() { return !!ov; }
function drawOverlay(ctx, v) {
  if (!ov || v.historyMode) return;
  const px = 1 / v.cam.s;
  for (const p of ov.era.polities || []) {
    if (!p._path) continue;
    ctx.save(); ctx.setLineDash([8 * px, 5 * px]); ctx.strokeStyle = "rgba(15,10,5,.8)"; ctx.lineWidth = 5 * px; ctx.stroke(p._path);
    ctx.strokeStyle = p._color; ctx.lineWidth = 2.6 * px; ctx.stroke(p._path); ctx.restore();
  }
}
function drawOverlayLabels(ctx, v) {
  if (!ov || v.historyMode) return;
  const serif = getComputedStyle(document.body).getPropertyValue("--serif");
  ctx.textAlign = "center"; ctx.textBaseline = "middle";
  const placed = [], fs = Math.max(11, Math.min(18, v.cam.s * 28));
  for (const p of ov.era.polities || []) {
    if (!p._label) continue;
    let [x, y] = v.toScreen(...p._label);
    ctx.font = `italic bold ${fs}px ${serif}`;
    const t = `${p.name} · ${yr(p.extent.year)}`, w = ctx.measureText(t).width;
    // ponytail: push a colliding label down one line; enough for the 3–6 polities of an era
    while (placed.some((b) => Math.abs(b[0] - x) < (b[2] + w) / 2 && Math.abs(b[1] - y) < fs + 4)) y += fs + 6;
    placed.push([x, y, w]);
    ctx.lineWidth = 4; ctx.strokeStyle = "rgba(20,12,4,.85)"; ctx.strokeText(t, x, y); ctx.fillStyle = "#fff1cf"; ctx.fillText(t, x, y);
    ctx.fillStyle = "rgba(20,12,4,.85)"; ctx.fillRect(x - w / 2 - 1, y + fs / 2 + 1, w + 2, 5); ctx.fillStyle = p._color; ctx.fillRect(x - w / 2, y + fs / 2 + 2, w, 3);
  }
}
// Mean of the current lens inside vs outside the extent (India's administered hexes only).
export async function overlayNote(app) {
  let el = document.getElementById("era-note");
  if (!ov) { if (el) el.hidden = true; return; }
  if (!el) { el = document.createElement("div"); el.id = "era-note"; el.className = "panel era-note"; document.body.appendChild(el); }
  const { lensValueAt } = await import("./main.js");
  const s = eraStats(app, ov.era), w = app.world;
  let cmp = "";
  if (app.lensMeta) {
    let si = 0, ni = 0, so = 0, no = 0;
    for (const i of w.land) {
      if (w.disputed[i] >= 0) continue;
      const v = lensValueAt(i); if (v == null || !isFinite(v)) continue;
      if (s.cells.has(i)) { si += v; ni++; } else { so += v; no++; }
    }
    if (ni && no) cmp = `<div>${app.lensMeta.emoji} ${esc(app.lensMeta.name)}: mean <b>${fmt(si / ni)}</b> inside vs <b>${fmt(so / no)}</b> outside <span class="faint">(${esc(app.lensMeta.unit)}, unweighted hex means)</span></div>`;
  }
  el.innerHTML = `<button class="close icon-btn" aria-label="Remove overlay">✕</button><b>${esc(ov.era.name)}</b> <span class="faint">${yr(ov.era.start)} – ${yr(ov.era.end)}</span>
    <div>${km(s.km2)} mapped; ${Math.round(s.indiaShare * 100)}% inside today's India; parts of ${s.states} of today's states.</div>${cmp}`;
  el.hidden = false;
  el.querySelector(".close").onclick = () => { ov = null; el.hidden = true; app.view.dirty = true; };
}
