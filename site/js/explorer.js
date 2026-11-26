// Explorer drawer: any table, any metric; sortable table, scatter, distribution, ranking.
// Selecting a row or a dot highlights the region on the map, which stays visible.
import { fmt, esc } from "./geo.js";
import { select, load, highlightCells, flyToCells } from "./main.js";
import { rampColor } from "./map.js";

const QUESTIONS = [
  { q: "Which districts have the highest share of graduates?", table: "district2011", x: "census2011_district.pct_graduate", y: "census2011_district.pct_other_workers", sort: "x" },
  { q: "How does literacy relate to household assets?", table: "district2011", x: "census2011_district.literacy_rate", y: "census2011_district.pct_hh_car", sort: "x" },
  { q: "Where do most workers farm their own land?", table: "district2011", x: "census2011_district.pct_cultivators", y: "census2011_district.literacy_rate", sort: "x" },
  { q: "Does women's schooling go with less stunting?", table: "district2020", x: "nfhs5_district.women_10yr_school", y: "nfhs5_district.stunting", sort: "y" },
  { q: "Which districts have the lowest health-insurance coverage?", table: "district2020", x: "nfhs5_district.health_insurance", y: "nfhs5_district.institutional_births", sort: "x", asc: true },
  { q: "Which states depend most on manufacturing?", table: "state", x: "gsva_sector_state.share_mfg", y: "gsdp_state.pc_nsdp_current", sort: "x" },
  { q: "Is income per person linked to life expectancy?", table: "state", x: "gsdp_state.pc_nsdp_current", y: "srs_state.life_exp", sort: "x" },
  { q: "Which states grow the most food per hectare?", table: "state", x: "crop_state.foodgrains_yield_all_kgha", y: "crop_state.irrigation_share_pct", sort: "x" },
  { q: "Where is unemployment highest?", table: "state", x: "plfs_state.ur", y: "plfs_state.wpr_female", sort: "x" },
  { q: "Which states lost or gained forest since 2013?", table: "state", x: "forest_state.forest_cover_change_km2", y: "forest_state.forest_cover_pct", sort: "x", asc: true },
  { q: "Which districts have more graduates than their wealth predicts?", table: "district2011", x: "strengths_district2011.graduates_expected", y: "census2011_district.pct_graduate", sort: "x" },
  { q: "Where is child stunting lower than living standards predict?", table: "district2020", x: "strengths_district2020.child_growth_expected", y: "nfhs5_district.stunting", sort: "x" },
  { q: "Which states export more than their economy size predicts?", table: "state", x: "strengths_state.exports_expected", y: "exports_state.exports_usd_mn", sort: "y" },
  { q: "Which district economies are largest in Maharashtra?", table: "district2020", x: "district_gdp.gddp_current", y: "district_gdp.per_capita_gddp", sort: "x" },
];

let st = { table: "district2011", x: null, y: null, sort: "x", asc: false, filter: "", stateF: "", sel: null };
let T = null, app = null;

export async function render(_modalBody, a, opts = {}) {
  app = a;
  document.getElementById("modal").hidden = true;
  let el = document.getElementById("explorer");
  if (!el) {
    el = document.createElement("aside"); el.id = "explorer"; el.className = "panel explorer";
    document.body.appendChild(el);
  }
  el.hidden = false;
  document.getElementById("strengths")?.setAttribute("hidden", "");
  if (opts.table) { st.table = opts.table; st.x = opts.x || null; st.y = opts.y || null; }
  if (opts.sel) st.sel = opts.sel;
  await setTable(st.table, !!opts.table);
}

async function setTable(id, keepSel) {
  T = await load(`table_${id}`);
  st.table = id; if (!keepSel) st.sel = null;
  const numeric = Object.keys(T.fields).filter((f) => T.cols[f].some((v) => typeof v === "number"));
  const DEF = { district2011: ["census2011_district.literacy_rate_7plus", "census2011_district.pct_graduate"], district2020: ["nfhs5_district.women_10yr_school", "nfhs5_district.stunting"], state: ["gsdp_state.pc_nsdp_current", "srs_state.life_exp"], city: ["cities.ua_population_2011", "cities.city_population_2011"] }[id] || [];
  if (!numeric.includes(st.x)) st.x = numeric.includes(DEF[0]) ? DEF[0] : numeric[0];
  if (!numeric.includes(st.y)) st.y = numeric.includes(DEF[1]) ? DEF[1] : numeric[1] || numeric[0];
  draw();
}

