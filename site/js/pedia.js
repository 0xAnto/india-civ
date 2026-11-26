// Advisors and the Almanac (methodology, sources, rules).
import { fmt, esc } from "./geo.js";
import { load, setLens, highlightCells, flyToCells, select } from "./main.js";
import { closeModal, setMode, openModal } from "./ui.js";

export async function advisors(body, app) {
  const adv = await load("advisors");
  body.innerHTML = `<div class="mhead"><h2>Advisors</h2><div class="sub">Each observation is computed from the data by <code>pipeline/advisors.py</code>. The evidence line names the dataset, the field and the year. "Show" highlights the places on the map.</div></div>
    <div class="mmain"><div class="advisors">${adv.map((a, ai) => `<div class="advisor"><header><div class="face">${a.face}</div><div><h3>${esc(a.name)}</h3><div class="role">${esc(a.role)}</div></div></header>
      ${a.insights.map((ins, k) => `<div class="insight">${esc(ins.text)}<div class="ev">${ins.evidence.map((e) => `${esc(e.dataset)}${e.field ? "." + esc(e.field) : ""}${e.year ? " · " + esc(e.year) : ""}${e.kind ? ` · <span class="kind-badge kind-${esc(e.kind)}">${esc(e.kind)}</span>` : ""}`).join(" | ")}
        <button class="linkish" data-a="${ai}" data-k="${k}">Show</button> <button class="linkish" data-src="${esc(ins.evidence[0]?.dataset)}">Source</button></div></div>`).join("")}</div>`).join("")}</div></div>`;
  body.querySelectorAll("[data-src]").forEach((b) => b.onclick = () => openModal("almanac", { source: b.dataset.src }));
  body.querySelectorAll("[data-a]").forEach((b) => b.onclick = async () => {
    const ins = adv[+b.dataset.a].insights[+b.dataset.k]; const e = ins.evidence[0];
    closeModal();
    if (e.mode === "history") return setMode("history", e.era);
    if (e.lens) { await setLens(e.lens); if (e.cells?.length) { highlightCells(e.cells); flyToCells(e.cells); } return; }
    const w = app.world; const keys = new Set((e.select || []).map(String));
    let cells = [];
    if (e.table === "state") {
      const idx = new Set(w.states.map((s, i) => (keys.has(s.id) ? i : -1)).filter((i) => i >= 0));
      cells = w.land.filter((i) => idx.has(w.state[i]) && w.disputed[i] < 0);
    } else if (e.table === "district2011" || e.table === "district2020") {
      const list = e.table === "district2011" ? w.districts11 : w.districts, own = e.table === "district2011" ? w.district11 : w.district;
      const idx = new Set(list.map((d, i) => (keys.has(d.key) ? i : -1)).filter((i) => i >= 0));
      cells = w.land.filter((i) => idx.has(own[i]));
    } else if (e.table === "point") {
      const pts = app.points.items.filter((p) => keys.has(String(p.k)));
      cells = pts.map((p) => app.grid.cellAt(p.x, p.y));
    }
    if (cells.length) { highlightCells(cells, "rgba(255,215,120,.28)"); flyToCells(cells); }
  });
}

const PAGES = [
  ["about", "How to read the map"], ["yields", "Yields"], ["terrain", "Terrain rules"], ["lenses", "Lenses"],
  ["method", "Methodology"], ["strengths", "Hidden strengths"], ["change", "Change over time"], ["history", "History layer"], ["sources", "Sources"], ["gaps", "Data gaps"], ["keys", "Keys"],
];

