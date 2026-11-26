// Top bar, lens dock, legend, tooltip, side panels, search, mode switch.
import { fmt, short, esc } from "./geo.js";
import { setLens, select, lensValueAt, lensT, highlightCells, flyToCells, load, setYear, togglePlay, isPlaying } from "./main.js";
import { rampColor } from "./map.js";

const $ = (s) => document.querySelector(s);
let app;
const YC = { food: "#8bc34a", production: "#e0884a", gold: "#f2c94c", science: "#5ab0f0", culture: "#c58af0", faith: "#f3efe0", health: "#ef6f7a", infra: "#9fb4c8" };

export function init(a) {
  app = a;
  renderTopbar(); renderLensDock(); bindSearch();
  document.querySelectorAll(".mode-switch button").forEach((b) => b.addEventListener("click", () => setMode(b.dataset.mode)));
  $("#btn-explorer").addEventListener("click", () => openModal("explorer"));
  $("#btn-advisors").addEventListener("click", () => openModal("advisors"));
  $("#btn-strengths").addEventListener("click", async () => (await import("./strengths.js")).open(app));
  $("#btn-almanac").addEventListener("click", () => openModal("almanac"));
  $("#modal").addEventListener("click", (e) => { if (e.target.id === "modal" || e.target.closest("[data-close]")) closeModal(); });
  document.addEventListener("keydown", (e) => {
    if (e.target.matches("input, select, textarea")) { if (e.key === "Escape") e.target.blur(); return; }
    if (e.key === "/") { e.preventDefault(); $("#search-input").focus(); }
    else if (e.key === "Escape") { if (!$("#modal").hidden) closeModal(); else if (!$("#lens-picker").hidden) toggPicker(false); else select(null); }
    else if (e.key === "e" || e.key === "E") openModal("explorer");
    else if (e.key === "a" || e.key === "A") openModal("advisors");
    else if (e.key === "s" || e.key === "S") import("./strengths.js").then((m) => m.open(app));
    else if (e.key === "?") openModal("almanac");
    else if (e.key === "l" || e.key === "L") toggPicker();
    else if (e.key === "r" || e.key === "R") { app.showResources = !app.showResources; app.view.dirty = true; toast(app.showResources ? "Resources shown" : "Resources hidden"); }
    else if (e.key === "y" || e.key === "Y") { app.showPips = !app.showPips; app.view.dirty = true; renderLensDock(); }
    else if ((e.key === "c" || e.key === "C") && app.mode === "history") app.history?.toggleCompare();
    else if (e.key === "h" || e.key === "H") setMode(app.mode === "history" ? "present" : "history");
    else if (e.key === "+" || e.key === "=") app.view.animateTo({ s: app.view.cam.s * 1.6 }, 250);
    else if (e.key === "-") app.view.animateTo({ s: app.view.cam.s / 1.6 }, 250);
  });
}

export function toast(msg) {
  const t = $("#toast"); t.textContent = msg; t.hidden = false;
  clearTimeout(toast._t); toast._t = setTimeout(() => (t.hidden = true), 1800);
}

// ---------------- top bar
function yieldShort(id, v) {
  if (v == null) return "—";
  if (id === "gold" || id === "production") return "₹" + (v / 1e12).toFixed(v >= 1e14 ? 0 : 1) + "L cr";
  if (id === "food") return (v / 1e6).toFixed(0) + " Mt";
  return short(v);
}
function renderTopbar() {
  const el = $("#yields");
  el.innerHTML = app.nation.yields_meta.map((y) =>
    `<button class="yield" data-y="${y.id}" style="color:${YC[y.id]}" title="${esc(y.name)}: ${esc(fmt(app.nation.yields[y.id]))} ${esc(y.unit)}${y.missing_states.length ? ` — ${y.missing_states.length} states/UTs have no value in the source` : ""}. Click to show the ${esc(y.name)} lens.">
      <span class="yi">${y.emoji}</span>${yieldShort(y.id, app.nation.yields[y.id])}</button>`).join("");
  el.addEventListener("click", (e) => { const b = e.target.closest(".yield"); if (b) setLens(`y_${b.dataset.y}`); });
}