function rows() {
  const { base, cols } = T;
  const out = [];
  for (let k = 0; k < base.key.length; k++) {
    const r = { k, key: base.key[k], name: base.name[k], state: base.state[k], x: cols[st.x]?.[k], y: cols[st.y]?.[k] };
    if (st.stateF && r.state !== st.stateF) continue;
    if (st.filter && !r.name.toLowerCase().includes(st.filter)) continue;
    out.push(r);
  }
  const key = st.sort === "name" ? "name" : st.sort;
  out.sort((a, b) => {
    const va = a[key], vb = b[key];
    if (va == null && vb == null) return 0; if (va == null) return 1; if (vb == null) return -1;
    return (st.asc ? 1 : -1) * (typeof va === "string" ? va.localeCompare(vb) : va - vb) * (key === "name" ? -1 : 1);
  });
  return out;
}

const fname = (f) => T.fields[f] ? `${T.fields[f].name}` : f;
const funit = (f) => T.fields[f]?.unit || "";

function fieldOptions(sel) {
  const byDs = new Map();
  for (const f in T.fields) { const ds = T.fields[f].ds; if (!byDs.has(ds)) byDs.set(ds, []); byDs.get(ds).push(f); }
  return [...byDs].map(([ds, fs]) => `<optgroup label="${esc(ds)}">${fs.map((f) => `<option value="${esc(f)}" ${f === sel ? "selected" : ""}>${esc(T.fields[f].name)}${T.fields[f].unit ? " (" + esc(T.fields[f].unit) + ")" : ""}</option>`).join("")}</optgroup>`).join("");
}

function draw() {
  const el = document.getElementById("explorer");
  const rs = rows();
  const states = app.world.states;
  const tables = app.lensIdx.tables;
  const qs = QUESTIONS.filter((q) => tables.some((t) => t.id === q.table));
  el.innerHTML = `
    <header class="ex-head"><h2>Explorer</h2><span class="muted">${esc(T.name)} · ${T.base.key.length} rows · ${Object.keys(T.fields).length} metrics from ${T.datasets.length} datasets</span>
      <button class="close icon-btn" aria-label="Close Explorer">✕</button></header>
    <div class="ex-controls">
      <label>Table <select id="ex-table">${tables.map((t) => `<option value="${t.id}" ${t.id === st.table ? "selected" : ""}>${esc(t.name)}</option>`).join("")}</select></label>
      <label>Ask <select id="ex-q"><option value="">A question…</option>${qs.map((q, k) => `<option value="${k}">${esc(q.q)}</option>`).join("")}</select></label>
    </div>
    <div class="ex-controls">
      <label>X <select id="ex-x">${fieldOptions(st.x)}</select></label>
      <label>Y <select id="ex-y">${fieldOptions(st.y)}</select></label>
      <label>State <select id="ex-st"><option value="">All</option>${states.map((s) => `<option value="${s.id}" ${s.id === st.stateF ? "selected" : ""}>${esc(s.name)}</option>`).join("")}</select></label>
      <input id="ex-f" type="search" placeholder="Filter by name" value="${esc(st.filter)}">
      ${st.table !== "city" ? `<button class="btn" id="ex-lens" title="Colour the map by X">Map X</button>` : ""}
    </div>
    <div class="ex-stats" id="ex-stats"></div>
    <div class="ex-grid">
      <div class="ex-table">${tableHtml(rs)}</div>
      <div class="ex-charts"><div id="ex-scatter"></div><div id="ex-hist"></div><div class="src" id="ex-src"></div></div>
    </div>`;
  el.querySelector(".close").onclick = () => { el.hidden = true; };
  el.querySelector("#ex-table").onchange = (e) => { st.stateF = ""; setTable(e.target.value); };
  el.querySelector("#ex-x").onchange = (e) => { st.x = e.target.value; draw(); };
  el.querySelector("#ex-y").onchange = (e) => { st.y = e.target.value; draw(); };
  el.querySelector("#ex-st").onchange = (e) => { st.stateF = e.target.value; draw(); };
  el.querySelector("#ex-f").oninput = (e) => { st.filter = e.target.value.toLowerCase(); const p = e.target.selectionStart; draw(); const f = document.getElementById("ex-f"); f.focus(); f.setSelectionRange(p, p); };
  el.querySelector("#ex-q").onchange = async (e) => {
    const q = qs[+e.target.value]; if (!q) return;
    st.sort = q.sort; st.asc = !!q.asc; st.stateF = ""; st.filter = "";
    if (q.table !== st.table) { T = await load(`table_${q.table}`); st.table = q.table; }
    st.x = q.x in T.fields ? q.x : st.x; st.y = q.y in T.fields ? q.y : st.y; draw();
  };
  el.querySelector("#ex-lens")?.addEventListener("click", () => mapMetric(st.x));
  el.querySelectorAll("th[data-s]").forEach((th) => th.onclick = () => { const s = th.dataset.s; st.asc = st.sort === s ? !st.asc : s === "name"; st.sort = s; draw(); });
  el.querySelectorAll("tr[data-k]").forEach((tr) => tr.onclick = () => pick(tr.dataset.key));
  scatter(rs); hist(rs); statsLine(rs);
  const dsx = T.fields[st.x]?.ds, dsy = T.fields[st.y]?.ds;
  document.getElementById("ex-src").innerHTML = `X: ${esc(T.fields[st.x]?.description || fname(st.x))} <i>[${esc(dsx)}]</i><br>Y: ${esc(T.fields[st.y]?.description || fname(st.y))} <i>[${esc(dsy)}]</i>`;
}