export async function almanac(body, app, opts = {}) {
  const sources = await load("sources");
  body.innerHTML = `<div class="mhead"><h2>Almanac</h2><div class="sub">What every number means and where it comes from</div></div>
    <div class="mbody"><nav class="mnav">${PAGES.map(([id, n]) => `<button data-p="${id}">${esc(n)}</button>`).join("")}<h4>Sources</h4>${sources.map((s) => `<button data-p="src:${esc(s.id)}">${esc(s.id)}</button>`).join("")}</nav><article class="mmain" id="pedia-main"></article></div>`;
  const show = (p) => {
    body.querySelectorAll(".mnav button").forEach((b) => b.setAttribute("aria-current", String(b.dataset.p === p)));
    const el = body.querySelector("#pedia-main"); el.scrollTop = 0;
    el.innerHTML = page(p, app, sources);
    el.querySelectorAll("[data-p]").forEach((b) => b.onclick = () => show(b.dataset.p));
    el.querySelectorAll("[data-lens]").forEach((b) => b.onclick = () => { closeModal(); setLens(b.dataset.lens); });
  };
  body.querySelectorAll(".mnav button").forEach((b) => b.onclick = () => show(b.dataset.p));
  show(opts.source ? `src:${opts.source}` : "about");
}

function srcCard(s) {
  const kv = [["Organisation", s.source_org], ["Reference year", s.reference_year], ["Published", s.published], ["Resolution", s.resolution], ["Kind", s.kind], ["Licence", s.license], ["Updates", s.update_frequency], ["Accessed", s.accessed], ["Rows / fields", s.rows != null ? `${s.rows} / ${s.fields}` : null], ["Redistributed via", s.redistributed_via]];
  return `<h3>${esc(s.name || s.id)}</h3><div class="pedia-src"><div class="kv">${kv.filter((r) => r[1]).map(([k, v]) => `<span class="k">${esc(k)}</span><span class="v" style="text-align:left">${k === "Kind" ? `<span class="kind-badge kind-${esc(v)}">${esc(v)}</span>` : esc(v)}</span>`).join("")}</div>
    <p class="m">${s.url ? `URL: <a href="${esc(s.url)}" target="_blank" rel="noopener">${esc(s.url)}</a>` : ""}${s.landing_url ? `<br>About: <a href="${esc(s.landing_url)}" target="_blank" rel="noopener">${esc(s.landing_url)}</a>` : ""}</p>
    ${s.method ? `<h4>Method</h4><p>${esc(s.method)}</p>` : ""}${s.limitations ? `<h4>Limitations</h4><p>${esc(s.limitations)}</p>` : ""}
    ${s.coverage_note ? `<h4>Coverage note</h4><pre style="white-space:pre-wrap;font-size:11px;color:var(--ink-dim)">${esc(s.coverage_note)}</pre>` : ""}</div>`;
}