// ---------------- lenses
export function renderLensDock() {
  const quick = app.lensIdx.lenses.filter((l) => l.quick);
  const dock = $("#lens-dock");
  const terrainOn = !app.lens;
  dock.innerHTML = `<button class="lens-btn" data-lens="" aria-pressed="${terrainOn}" title="Terrain (no lens)"><span class="e">🗺️</span><span class="lbl">Terrain</span></button>` +
    quick.map((l) => `<button class="lens-btn" data-lens="${l.id}" aria-pressed="${app.lens === l.id}" title="${esc(l.name)}"><span class="e">${l.emoji}</span><span class="lbl">${esc(l.short || l.name.split(" ")[0])}</span></button>`).join("") +
    (app.lens && !quick.some((l) => l.id === app.lens) ? `<button class="lens-btn" data-lens="${app.lens}" aria-pressed="true"><span class="e">${app.lensMeta.emoji}</span>${esc(app.lensMeta.name)}</button>` : "") +
    `<button class="lens-btn" id="more-lenses" aria-expanded="${!$("#lens-picker").hidden}" title="All lenses (L)"><span class="e">☰</span>All ${app.lensIdx.lenses.length} lenses</button>` +
    `<button class="lens-btn" id="era-ov" aria-pressed="${!!document.querySelector("#era-note:not([hidden])")}" title="Lay a historical extent over today's map"><span class="e">🏺</span></button>` +
    `<button class="lens-btn" id="res-toggle" aria-pressed="${app.showResources}" title="Resources, wonders, main rail lines and highways (R). Lines: Natural Earth major corridors only"><span class="e">💎</span></button>` +
    `<button class="lens-btn" id="pip-toggle" aria-pressed="${!!app.showPips}" title="Tile yield pips when zoomed in (Y)"><span class="e">🔢</span></button>`;
  dock.onclick = (e) => {
    const b = e.target.closest("button"); if (!b) return;
    if (b.id === "more-lenses") return toggPicker();
    if (b.id === "era-ov") return import("./history.js").then((m) => m.overlayMenu(app, b));
    if (b.id === "res-toggle") { app.showResources = !app.showResources; app.view.dirty = true; return renderLensDock(); }
    if (b.id === "pip-toggle") { app.showPips = !app.showPips; app.view.dirty = true; if (app.showPips && app.view.hexPx() < 30) toast("Zoom in to see tile yields"); return renderLensDock(); }
    toggPicker(false);
    setLens(b.dataset.lens || null);
  };
  renderPicker();
}
function toggPicker(on) {
  const p = $("#lens-picker"); p.hidden = on === undefined ? !p.hidden : !on;
  $("#more-lenses")?.setAttribute("aria-expanded", String(!p.hidden));
}
function renderPicker() {
  const p = $("#lens-picker");
  p.innerHTML = app.lensIdx.groups.map((g) => {
    const ls = app.lensIdx.lenses.filter((l) => l.group === g.id);
    if (!ls.length) return "";
    return `<h4>${esc(g.name)}</h4>` + ls.map((l) => `<button data-lens="${l.id}" aria-pressed="${app.lens === l.id}" title="${esc(l.description)}"><span>${l.emoji}</span>${esc(l.name)}<span class="kindtag">${esc(resLabel(l))}</span></button>`).join("");
  }).join("");
  p.onclick = (e) => { const b = e.target.closest("button[data-lens]"); if (b) { setLens(b.dataset.lens); toggPicker(false); } };
}
const resLabel = (l) => ({ district2011: "district '11", district2020: "district '20", state: "state", raster: l.kind === "satellite" ? "satellite" : "grid", "hex model": "model" })[l.resolution] || l.resolution;

// Year slider, per-year note and a sparkline of the India value (when the source gives one).
function timeRow(l) {
  const S = app.lensSeries, k = app.yearIdx, years = S.years, y = years[k];
  return `<div class="time"><button class="icon-btn" id="yr-play" aria-label="${isPlaying() ? "Pause" : "Play"}">${isPlaying() ? "❚❚" : "▶"}</button>
      <input id="yr" type="range" min="0" max="${years.length - 1}" step="1" value="${k}" aria-label="Year">
      <b class="yr-l" id="yr-l">${esc(y)}</b></div>
    <div class="yr-ticks"><span>${esc(years[0])}</span><span>${esc(years[years.length - 1])}</span></div>
    <div id="yr-dyn">${yearDyn(l)}</div>`;
}
// The parts that change with the year; updated in place while the slider moves.
export function updateYear() {
  const l = app.lensMeta, S = app.lensSeries; if (!S) return;
  const lab = $("#yr-l"), dyn = $("#yr-dyn"), r = $("#yr");
  if (!lab || !dyn) return renderLegend();
  lab.textContent = S.years[app.yearIdx]; dyn.innerHTML = yearDyn(l);
  if (r && +r.value !== app.yearIdx) r.value = app.yearIdx;
}
function yearDyn(l) {
  const S = app.lensSeries, k = app.yearIdx, years = S.years, y = years[k];
  const N = l.series?.national, nat = N?.values, note = l.series?.notes?.[y];
  let spark = "";
  if (nat && nat.filter((v) => v != null).length > 1) {
    const vs = nat.filter((v) => v != null), lo = Math.min(...vs), hi = Math.max(...vs), W = 276, H = 34;
    const X = (i) => 4 + (i / (years.length - 1)) * (W - 8), Y = (v) => H - 4 - ((v - lo) / (hi - lo || 1)) * (H - 8);
    const pts = nat.map((v, i) => (v == null ? null : `${X(i).toFixed(1)},${Y(v).toFixed(1)}`)).filter(Boolean).join(" ");
    spark = `<svg class="spark" viewBox="0 0 ${W} ${H}" aria-label="India value per year"><polyline points="${pts}"/>${nat[k] != null ? `<circle cx="${X(k)}" cy="${Y(nat[k])}" r="3"/>` : ""}</svg>
      <div class="spark-l faint">${esc(N.label)}, ${esc(y)}: ${nat[k] != null ? `<b>${fmt(nat[k])}</b>${N.coverage[k] ? ` (${esc(N.coverage[k])} units report)` : ""}` : "not in source"}</div>`;
  }
  return `${note ? `<div class="yr-note">${esc(y)}: ${esc(note)}</div>` : ""}${spark}`;
}