function tableHtml(rs) {
  const arrow = (s) => (st.sort === s ? (st.asc ? " ▲" : " ▼") : "");
  const sname = (id) => app.world.states.find((s) => s.id === id)?.name || id || "";
  const rank = new Map(rs.filter((r) => r.x != null).sort((a, b) => b.x - a.x).map((r, i) => [r.key, i + 1]));
  return `<table class="data"><thead><tr><th class="l" data-s="name">Name${arrow("name")}</th><th class="l">State</th><th data-s="x" title="${esc(fname(st.x))}">${esc(trunc(fname(st.x)))}${arrow("x")}</th><th data-s="y" title="${esc(fname(st.y))}">${esc(trunc(fname(st.y)))}${arrow("y")}</th><th>Rank X</th></tr></thead><tbody>` +
    rs.map((r) => `<tr data-k="${r.k}" data-key="${esc(r.key)}" class="${r.key === st.sel ? "sel" : ""}"><td>${esc(r.name)}</td><td class="l muted">${esc(st.table === "state" ? "" : sname(r.state))}</td><td class="${r.x == null ? "null" : ""}">${r.x == null ? "—" : fmt(r.x)}</td><td class="${r.y == null ? "null" : ""}">${r.y == null ? "—" : fmt(r.y)}</td><td class="faint">${rank.get(r.key) || ""}</td></tr>`).join("") + "</tbody></table>";
}
const trunc = (s) => (s.length > 26 ? s.slice(0, 25) + "…" : s);

function pearson(rs) {
  const p = rs.filter((r) => r.x != null && r.y != null);
  if (p.length < 3) return null;
  const mx = p.reduce((s, r) => s + r.x, 0) / p.length, my = p.reduce((s, r) => s + r.y, 0) / p.length;
  let sxy = 0, sxx = 0, syy = 0; for (const r of p) { sxy += (r.x - mx) * (r.y - my); sxx += (r.x - mx) ** 2; syy += (r.y - my) ** 2; }
  return { r: sxy / Math.sqrt(sxx * syy), n: p.length };
}