function page(p, app, sources) {
  if (p.startsWith("src:")) {
    const s = sources.find((x) => x.id === p.slice(4));
    return s ? srcCard(s) : `<p>No source record for “${esc(p.slice(4))}”. Hex-model values (“mechanics”) are explained on the <button class="linkish" data-p="yields">Yields</button> page.</p>`;
  }
  const w = app.world;
  switch (p) {
    case "about": return `<h3>India as a strategy map</h3>
      <p>Every hex is 20 km across (346 km²). There are ${w.land.length.toLocaleString()} Indian land hexes on a Lambert conformal conic grid. Each hex has a stable id <code>c&lt;col&gt;r&lt;row&gt;</code> and real coordinates.</p>
      <p><b>Present</b> mode shows today's data. <b>History</b> mode is a separate timeline of eras, capitals, sites and approximate empire extents; it never mixes with present-day statistics.</p>
      <p>Click a hex, a city banner, a resource icon or a wonder to inspect it. Use the lens dock to recolour the map by one metric. The <b>Explorer</b> compares districts, states and cities and highlights them on the map. The <b>Advisors</b> report computed observations with their sources.</p>
      <h4>Kinds of data</h4><p><span class="kind-badge kind-official">official</span> government statistics · <span class="kind-badge kind-modelled">modelled</span> estimates and the hex yield model · <span class="kind-badge kind-satellite">satellite</span> remote-sensing measurements · <span class="kind-badge kind-historical">historical</span> interpretations with uncertainty · <span class="kind-badge kind-curated">curated</span> compiled lists (for example Wikidata coordinates).</p>
      <h4>Reference years</h4><p>Each lens and table shows its own reference year. Census 2011 values are 2011 values; the map never presents them as current. Where a model combines years (for example 2023-24 GSDP spread by Census 2011 non-farm workers), the description says so.</p>
      <h4>Boundaries</h4><p>The outline follows the official map of India (Survey of India, via DataMeet). Hexes inside it that Pakistan or China administer are hatched; Indian statistics do not cover them, so their values are missing. Neighbouring countries follow Natural Earth's India point-of-view boundaries.</p>`;
    case "yields": {
      const n = app.nation;
      return `<h3>Yields</h3><p>Eight yields turn real indicators into game resources. Each yield has one main indicator with real units (state and national totals, in the top bar) and a documented hex model.</p>
        <table class="data"><thead><tr><th class="l">Yield</th><th>India total</th><th class="l">Unit</th><th class="l">States without data</th></tr></thead><tbody>${n.yields_meta.map((y) => `<tr><td class="l">${y.emoji} ${esc(y.name)}</td><td>${fmt(n.yields[y.id])}</td><td class="l">${esc(y.unit)}</td><td class="l faint">${esc(y.missing_states.join(", "))}</td></tr>`).join("")}</tbody></table>
        ${n.yields_meta.map((y) => `<h4>${y.emoji} ${esc(y.name)}</h4><p>${esc(y.note)} <button class="linkish" data-lens="y_${y.id}">Show the ${esc(y.name)} lens</button></p>`).join("")}
        <h4>Tile pips</h4><p>Each land hex has 0–4 pips per yield: the quintile of its value per km² among all land hexes with data (culture, faith and infrastructure use quartiles of hexes that have any such site; 0 = none). Pips compare hexes; they are not units. Pips of 3 or more show under the hex when you zoom in.</p>
        <h4>City footprints and specialisations</h4><p>A city's footprint is its hex plus the six neighbours (~2,400 km²). Footprint yields are sums of the hex model. A city gets a specialisation when a yield per resident in its footprint is at least 1.5× the national rate (Census 2011 population as the common denominator), or when the footprint holds a major port, three or more national institutes / NIRF top-25 institutions, or a UNESCO site. The evidence is shown in the city panel.</p>
        <h4>Normalisation rules</h4><p>Absolute output (₹, tonnes, persons) is never added across yields. Lenses show density (per km²), rates (per person, per household, per 1,000) or shares, and the legend names the unit. Counts are divided by area before they are compared between regions of different size.</p>
        <pre style="white-space:pre-wrap;font-size:11px;color:var(--ink-dim)">${esc(n.model_note || "")}</pre>`;
    }
    case "terrain": return `<h3>Terrain rules</h3>${["water", "relief", "cover"].map((t) => `<h4>${t}</h4><table class="data"><tbody>${w.tables[t].map((r) => `<tr><td class="l">${r.color ? `<i style="display:inline-block;width:10px;height:10px;background:${r.color};margin-right:6px"></i>` : ""}${esc(r.name)}</td><td class="l" style="white-space:normal">${esc(r.rule)}</td></tr>`).join("")}</tbody></table>`).join("")}`;
    case "lenses": return `<h3>Lenses</h3><table class="data"><thead><tr><th class="l">Lens</th><th class="l">Unit</th><th class="l">Year</th><th class="l">Resolution</th><th class="l">Kind</th><th>Coverage</th><th class="l">Source</th></tr></thead><tbody>${app.lensIdx.lenses.map((l) => `<tr><td class="l"><button class="linkish" data-lens="${l.id}">${l.emoji} ${esc(l.name)}</button></td><td class="l">${esc(l.unit)}</td><td class="l">${esc(l.year || "")}</td><td class="l">${esc(l.resolution)}</td><td class="l"><span class="kind-badge kind-${esc(l.kind)}">${esc(l.kind)}</span></td><td>${Math.round((l.coverage ?? 1) * 100)}%</td><td class="l"><button class="linkish" data-p="src:${esc(l.source)}">${esc(l.source)}</button></td></tr>`).join("")}</tbody></table>
      ${app.lensIdx.lenses.map((l) => `<h4>${l.emoji} ${esc(l.name)}</h4><p>${esc(l.description)}</p>`).join("")}`;
    case "method": return `<h3>Methodology</h3>
      <h4>Pipeline</h4><p>1. <code>raw/</code> source files, unchanged. 2. <code>pipeline/fetch_*.py</code> download them. 3. <code>pipeline/build_*.py</code> write normalized tables (<code>data/normalized/*.json</code>) with metadata. 4. <code>grid.py</code> and <code>terrain.py</code> build the hex grid and sample rasters. 5. <code>publish.py</code> and <code>mechanics.py</code> join tables to hexes and compute yields. 6. The browser reads <code>site/data/</code>.</p>
      <h4>Hex grid</h4><p>Pointy-top hexes, 20 km flat to flat, on a Lambert conformal conic projection (central meridian 82°E, standard parallels 12.47°N and 35.17°N). About 73 evenly spaced sample points per hex measure the share of each district, state, land cover class and raster value in the hex.</p>
      <h4>Joining districts to hexes</h4><p>Each dataset joins to the boundaries of its own vintage: Census 2011 tables to the 640 Census 2011 districts, NFHS-5 to ~2020 districts. A <b>count</b> becomes a density: district value ÷ district area, then the area-weighted mean of the districts in the hex. A <b>rate</b> is the area-weighted mean of the district rates; a hex is missing when districts with data cover less than half of it. A <b>state</b> value applies to every hex of the state. Small districts (smaller than a hex) still contribute through their sample points; every state, UT and ~2020 district owns at least one hex.</p>
      <h4>Missing data</h4><p>Missing values stay missing (hatched grey on lenses, “no data” in panels). Nothing is interpolated or estimated to fill gaps. A lens is published only if at least 50 hexes have data.</p>
      <h4>Disputed areas</h4><p>The outline is India's official boundary. Areas administered by Pakistan (Gilgit-Baltistan and the area Pakistan calls Azad Kashmir) and China (Aksai Chin, Shaksgam) are hatched and have no statistics.</p>`;
    case "history": return `<h3>History layer</h3><p><b>Compare</b>: in History mode, press "⇄ Compare eras" (or C) and pick a second era on the timeline. Era B shows in blue, A in gold, and their overlap as a blend. The card gives the area, the share inside today's India, the number of today's states each extent touches, and the overlap. <b>Overlay</b>: in Present mode, the 🏺 button lays an era's outline over any modern lens and gives the lens mean inside and outside the outline. These numbers count hexes inside approximate outlines; they describe, they do not explain.</p><p>The history timeline is a separate mode. Places and capitals come from Wikidata (each has a QID); empire extents come from the <i>historical-basemaps</i> project (GPL-3.0) as single-year snapshots, drawn with soft, dashed edges. Extents before 1000 CE have low confidence. Polities without a published polygon have no outline: none is drawn by hand. Routes join documented waypoint cities with straight lines; they are not surveyed paths.</p><p><button class="linkish" data-p="src:history">History source record</button></p>`;
    case "strengths": return `<h3>Hidden strengths</h3>
      <p>A hidden strength is a place that does better than places with the same conditions. For each question, a least-squares line predicts the outcome from a few conditions (for example graduates from urban share, density and household assets). The score is the gap between the actual and the predicted value, divided by the standard deviation of all gaps. A score of +1.5 or more counts as a strength. For outcomes where lower is better (child stunting), the sign is reversed, so a positive score is always good.</p>
      <h4>Rules</h4><p>Each model uses one table of one vintage: Census 2011 districts, NFHS-5 districts (2019–21 boundaries) or states. The pipeline does not mix district vintages in one fit. A model with R² below 0.1 is not published, because its "expected" value says almost nothing (the immunisation model failed this rule). Crop rows with a rice or wheat yield above 7 t/ha are source errors and are left out (North Goa, South Goa in APY 2022-23).</p>
      <h4>Limits</h4><p>A score is a question, not an answer. A condition that the model leaves out (irrigation, history, policy, data errors) moves the score too. The drawer shows the weights, R², sample size and years of every model. Code: <code>pipeline/strengths.py</code>; open the drawer with <b>S</b> or the Strengths button.</p>`;
    case "change": return `<h3>Change over time</h3>
      <p>Time lenses have one map per year with a slider and a play button. Each year goes through the same hex aggregation on its own; the pipeline never mixes years inside one map. All years share one colour scale, so change shows as colour change.</p>
      <h4>Boundaries</h4><p>District population 1901–2011 comes from Census 2011 Table A-2, which gives every census year on 2011 district boundaries, so the districts compare directly. State literacy before 2011 is on the state boundaries of the census year (Economic Survey 2021-22 Table 8.5); the legend shows the basis of each year. Literacy uses the population aged 5+ for 1951–1971 and aged 7+ from 1981. State urban share is available for 1991–2011 only.</p>
      <h4>Gaps</h4><p>Assam had no census in 1981. Arunachal Pradesh has no population before 1961. Andhra Pradesh, Telangana, Jammu and Kashmir, Ladakh and Dadra and Nagar Haveli and Daman and Diu have no urban share or literacy before 2011 on present boundaries, so the map shows them as no data. Income per person uses constant 2011-12 prices (MoSPI), 2011-12 to 2024-25.</p>
      <p>${app.lensIdx.lenses.filter((l) => l.group === "change").map((l) => `<button class="linkish" data-lens="${l.id}">${l.emoji} ${esc(l.name)}</button>`).join(" · ")}</p>`;
    case "sources": return `<h3>Sources</h3><p>${sources.length} source records.</p><table class="data"><thead><tr><th class="l">Id</th><th class="l">Name</th><th class="l">Organisation</th><th class="l">Year</th><th class="l">Kind</th></tr></thead><tbody>${sources.map((s) => `<tr><td class="l"><button class="linkish" data-p="src:${esc(s.id)}">${esc(s.id)}</button></td><td class="l" style="white-space:normal">${esc(s.name)}</td><td class="l" style="white-space:normal">${esc(s.source_org)}</td><td class="l">${esc(s.reference_year)}</td><td class="l"><span class="kind-badge kind-${esc(s.kind)}">${esc(s.kind)}</span></td></tr>`).join("")}</tbody></table>`;
    case "gaps": {
      const g = sources.filter((s) => /could not|not reach|unreachable|captcha|403|404|not deliver|not built|no machine/i.test(s.coverage_note || ""));
      return `<h3>Data gaps</h3><p>These records note sources that could not be reached or parts that are not built. The full notes are in <code>data/meta/*.md</code> and <code>SOURCES.md</code>.</p>${g.map((s) => `<h4>${esc(s.id)}</h4><pre style="white-space:pre-wrap;font-size:11px;color:var(--ink-dim)">${esc((s.coverage_note || "").split("\n").filter((l) => /could not|not reach|unreachable|captcha|403|404|not deliver|not built|fail|timeout|login/i.test(l)).join("\n"))}</pre>`).join("")}`;
    }
    case "keys": return `<h3>Keys</h3><table class="data"><tbody>${[["Drag / wheel / pinch", "Pan and zoom"], ["Double-click", "Zoom in"], ["/", "Search"], ["L", "All lenses"], ["R", "Resources on or off"], ["H", "History mode on or off"], ["S", "Hidden strengths"], ["E", "Explorer"], ["A", "Advisors"], ["?", "Almanac"], ["Esc", "Close or clear the selection"], ["+ / −", "Zoom"]].map(([k, v]) => `<tr><td class="l"><kbd>${esc(k)}</kbd></td><td class="l">${esc(v)}</td></tr>`).join("")}</tbody></table>`;
  }
  return "";
}