export function renderLegend() {
  const el = $("#legend"); const l = app.lensMeta;
  if (!l) {
    const covers = app.world.tables.cover.filter((c) => c.id > 0);
    el.hidden = app.view.hexPx() > 999;
    el.innerHTML = `<div class="lt"><b>Terrain</b></div>
      <div class="lt2 muted">MODIS land cover 2023 · relief from terrain tiles · rivers: Natural Earth</div>
      <details ${innerHeight > 800 ? "open" : ""}><summary>Land cover classes</summary><div class="cats">${covers.map((c) => `<span title="${esc(c.rule)}"><i style="background:${c.color}"></i>${esc(c.name)}</span>`).join("")}<span class="wide" title="Areas inside India's official boundary administered by Pakistan or China. No statistics are shown."><i style="background:repeating-linear-gradient(135deg,#888 0 2px,#444 2px 4px)"></i>Claimed, administered by another country</span></div></details>`;
    return;
  }
  el.hidden = false;
  const ramp = `linear-gradient(90deg, ${l.ramp.map((c, i) => `${c} ${(i / (l.ramp.length - 1)) * 100}%`).join(",")})`;
  const st = l.stats || {};
  let ticks;
  if (l.domain && l.domain.length === 3) ticks = l.domain.map((v) => fmt(v));
  else {
    const lo = l.domain ? l.domain[0] : st.p2, hi = l.domain ? l.domain[1] : st.p98;
    const mid = l.scale === "log" ? Math.sqrt(Math.max(lo, 1e-6) * hi) : (lo + hi) / 2;
    ticks = [fmt(lo), fmt(mid), fmt(hi)];
  }
  const better = l.higher_is === "better" ? "Higher is better →" : l.higher_is === "worse" ? "Higher is worse →" : "";
  el.innerHTML = `<div class="lt"><span>${l.emoji}</span><b>${esc(l.name)}</b></div>
    <div class="lt2"><span class="muted">${esc(l.unit)}</span><span class="kind-badge kind-${esc(l.kind)}" style="margin-left:auto">${esc(l.kind)}</span><span class="faint">${esc(l.year || "")}</span></div>
    <div class="ramp" style="background:${ramp}"></div>
    <div class="ticks"><span>${ticks[0]}</span><span>${ticks[1]}</span><span>${ticks[2]}</span></div>
    ${better ? `<div class="dir">${better}</div>` : ""}
    ${app.lensSeries ? timeRow(l) : ""}
    <details${app.legendOpen ? " open" : ""}><summary>About this lens</summary><p>${esc(l.description)}</p>
    <p class="faint">Hatched grey = no data. Colours span the 2nd–98th percentile of hexes. Coverage ${Math.round((l.coverage ?? 1) * 100)}% of hexes.</p>
    <p><button class="linkish" data-src="${esc(l.source)}">Source: ${esc(l.source)}</button></p></details>`;
  el.querySelector("details").ontoggle = (e) => { app.legendOpen = e.target.open; };
  if (app.lensSeries) {
    el.querySelector("#yr").oninput = (e) => setYear(+e.target.value);
    el.querySelector("#yr-play").onclick = togglePlay;
  }
  el.querySelector("[data-src]").onclick = () => openModal("almanac", { source: l.source });
}