function statsLine(rs) {
  const xs = rs.map((r) => r.x).filter((v) => v != null).sort((a, b) => a - b);
  const c = pearson(rs);
  const q = (p) => xs[Math.min(xs.length - 1, Math.floor(p * xs.length))];
  document.getElementById("ex-stats").innerHTML = xs.length ? `<span class="stat">n <b>${xs.length}</b></span><span class="stat">missing <b>${rs.length - xs.length}</b></span><span class="stat">median X <b>${fmt(q(0.5))}</b></span><span class="stat">range <b>${fmt(xs[0])} – ${fmt(xs[xs.length - 1])}</b></span>` +
    (c ? `<span class="stat">Pearson r(X,Y) <b>${c.r.toFixed(2)}</b> <span class="faint">n=${c.n}; correlation is not causation</span></span>` : "") : `<span class="muted">No values for X in this selection.</span>`;
}

function scatter(rs) {
  const p = rs.filter((r) => r.x != null && r.y != null);
  const W = 460, H = 300, m = { l: 48, r: 10, t: 10, b: 34 };
  const el = document.getElementById("ex-scatter");
  if (p.length < 2) { el.innerHTML = `<div class="muted" style="padding:20px">Not enough rows with both X and Y.</div>`; return; }
  const ext = (k) => { let a = Infinity, b = -Infinity; for (const r of p) { a = Math.min(a, r[k]); b = Math.max(b, r[k]); } return a === b ? [a - 1, b + 1] : [a, b]; };
  const [x0, x1] = ext("x"), [y0, y1] = ext("y");
  const sx = (v) => m.l + ((v - x0) / (x1 - x0)) * (W - m.l - m.r), sy = (v) => H - m.b - ((v - y0) / (y1 - y0)) * (H - m.t - m.b);
  const ticks = (a, b) => [0, 0.25, 0.5, 0.75, 1].map((t) => a + t * (b - a));
  const states = [...new Set(p.map((r) => r.state))];
  const col = (s) => { const c = rampColor(["#5ab0f0", "#8bc34a", "#f2c94c", "#e0884a", "#c58af0", "#ef6f7a", "#9fb4c8"], (states.indexOf(s) % 7) / 6); return `rgb(${c.map((v) => v | 0)})`; };
  el.innerHTML = `<svg class="chart" viewBox="0 0 ${W} ${H}">
    <g class="axis">${ticks(x0, x1).map((v) => `<line x1="${sx(v)}" x2="${sx(v)}" y1="${m.t}" y2="${H - m.b}" stroke-opacity=".3"/><text x="${sx(v)}" y="${H - m.b + 13}" text-anchor="middle">${fmt(v)}</text>`).join("")}
    ${ticks(y0, y1).map((v) => `<line x1="${m.l}" x2="${W - m.r}" y1="${sy(v)}" y2="${sy(v)}" stroke-opacity=".3"/><text x="${m.l - 4}" y="${sy(v) + 3}" text-anchor="end">${fmt(v)}</text>`).join("")}</g>
    <text x="${(W + m.l) / 2}" y="${H - 4}" text-anchor="middle">${esc(trunc(fname(st.x)))} (${esc(funit(st.x))})</text>
    <text transform="translate(11 ${(H - m.b) / 2}) rotate(-90)" text-anchor="middle">${esc(trunc(fname(st.y)))}</text>
    ${p.map((r) => `<circle class="dot ${r.key === st.sel ? "sel" : ""}" data-key="${esc(r.key)}" cx="${sx(r.x).toFixed(1)}" cy="${sy(r.y).toFixed(1)}" r="${r.key === st.sel ? 5.5 : 3.4}" fill="${col(r.state)}" fill-opacity=".78"><title>${esc(r.name)}: ${fmt(r.x)} / ${fmt(r.y)}</title></circle>`).join("")}
  </svg>`;
  el.querySelectorAll(".dot").forEach((d) => d.addEventListener("click", () => pick(d.dataset.key)));
}

