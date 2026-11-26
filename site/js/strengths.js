// Hidden strengths drawer: places that do better than their conditions predict (pipeline/strengths.py).
import { fmt, esc } from "./geo.js";
import { setLens, select, load } from "./main.js";

let app = null, data = null, cur = null;
const SEL_TYPE = { district2011: "district11", district2020: "district", state: "state" };
const TABLE_NAME = { district2011: "districts, Census 2011", district2020: "districts, 2019–21", state: "states" };

export async function open(a, id) {
  app = a; data = data || (await load("strengths"));
  let el = document.getElementById("strengths");
  if (!el) { el = document.createElement("aside"); el.id = "strengths"; el.className = "panel drawer-left"; document.body.appendChild(el); }
  document.getElementById("explorer")?.setAttribute("hidden", "");
  el.hidden = false;
  show(id || cur || data.models[0].id);
}

export function close() { document.getElementById("strengths")?.setAttribute("hidden", ""); }

const num = (v, unit) => (v == null ? "—" : unit?.startsWith("US$") || unit === "institutions" ? fmt(Math.round(v)) : fmt(v));
const sigma = (z) => `${z >= 0 ? "+" : "−"}${Math.abs(z).toFixed(1)}σ`;

function show(id) {
  cur = id;
  const m = data.models.find((x) => x.id === id) || data.models[0];
  const el = document.getElementById("strengths");
  const row = (t, k) => `<li><button class="hs-row" data-k="${esc(t.key)}"><span class="hs-rank">${k + 1}</span>
      <span class="hs-name">${esc(t.name)} <small class="faint">${esc(t.state || "")}</small></span>
      <span class="hs-vals">${num(t.actual, m.outcome.unit)} <small class="faint">vs ${num(t.expected, m.outcome.unit)} expected</small></span>
      <span class="hs-z ${t.score >= 0 ? "up" : "down"}">${sigma(t.score)}</span></button></li>`;
  const wmax = Math.max(...m.conditions.map((c) => Math.abs(c.weight)), 1e-9);
  el.innerHTML = `
    <header><h2>Hidden strengths</h2><div class="sub">Places that do better than their conditions predict</div>
      <button class="close icon-btn" aria-label="Close">✕</button></header>
    <nav class="hs-tabs">${data.models.map((x) => `<button data-m="${x.id}" aria-pressed="${x.id === m.id}" title="${esc(x.name)}">${x.emoji} ${esc(x.name.split(" beyond")[0])}</button>`).join("")}</nav>
    <section>
      <h3>${m.emoji} ${esc(m.name)}</h3>
      <p class="hs-q">${esc(m.question)}</p>
      <div class="hs-actions"><button class="btn" id="hs-map">Map the score</button><button class="btn" id="hs-ex">Actual vs expected in Explorer</button></div>
    </section>
    <section><h3>Above expectation</h3><ol class="hs-list">${m.top.map(row).join("")}</ol>
      <details class="hs-more"><summary>Below expectation</summary><ol class="hs-list">${m.bottom.map(row).join("")}</ol></details></section>
    <section class="hs-method"><h3>How the score works</h3>
      <p>Outcome: <b>${esc(m.outcome.name)}</b> (${esc(m.outcome.unit)}${m.outcome.higher_is === "worse" ? ", lower is better" : ""}).
      The model predicts it from the conditions below with a least-squares fit over ${m.n} ${TABLE_NAME[m.table]}.
      The score is the gap between the actual and the predicted value, in standard deviations. +1.5σ or more counts as a strength (${m.flagged} places).</p>
      <div class="hs-conds">${m.conditions.map((c) => `<div><span>${esc(c.name)}</span><i style="width:${Math.round((Math.abs(c.weight) / wmax) * 100)}%" class="${c.weight >= 0 ? "pos" : "neg"}"></i><small>${c.weight >= 0 ? "+" : "−"}</small></div>`).join("")}</div>
      <p class="faint">Bars: weight of each condition in the fit (standardised). R² = ${m.r2.toFixed(2)}: the conditions explain ${Math.round(m.r2 * 100)}% of the variation.
      Years: ${Object.entries(m.years).map(([k, v]) => `${esc(k)} ${esc(v || "")}`).join(" · ")}.
      ${m.excluded?.length ? `Left out as source errors: ${m.excluded.map(esc).join(", ")}.` : ""}</p>
      ${m.note ? `<p class="hs-note">${esc(m.note)}</p>` : ""}
      <p class="faint">A high score is a question, not an answer. Conditions that the model leaves out (irrigation, history, policy, data errors) also move the score.</p>
    </section>`;
  el.querySelector(".close").onclick = close;
  el.querySelectorAll(".hs-tabs button").forEach((b) => (b.onclick = () => show(b.dataset.m)));
  el.querySelectorAll(".hs-row").forEach((b) => (b.onclick = () => {
    const t = SEL_TYPE[m.table];
    select(t === "state" ? { type: "state", id: b.dataset.k } : { type: t, key: b.dataset.k }, { fly: true });
  }));
  el.querySelector("#hs-map").onclick = () => app.lens !== m.lens && setLens(m.lens);
  el.querySelector("#hs-ex").onclick = async () => { close(); (await import("./explorer.js")).render(null, app, { table: m.explorer.table, x: m.explorer.x, y: m.explorer.y }); };
  if (app.lens !== m.lens) setLens(m.lens);
}