// ---------------- tooltip
const tt = () => $("#tooltip");
export function hideTooltip() { tt().hidden = true; }
export function tooltip(hit, px, py) {
  const { world } = app;
  let html = "";
  if (hit.type === "city") {
    const c = hit.c;
    html = `<b>${esc(c.name)}</b>${c.capital === "national" ? " ★ capital" : c.capital ? " · state capital" : ""}<div class="tl">${c.population ? fmt(c.population) + " · " + esc(c.population_kind) : "population not in source"}</div>` +
      (c.specializations?.length ? `<div>${c.specializations.map((s) => `${s.icon} ${esc(s.name)}`).join(" · ")}</div>` : "");
  } else if (hit.type === "point") {
    const p = hit.p; const t = app.points.types.find((x) => x.id === p.t);
    html = `<b>${esc(p.n)}</b><div class="tl">${t ? t.emoji + " " + esc(t.name) : p.t === "wonder" ? "🏛️ Wonder" : ""}${p.c ? " · " + esc(p.c) : ""}</div>` +
      (p.v != null && t?.unit ? `<div>${fmt(p.v)} ${esc(t.unit)}</div>` : "") + (p.year ? `<div class="tl">Inscribed ${p.year}</div>` : "");
  } else {
    const i = hit.cell; if (i < 0) return hideTooltip();
    const k = world.kind[i];
    if (k === 0 || k === 3) { html = `<b>${["", "Ocean", "Coast", "Lake"][world.water[i]] || "Water"}</b>` + (world.elev[i] != null && world.elev[i] < 0 ? `<div class="tl">mean depth ${fmt(-world.elev[i])} m</div>` : ""); }
    else if (k === 2) html = `<b>${esc(world.countries[world.country[i]] || "Neighbouring country")}</b><div class="tl">Outside India</div>`;
    else {
      const d = world.districts[world.district[i]], s = world.states[world.state[i]];
      const cov = world.tables.cover[world.cover[i]]?.name, rel = world.tables.relief[world.relief[i]]?.name;
      html = `<b>${esc(d?.name || "—")}</b> <span class="tl">${esc(s?.name || "")}</span><div class="tl">${esc(cov)} · ${esc(rel)} · ${fmt(world.elev[i])} m</div>`;
      if (world.disputed[i] >= 0) html += `<div>Claimed by India · administered by ${esc(world.disputedNames[world.disputed[i]])}. No statistics.</div>`;
      const v = lensValueAt(i);
      if (app.lensMeta && v !== undefined) html += `<div>${app.lensMeta.emoji} ${esc(app.lensMeta.name)}: <b>${v == null ? "no data" : fmt(v)}</b> <span class="tl">${v == null ? "" : esc(app.lensMeta.unit)}${app.lensSeries ? ` · ${esc(app.lensSeries.years[app.yearIdx])}` : ""}</span></div>`;
    }
  }
  const el = tt(); el.innerHTML = html; el.hidden = false;
  const w = el.offsetWidth, h = el.offsetHeight;
  el.style.left = Math.min(window.innerWidth - w - 8, px + 14) + "px";
  el.style.top = Math.min(window.innerHeight - h - 8, py + 14) + "px";
}

// ---------------- side panel
export function closePanel() { $("#panel").hidden = true; }
export async function openPanel(sel) {
  const el = $("#panel"); el.hidden = false; el.scrollTop = 0;
  let html = "";
  if (sel.type === "city") html = await cityPanel(app.cityById.get(sel.id));
  else if (sel.type === "state") html = await statePanel(sel.id);
  else if (sel.type === "district") html = await districtPanel(sel.key, "district2020");
  else if (sel.type === "district11") html = await districtPanel(sel.key, "district2011");
  else if (sel.type === "cell") html = await cellPanel(sel.cell);
  else if (sel.type === "point") html = pointPanel(sel.item);
  if (app.sel !== sel) return; // superseded
  el.innerHTML = html;
  el.querySelector(".close")?.addEventListener("click", () => select(null));
  el.querySelectorAll("[data-go]").forEach((b) => b.addEventListener("click", () => {
    const [t, ...k] = b.dataset.go.split(":"); const key = k.join(":");
    if (t === "city") select({ type: "city", id: key }, { fly: true });
    else if (t === "state") select({ type: "state", id: key }, { fly: true });
    else if (t === "district" || t === "district11") select({ type: t, key }, { fly: true });
    else if (t === "lens") setLens(key);
    else if (t === "explore") openModal("explorer", JSON.parse(decodeURIComponent(key)));
    else if (t === "source") openModal("almanac", { source: key });
  }));
}

const kv = (rows) => `<div class="kv">${rows.filter((r) => r).map(([k, v, unit, src]) => `<span class="k">${esc(k)}</span><span class="v">${v == null ? '<span class="faint">no data</span>' : esc(typeof v === "number" ? fmt(v) : v)}${unit ? ` <small>${esc(unit)}</small>` : ""}</span>`).join("")}</div>`;
const srcLine = (ids) => `<div class="src">Sources: ${ids.map((id) => `<button class="linkish" data-go="source:${esc(id)}">${esc(id)}</button>`).join(", ")}</div>`;
const header = (title, sub) => `<header><button class="close icon-btn" aria-label="Close">✕</button><h2>${esc(title)}</h2><div class="sub">${sub}</div></header>`;

async function tableRow(res, key) {
  const t = await load(`table_${res}`); if (!t) return null;
  const k = t.base.key.indexOf(String(key)); if (k < 0) return null;
  const row = { _t: t };
  for (const f in t.cols) row[f] = t.cols[f][k];
  return row;
}