function hist(rs) {
  const xs = rs.map((r) => r.x).filter((v) => v != null);
  const el = document.getElementById("ex-hist");
  if (xs.length < 3) { el.innerHTML = ""; return; }
  const a = Math.min(...xs), b = Math.max(...xs), N = 24, bins = new Array(N).fill(0);
  for (const v of xs) bins[Math.min(N - 1, Math.floor(((v - a) / (b - a || 1)) * N))]++;
  const mx = Math.max(...bins), W = 460, H = 110;
  const selV = rs.find((r) => r.key === st.sel)?.x;
  el.innerHTML = `<div class="muted" style="margin-top:10px">Distribution of X</div><svg class="chart" viewBox="0 0 ${W} ${H}">
    ${bins.map((c, k) => `<rect x="${10 + (k * (W - 20)) / N}" y="${H - 18 - (c / mx) * (H - 26)}" width="${(W - 20) / N - 1}" height="${(c / mx) * (H - 26)}" fill="#c9a45c" fill-opacity=".7"><title>${fmt(a + (k * (b - a)) / N)} – ${fmt(a + ((k + 1) * (b - a)) / N)}: ${c}</title></rect>`).join("")}
    ${selV != null ? `<line x1="${10 + ((selV - a) / (b - a || 1)) * (W - 20)}" x2="${10 + ((selV - a) / (b - a || 1)) * (W - 20)}" y1="4" y2="${H - 18}" stroke="#ffe39a" stroke-width="2"/>` : ""}
    <text x="10" y="${H - 4}">${fmt(a)}</text><text x="${W - 10}" y="${H - 4}" text-anchor="end">${fmt(b)}</text></svg>`;
}

function pick(key) {
  st.sel = key;
  document.querySelectorAll("#explorer tr.sel").forEach((t) => t.classList.remove("sel"));
  document.querySelectorAll(`#explorer tr[data-key="${CSS.escape(key)}"]`).forEach((t) => t.classList.add("sel"));
  const t = st.table;
  const type = t === "district2011" ? "district11" : t === "district2020" ? "district" : t;
  if (type === "city") select({ type: "city", id: key }, { fly: true });
  else if (type === "state") select({ type: "state", id: key }, { fly: true });
  else select({ type, key }, { fly: true });
  scatter(rows()); hist(rows());
}

// Custom lens from any table column: each hex takes its majority district's (or state's) value.
async function mapMetric(f) {
  const w = app.world; const fld = T.fields[f];
  const val = new Map(T.base.key.map((k, i) => [k, T.cols[f][i]]));
  const list = st.table === "district2011" ? w.districts11 : st.table === "district2020" ? w.districts : null;
  const owner = st.table === "district2011" ? w.district11 : st.table === "district2020" ? w.district : w.state;
  const keys = list ? list.map((d) => d.key) : w.states.map((s) => s.id);
  const areas = list ? list.map((d) => d.area_km2) : null;
  const perArea = fld.type === "count" && list;
  const values = w.land.map((i) => { const o = owner[i]; if (o < 0 || w.disputed[i] >= 0) return null; const v = val.get(keys[o]); return v == null ? null : perArea ? v / areas[o] : v; });
  const xs = values.filter((v) => v != null).sort((a, b) => a - b);
  if (!xs.length) return;
  const q = (p) => xs[Math.floor(p * (xs.length - 1))];
  const meta = { id: "custom", name: fld.name, emoji: "🧭", unit: perArea ? `${fld.unit} per km²` : fld.unit, kind: app.world && "official", year: "", ramp: ["#101c3a", "#1d3f7a", "#2f6fb0", "#4fa3d8", "#e9d27a", "#fff3a8"],
    scale: perArea && q(0.02) > 0 ? "log" : "linear", stats: { p2: q(0.02), p98: q(0.98) }, higher_is: fld.higher_is,
    description: `Custom lens from the Explorer: ${fld.name} [${fld.ds}]. Each hex takes the value of the ${st.table === "state" ? "state" : "district that covers most of it"}${perArea ? ", divided by district area" : ""}.`, source: fld.ds, coverage: xs.length / w.land.length };
  const { setCustomLens } = await import("./main.js");
  setCustomLens(meta, values);
}