function yieldsBlock(y, title = "Yields") {
  if (!y) return "";
  const metas = app.nation.yields_meta.filter((m) => y[m.id] != null);
  return `<section><h3>${title}</h3><div class="yield-row">${metas.map((m) => `<div class="yield-cell" title="${esc(m.unit)} — ${esc(m.note)}"><div class="yv" style="color:${YC[m.id]}">${m.emoji} ${yieldShort(m.id, y[m.id])}</div><div class="yl">${esc(m.name)}</div></div>`).join("")}</div></section>`;
}

async function cityPanel(c) {
  const st = app.world.states.find((s) => s.id === c.state);
  const d11 = c.district_2011, n5 = c.district_nfhs5;
  const cap = c.capital === "national" ? "★ National capital · " : c.capital ? "State capital · " : "";
  let h = header(c.name, `${cap}<button class="linkish" data-go="state:${c.state}">${esc(st?.name)}</button>`);
  h += `<section><div class="kv"><span class="k">Population</span><span class="v">${c.population ? fmt(c.population) : "—"} <small>${esc(c.population_kind || "not in source")}</small></span>
    <span class="k">Footprint population</span><span class="v">${fmt(c.footprint_pop_2011)} <small>7 hexes, Census 2011</small></span></div>
    ${c.hex_offset_km ? `<div class="src">The island is smaller than one hex. The nearest land hex of the same state, ${c.hex_offset_km} km away, stands in for the city.</div>` : ""}
    ${c.specializations?.length ? `<div style="margin-top:8px">${c.specializations.map((s) => `<span class="chip spec" title="${esc(s.evidence)}">${s.icon} ${esc(s.name)}</span>`).join("")}</div><div class="src">${c.specializations.map((s) => `${s.icon} ${esc(s.evidence)}`).join("<br>")}</div>` : `<div class="src">No yield per resident is 1.6× the median city in this footprint, and no facility hub rule applies.</div>`}</section>`;
  if (c.yields) {
    h += `<section><h3>City footprint yields</h3><div class="yield-row">${app.nation.yields_meta.filter((m) => c.yields[m.id] != null).map((m) => `<div class="yield-cell" title="${esc(m.note)}"><div class="yv" style="color:${YC[m.id]}">${m.emoji} ${yieldShort(m.id, c.yields[m.id])}</div><div class="yl">${esc(m.name)}</div><div class="faint" style="font-size:10px">${c.lq?.[m.id] != null ? c.lq[m.id].toFixed(1) + "× per resident" : ""}</div></div>`).join("")}</div>
      <div class="src">Footprint: the city's hex and its 6 neighbours (~2,400 km²). Yields come from the hex model (see Almanac → Yields); "× per resident" compares with India as a whole.</div></section>`;
  }
  if (d11) {
    const w = (d11.cultivators || 0) + (d11.agri_labourers || 0) + (d11.household_industry_workers || 0) + (d11.other_workers || 0);
    const job = (k, label, color) => { const v = d11[k] || 0; const p = w ? (v / w) * 100 : 0; return `<div class="row"><span>${label}</span><div class="bar"><i style="width:${p}%;background:${color}"></i></div><span class="num">${p.toFixed(0)}%</span></div>`; };
    h += `<section><h3>Work in ${esc(d11.name)} district (Census 2011)</h3><div class="jobs">${job("cultivators", "Cultivators", "#8bc34a")}${job("agri_labourers", "Farm labourers", "#b5c34a")}${job("household_industry_workers", "Household industry", "#e0884a")}${job("other_workers", "Other (industry, services)", "#5ab0f0")}</div>
      ${kv([["Literates per 100 people", d11.literacy_rate], ["Graduates", d11.pct_graduate, "%"], ["Women at work", d11.female_worker_participation, "% of women"], ["Urban households", d11.urban_household_share, "%"], ["Households with internet", d11.pct_hh_internet, "%"], ["Households with a car", d11.pct_hh_car, "%"], ["Electric lighting", d11.pct_hh_electric_lighting, "%"]])}
      <div class="src">Census 2011 values are for the whole core district, not only the city. <button class="linkish" data-go="district11:${esc(c.district2011)}">Open district</button></div></section>`;
  }
  if (n5) {
    h += `<section><h3>Health & living (NFHS-5, 2019–21)</h3>${kv([["Institutional births", n5.institutional_births, "%"], ["Full immunisation", n5.full_immunisation, "%"], ["Child stunting", n5.stunting, "%"], ["Health insurance", n5.health_insurance, "% hh"], ["Improved sanitation", n5.improved_sanitation, "%"], ["Clean cooking fuel", n5.clean_cooking_fuel, "%"], ["Women with 10+ yrs school", n5.women_10yr_school, "%"]])}
      <div class="src">District: ${esc(n5.name)}. <button class="linkish" data-go="district:${esc(c.district2020)}">Open district</button></div></section>`;
  }
  const nb = c.nearby || {};
  const lab = { campus: "🎓 Campuses & research", unesco: "🏛️ World Heritage", port: "⚓ Ports", airport: "✈️ Airports", power: "⚡ Power stations", medical: "⚕️ Medical colleges", defence: "🛠️ Defence production" };
  const blocks = Object.entries(nb).filter(([k, v]) => v.length && lab[k]);
  if (blocks.length) h += `<section><h3>In the footprint</h3>${blocks.map(([k, v]) => `<div style="margin-bottom:6px"><div class="muted">${lab[k]}</div><ul class="list-plain">${v.map((p) => `<li>${esc(p.name)}<span class="faint" style="margin-left:auto">${p.capacity_mw ? fmt(p.capacity_mw) + " MW" : p.passengers ? fmt(p.passengers) + " pax" : p.cargo_tonnes ? fmt(p.cargo_tonnes) + " t" : p.nirf_rank ? "NIRF #" + p.nirf_rank : esc(p.category || "")}</span></li>`).join("")}</ul></div>`).join("")}</section>`;
  h += `<section>${c.wikipedia ? `<a href="https://en.wikipedia.org/wiki/${encodeURIComponent(c.wikipedia)}" target="_blank" rel="noopener">Wikipedia</a> · ` : ""}${c.wikidata ? `<a href="https://www.wikidata.org/wiki/${esc(c.wikidata)}" target="_blank" rel="noopener">Wikidata ${esc(c.wikidata)}</a>` : ""}
    ${srcLine(["cities", "census2011_district", "nfhs5_district"])}</section>`;
  return h;
}

async function statePanel(id) {
  const s = app.world.states.find((x) => x.id === id);
  const so = app.stateById.get(id);
  const r = await tableRow("state", id);
  let h = header(s.name, `${esc(s.type === "UT" ? "Union Territory" : "State")} · ${fmt(s.area_km2)} km² on the grid`);
  h += yieldsBlock(so?.yields, "State yields");
  if (so?.rank) h += `<section><div class="src">${Object.entries(so.rank).map(([y, k]) => `${app.nation.yields_meta.find((m) => m.id === y)?.emoji} #${k}`).join(" · ")} — rank among states and UTs with data</div></section>`;
  if (r) {
    const g = (k) => r[k];
    h += `<section><h3>People</h3>${kv([["Population (2011)", g("census2011_state.population")], ["Literates per 100 people (2011)", g("census2011_state.literacy_rate")], ["Sex ratio (2011)", g("census2011_state.sex_ratio"), "F per 1,000 M"], ["Urban households (2011)", g("census2011_state.urban_household_share"), "%"], ["Birth rate (SRS 2024)", g("srs_state.birth_rate"), "per 1,000"], ["Life expectancy (2020–24)", g("srs_state.life_exp"), "years"], ["Infant mortality (SRS 2024)", g("srs_state.imr"), "per 1,000 births"]])}</section>`;
    h += `<section><h3>Economy</h3>${kv([["GSDP 2023-24", g("gsdp_state.gsdp_current"), "₹ crore"], ["Income per person (NSDP)", g("gsdp_state.pc_nsdp_current"), "₹"], ["Manufacturing share", g("gsva_sector_state.share_mfg"), "% GSVA"], ["Agriculture share", g("gsva_sector_state.share_agri"), "% GSVA"], ["Unemployment (PLFS 2025)", g("plfs_state.ur"), "%"], ["Women at work (PLFS 2025)", g("plfs_state.wpr_female"), "%"], ["Factories (ASI 2023-24)", g("asi_state.factories")], ["Exports 2024-25", g("exports_state.exports_usd_mn"), "US$ mn"]])}</section>`;
    h += `<section><h3>Land & resources</h3>${kv([["Forest cover (ISFR 2023)", g("forest_state.forest_cover_pct"), "%"], ["Foodgrains 2023-24", g("crop_state.foodgrains_prod_mt"), "Mt"], ["Irrigated share of sown area", g("crop_state.irrigation_share_pct"), "%"], ["Fish 2023-24", g("fisheries_state.total_lakh_t"), "lakh t"], ["Milk 2023-24", g("livestock_state.milk_kt"), "thousand t"], ["Installed solar", g("renewable_potential_state.solar_mw"), "MW"], ["Wind potential (150 m)", g("renewable_potential_state.wind_potential_150m_gw"), "GW"]])}</section>`;
    h += `<section><h3>Health (NFHS-5)</h3>${kv([["Child stunting", g("nfhs5_state.stunting"), "%"], ["Institutional births", g("nfhs5_state.institutional_births"), "%"], ["Full immunisation", g("nfhs5_state.full_immunisation"), "%"], ["Total fertility rate", g("nfhs5_state.tfr")]])}</section>`;
  }
  const cs = app.cities.filter((c) => c.state === id && c.population).slice(0, 8);
  if (cs.length) h += `<section><h3>Cities</h3><ul class="list-plain">${cs.map((c) => `<li><button class="linkish" data-go="city:${c.id}">${esc(c.name)}</button><span class="faint" style="margin-left:auto">${fmt(c.population)}</span></li>`).join("")}</ul></section>`;
  h += `<section><button class="btn" data-go="explore:${encodeURIComponent(JSON.stringify({ table: "state", sel: id }))}">Compare in Explorer</button>${srcLine(["gsdp_state", "census2011_state", "nfhs5_state", "srs_state", "plfs_state"])}</section>`;
  return h;
}

async function districtPanel(key, res) {
  const w = app.world;
  const list = res === "district2011" ? w.districts11 : w.districts;
  const d = list.find((x) => x.key === key);
  const s = w.states.find((x) => x.id === d?.state);
  const r = await tableRow(res, key);
  let h = header(d?.name || key, `District (${res === "district2011" ? "Census 2011 boundary" : "2019–21 boundary"}) · <button class="linkish" data-go="state:${d?.state}">${esc(s?.name)}</button>`);
  if (!r) return h + `<section class="muted">No data rows for this district in the ${res === "district2011" ? "Census 2011" : "NFHS-5"} tables. It may have been created after the survey.</section>`;
  const fields = r._t.fields;
  const groups = new Map();
  for (const f in fields) { if (r[f] == null) continue; const ds = fields[f].ds; if (!groups.has(ds)) groups.set(ds, []); groups.get(ds).push(f); }
  const pick = { census2011_district: ["population", "literacy_rate", "literacy_rate_female", "sex_ratio", "urban_household_share", "pct_graduate", "worker_participation", "female_worker_participation", "pct_cultivators", "pct_agri_labourers", "pct_household_industry", "pct_other_workers", "pct_st", "pct_sc", "pct_hh_electric_lighting", "pct_hh_lpg_png", "pct_hh_internet", "pct_hh_mobile_phone", "pct_hh_car"],
    nfhs5_district: null, district_gdp: null };
  for (const [ds, fs] of groups) {
    const want = pick[ds] ? pick[ds].map((f) => `${ds}.${f}`).filter((f) => fs.includes(f)) : fs;
    h += `<section><h3>${esc(ds.replace(/_/g, " "))}</h3>${kv(want.map((f) => [fields[f].name, r[f], fields[f].unit]))}${srcLine([ds])}</section>`;
  }
  h += `<section><button class="btn" data-go="explore:${encodeURIComponent(JSON.stringify({ table: res, sel: key }))}">Compare in Explorer</button></section>`;
  return h;
}

async function cellPanel(i) {
  const w = app.world, g = app.grid;
  const d = w.districts[w.district[i]], s = w.states[w.state[i]];
  const d11 = w.districts11[w.district11[i]];
  const [lon, lat] = (await import("./geo.js")).unproject(g.cx[i], g.cy[i]);
  const cov = w.tables.cover[w.cover[i]], rel = w.tables.relief[w.relief[i]];
  const k = app.landPos.get(i);
  let h = header(d?.name || "Hex", `<button class="linkish" data-go="state:${s?.id}">${esc(s?.name)}</button> · hex c${i % g.cols}r${(i / g.cols) | 0} · ${lat.toFixed(2)}°N ${lon.toFixed(2)}°E`);
  if (w.disputed[i] >= 0) h += `<section><b>Claimed by India, administered by ${esc(w.disputedNames[w.disputed[i]])}.</b><div class="muted">The map follows India's official boundary (Survey of India). Indian statistics do not cover this area, so every value is missing.</div></section>`;
  const yid = app.hexyields?.yields || [];
  if (k != null && yid.length) {
    h += `<section><h3>Tile yields</h3><div class="yield-row">${yid.map((y) => { const m = app.nation.yields_meta.find((x) => x.id === y); const p = app.hexyields.pips[y][k]; return `<div class="yield-cell" title="${esc(m?.note)}"><div class="yv" style="color:${YC[y]}">${m?.emoji} ${p}</div><div class="yl">${esc(m?.name)}</div></div>`; }).join("")}</div><div class="src">Pips 0–4 rank this hex among all Indian land hexes (quintiles). See Almanac → Yields.</div></section>`;
  }
  h += `<section><h3>Terrain</h3>${kv([["Cover", cov?.name], ["Relief", rel?.name], ["Mean elevation", w.elev[i], "m"]])}<div class="src">${esc(cov?.rule || "")} ${esc(rel?.rule || "")}</div></section>`;
  const lensRows = [];
  const lens = await Promise.all(["population", "rainfall", "heat", "forest", "lights", "flood"].map((id) => app.lensById.has(id) ? load(`lens/${id}`).then((x) => [app.lensById.get(id), x]) : null));
  for (const x of lens) if (x && k != null) lensRows.push([x[0].name, x[1].values[k], x[0].unit]);
  h += `<section><h3>Hex values</h3>${kv(lensRows)}</section>`;
  h += `<section><button class="btn" data-go="district:${esc(d?.key)}">District (2019–21)</button> <button class="btn" data-go="district11:${esc(d11?.key)}">District (Census 2011)</button> <button class="btn" data-go="state:${s?.id}">State</button></section>`;
  return h;
}

function pointPanel(p) {
  const t = app.points.types.find((x) => x.id === p.t);
  let h = header(p.n || p.name, `${t ? t.emoji + " " + esc(t.name) : "🏛️ Wonder"}${p.c ? " · " + esc(p.c) : ""}`);
  if (p.t === "wonder") {
    const rule = app.wonders.rules.find((r) => r.id === p.rule);
    h += `<section>${kv([["Category", p.category], ["Inscribed", p.year], ["NIRF rank", p.rank], ["Capacity", p.capacity_mw, "MW"]].filter((r) => r[1] != null))}<div class="src">Why this is a wonder: ${esc(rule?.text)}</div>${p.url ? `<a href="${esc(p.url)}" target="_blank" rel="noopener">UNESCO page</a>` : ""}</section>`;
    return h;
  }
  h += `<section>${kv([[t?.unit ? "Value" : "", p.v, t?.unit], ["IATA", p.iata], ["Commissioned", p.commissioning_year], ["NIRF rank", p.nirf_rank], ["State", app.world.states.find((s) => s.id === p.s)?.name]].filter((r) => r[1] != null && r[0]))}
    ${p.wikidata ? `<a href="https://www.wikidata.org/wiki/${esc(p.wikidata)}" target="_blank" rel="noopener">Wikidata ${esc(p.wikidata)}</a>` : ""}${srcLine([t?.source || ""])}</section>`;
  return h;
}

// ---------------- search
function bindSearch() {
  const input = $("#search-input"), box = $("#search-results");
  let items = null, active = 0, results = [];
  const build = () => {
    const w = app.world;
    items = [
      ...app.cities.map((c) => ({ label: c.name, sub: w.states.find((s) => s.id === c.state)?.name, kind: "city", go: { type: "city", id: c.id }, rank: 3 })),
      ...w.states.map((s) => ({ label: s.name, sub: s.type, kind: "state", go: { type: "state", id: s.id }, rank: 4 })),
      ...w.districts.map((d) => ({ label: d.name, sub: w.states.find((s) => s.id === d.state)?.name, kind: "district", go: { type: "district", key: d.key }, rank: 2 })),
    ];
  };
  const render = () => {
    box.hidden = !results.length;
    box.innerHTML = results.map((r, k) => `<button class="${k === active ? "active" : ""}" data-k="${k}">${esc(r.label)} <span class="faint">${esc(r.sub || "")}</span><span class="kind">${r.kind}</span></button>`).join("");
  };
  input.addEventListener("input", () => {
    if (!items) build();
    const q = input.value.trim().toLowerCase(); active = 0;
    if (!q) { results = []; return render(); }
    results = items.map((it) => { const l = it.label.toLowerCase(); const sc = l === q ? 100 : l.startsWith(q) ? 50 : l.includes(q) ? 20 : 0; return [sc + it.rank, it]; })
      .filter((x) => x[0] > 4).sort((a, b) => b[0] - a[0]).slice(0, 12).map((x) => x[1]);
    render();
  });
  input.addEventListener("keydown", (e) => {
    if (e.key === "ArrowDown") { active = Math.min(results.length - 1, active + 1); render(); e.preventDefault(); }
    else if (e.key === "ArrowUp") { active = Math.max(0, active - 1); render(); e.preventDefault(); }
    else if (e.key === "Enter" && results[active]) go(results[active]);
  });
  box.addEventListener("click", (e) => { const b = e.target.closest("button"); if (b) go(results[+b.dataset.k]); });
  const go = (r) => { input.value = ""; results = []; render(); input.blur(); if (app.mode === "history") setMode("present"); select(r.go, { fly: true }); };
  input.addEventListener("blur", () => setTimeout(() => { box.hidden = true; }, 150));
}

// ---------------- modes and modals
export async function setMode(mode, era) {
  app.mode = mode;
  document.querySelectorAll(".mode-switch button").forEach((b) => b.setAttribute("aria-selected", String(b.dataset.mode === mode)));
  const { History } = await import("./history.js");
  if (!app.history) app.history = new History(app);
  if (mode === "history") { $("#lens-area").hidden = true; await app.history.enter(era); }
  else { $("#lens-area").hidden = false; app.history.exit(); }
  app.view.dirty = true;
}

export async function openModal(kind, opts = {}) {
  const m = $("#modal"); m.hidden = false;
  const body = $("#modal-body"); body.innerHTML = `<div class="mhead"><h2>Loading…</h2></div>`;
  if (kind === "explorer") (await import("./explorer.js")).render(body, app, opts);
  else if (kind === "advisors") (await import("./pedia.js")).advisors(body, app);
  else (await import("./pedia.js")).almanac(body, app, opts);
}
export function closeModal() { $("#modal").hidden = true; }
