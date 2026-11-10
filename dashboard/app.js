/* Rolulabo, dashboard narrativo. Estado, filtros, agregación y render.
   Los datos vienen de data.js (reports/build_dashboard_data.py) en formato columnar. */
"use strict";

const D = window.DATA;
const C = D.cols;
const N = C.y.length;
const DIM = D.dims;
const MES = ["ene", "feb", "mar", "abr", "may", "jun", "jul", "ago", "sep", "oct", "nov", "dic"];
const HIGH = new Set(D.decision.estados.map(s => DIM.state.indexOf(s)));
const SEM = ["", "Rojo", "Amarillo", "Verde"];

// ------------------------------------------------------------------ formato es-MX
const NF = {};
const nf = d => (NF[d] ??= new Intl.NumberFormat("es-MX", { minimumFractionDigits: d, maximumFractionDigits: d }));
const int = v => nf(0).format(Math.round(v));
const money = v => (v < 0 ? "-$" : "$") + nf(0).format(Math.abs(Math.round(v)));
const moneyK = v => {
  const a = Math.abs(v), s = v < 0 ? "-$" : "$";
  if (a >= 1e6) return s + nf(2).format(a / 1e6) + " M";
  if (a >= 1e4) return s + nf(0).format(a / 1e3) + " mil";
  if (a >= 1e3) return s + nf(1).format(a / 1e3) + " mil";
  return s + nf(0).format(a);
};
const pct = (v, d = 1) => (isFinite(v) ? nf(d).format(v * 100) + "%" : "sin datos");
const signPct = v => (v >= 0 ? "+" : "") + pct(v);
const css = n => getComputedStyle(document.documentElement).getPropertyValue(n).trim();
const $ = s => document.querySelector(s);
const el = (tag, attrs = {}, html = "") => { const e = document.createElement(tag); Object.assign(e, attrs); if (html) e.innerHTML = html; return e; };
const sum = (I, f) => { let t = 0; for (const i of I) t += f(i); return t; };

// ------------------------------------------------------------------ estado en el hash
const S = { p: "2017", r: -1, c: -1, s: -1, pol: "c", e: "both", th: "dark", only: null };
function readHash() {
  const h = new URLSearchParams(location.hash.slice(1));
  if (h.has("p")) S.p = h.get("p");
  for (const k of ["r", "c", "s"]) if (h.has(k)) S[k] = +h.get(k);
  if (h.has("pol")) S.pol = h.get("pol") === "b" ? "b" : "c";
  if (h.has("e")) S.e = h.get("e");
  if (h.has("th")) S.th = h.get("th") === "light" ? "light" : "dark";
  S.only = h.get("only");
}
function writeHash() {
  const h = new URLSearchParams({ p: S.p, r: S.r, c: S.c, s: S.s, pol: S.pol, e: S.e, th: S.th });
  if (S.only) h.set("only", S.only);
  history.replaceState(null, "", "#" + h);
}

// ------------------------------------------------------------------ filtros y agregación
const yearOk = y => S.p === "all" || (S.p === "train" ? y <= 2016 : y === +S.p);
const periodLabel = () => ({ all: "2014 a 2017", train: "2014 a 2016" })[S.p] || S.p;
const polLabel = () => (S.pol === "b" ? "todo el país" : "los 10 estados de descuento alto");
function rows({ period = true, only2017 = false } = {}) {
  const I = [];
  for (let i = 0; i < N; i++) {
    if (only2017 ? C.y[i] !== 2017 : period && !yearOk(C.y[i])) continue;
    if (S.r >= 0 && C.rg[i] !== S.r) continue;
    if (S.c >= 0 && C.ca[i] !== S.c) continue;
    if (S.s >= 0 && C.st[i] !== S.s) continue;
    I.push(i);
  }
  return I;
}
const capped = i => S.pol === "b" || HIGH.has(C.st[i]);
const P2 = i => (capped(i) ? C.p2[i] : C.p[i]);
const S2 = i => (capped(i) ? C.s2[i] : C.s[i]);
const D2 = i => (capped(i) ? C.d2[i] : C.d[i]);
function agg(I) {
  const A = { n: I.length, s: 0, p: 0, s2: 0, p2: 0, nl: 0, nl2: 0, la: 0, la2: 0, aff: 0, d: 0, dd: 0 };
  for (const i of I) {
    const p = C.p[i], p2 = P2(i);
    A.s += C.s[i]; A.p += p; A.s2 += S2(i); A.p2 += p2; A.d += C.d[i]; A.dd += D2(i);
    if (p < 0) { A.nl++; A.la -= p; }
    if (p2 < -0.005) { A.nl2++; A.la2 -= p2; }
    if (D2(i) !== C.d[i]) A.aff++;
  }
  A.m = A.p / A.s; A.m2 = A.p2 / A.s2; A.d /= 100 * (A.n || 1); A.dd /= 100 * (A.n || 1);
  return A;
}
function groupBy(I, key) {
  const m = new Map();
  for (const i of I) { const k = key(i); if (!m.has(k)) m.set(k, []); m.get(k).push(i); }
  return m;
}
const showA = () => S.e !== "b";
const showB = () => S.e !== "a";
const SERIES = () => [showA() && "Hoy", showB() && "Con topes"].filter(Boolean);
const filterText = () => {
  const f = [];
  if (S.r >= 0) f.push("región " + DIM.region[S.r]);
  if (S.c >= 0) f.push(DIM.category[S.c]);
  if (S.s >= 0) f.push(DIM.state[S.s]);
  return f.length ? ", " + f.join(", ") : "";
};

// ------------------------------------------------------------------ gráficas
const COL = () => ({ a: css("--a"), b: css("--b"), ctx: css("--context"), neg: css("--neg"), ink: css("--ink"),
  ink2: css("--ink-2"), ink3: css("--ink-3"), rule: css("--rule"), cell0: css("--cell-0"), page: css("--page"),
  card: css("--card"), sr: css("--sem-r"), sy: css("--sem-y"), sg: css("--sem-g") });
let K = COL();
const entScale = () => ({ domain: ["Hoy", "Con topes"], range: [K.a, K.b] });

function P(opts, el) {
  const width = Math.max(280, Math.floor(el.clientWidth || 560));
  const plot = Plot.plot({
    width, marginLeft: 48, marginRight: 16, marginTop: 26, marginBottom: 32,
    style: { background: "transparent", color: K.ink2, fontFamily: "Montserrat, sans-serif", fontSize: "12px", overflow: "visible" },
    ...opts,
  });
  plot.querySelectorAll("[aria-label='y-grid'] line, [aria-label='x-grid'] line").forEach(l => { l.setAttribute("stroke", K.rule); l.setAttribute("stroke-opacity", 1); });
  return plot;
}
const grid = { grid: true };

function chart(fig, { title, note, legend, plot, table }) {
  fig.innerHTML = "";
  fig.setAttribute("aria-label", title);
  fig.append(el("h3", {}, title));
  if (note) fig.append(el("p", { className: "note" }, note));
  if (legend) fig.append(el("div", { className: "legend" }, legend.map(([t, c]) => `<span><i style="--c:${c}"></i>${t}</span>`).join("")));
  const box = el("div", { className: "plot" });
  fig.append(box);
  box.append(plot(box));
  if (table) {
    const d = el("details");
    const [head, body] = table;
    d.innerHTML = `<summary>Ver tabla</summary><table><thead><tr>${head.map((h, j) => `<th class="${j ? "n" : ""}">${h}</th>`).join("")}</tr></thead><tbody>${body.map(r => `<tr>${r.map((c, j) => `<td class="${j ? "n" : ""}">${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
    fig.append(d);
  }
}
const legendEnt = () => SERIES().map(s => [s, s === "Hoy" ? K.a : K.b]);

// tooltip propio para el mapa y las barras versus
const tip = $("#tip");
function showTip(ev, html) {
  tip.innerHTML = html; tip.style.display = "block";
  const w = tip.offsetWidth, h = tip.offsetHeight;
  tip.style.left = Math.min(innerWidth - w - 8, ev.clientX + 14) + "px";
  tip.style.top = Math.min(innerHeight - h - 8, ev.clientY + 14) + "px";
}
const hideTip = () => { tip.style.display = "none"; };

// ------------------------------------------------------------------ hero
function renderHero(A) {
  const up = A.p !== 0 ? (A.p2 - A.p) / Math.abs(A.p) : 0;
  $("#dek").innerHTML = A.aff
    ? `En ${periodLabel()}${filterText()}, con topes en ${polLabel()} la utilidad pasa de <span class="ta">${money(A.p)}</span> a <span class="tb">${money(A.p2)}</span> (${signPct(up)}) con el mismo volumen. Solo cambia el descuento en ${int(A.aff)} de ${int(A.n)} líneas.`
    : `En ${periodLabel()}${filterText()} ninguna línea supera su tope, así que hoy y con topes es lo mismo.`;
  const card = (ent, name, sub, c, tags, kpis, dl) => `
    <article class="profile ${(ent === "a" && !showA()) || (ent === "b" && !showB()) ? "dim" : ""}" style="--c:${c}">
      <div class="p-head"><div class="avatar">${name[0]}</div><div><div class="p-name">${name}</div><div class="p-sub">${sub}</div></div></div>
      <div class="tags">${tags.map(t => `<span class="tag">${t}</span>`).join("")}</div>
      <div class="kpis">${kpis.map(([v, l]) => `<div class="kpi"><b>${v}</b><span>${l}</span></div>`).join("")}</div>
      <dl>${dl.map(([k, v, n]) => `<dt>${k}</dt><dd>${v}${n ? `<small>${n}</small>` : ""}</dd>`).join("")}</dl>
    </article>`;
  $("#profiles").innerHTML =
    card("a", "Hoy", "Política de descuento actual", "var(--a)",
      ["Descuento fijo por estado", `${pct(A.nl / A.n)} de líneas pierden`, "Se ve al cierre contable"],
      [[moneyK(A.p), "Utilidad"], [pct(A.m), "Margen"], [int(A.nl), "Líneas con pérdida"]],
      [["Ventas", money(A.s)], ["Monto perdido", money(A.la), "Suma de las líneas con utilidad negativa"],
       ["Descuento promedio", pct(A.d)]]) +
    card("b", "Con topes", "Descuento máximo por subcategoría", "var(--b)",
      [S.pol === "b" ? "Opción B, todo el país" : "Opción C, 10 estados", "Volumen constante", "Semáforo y decisión humana"],
      [[moneyK(A.p2), "Utilidad"], [pct(A.m2), "Margen"], [int(A.nl2), "Líneas con pérdida"]],
      [["Ventas", money(A.s2), "Suben porque se cobra más por línea"], ["Monto perdido", money(A.la2)],
       ["Líneas con tope aplicado", `${int(A.aff)} (${pct(A.aff / A.n)})`]]);
}

// ------------------------------------------------------------------ 00 cara a cara
function renderC0(I, A) {
  const up = A.p !== 0 ? (A.p2 - A.p) / Math.abs(A.p) : 0;
  $("#h0").textContent = A.aff
    ? `Con topes la utilidad ${A.p < 0 && A.p2 > 0 ? "deja de ser pérdida" : `sube ${pct(up, 0)}`} y las líneas con pérdida bajan de ${pct(A.nl / A.n)} a ${pct(A.nl2 / A.n)}`
    : "En este corte los topes no cambian ninguna línea";
  $("#x0").textContent = `Mismas ${int(A.n)} líneas de ${periodLabel()}${filterText()}, mismo volumen. Topes en ${polLabel()}. Cada barra tiene su propia escala.`;
  const M = [
    ["Utilidad", "dólares", A.p, A.p2, money, 1],
    ["Margen", "utilidad entre ventas", A.m, A.m2, v => pct(v), 1],
    ["Ventas", "dólares", A.s, A.s2, money, 0],
    ["Líneas con pérdida", "porcentaje de líneas", A.nl / A.n, A.nl2 / A.n, v => pct(v), -1],
    ["Monto perdido", "dólares", A.la, A.la2, money, -1],
    ["Descuento promedio", "por línea", A.d, A.dd, v => pct(v), 0],
  ];
  $("#versus").innerHTML = M.map(([l, u, a, b, f, better]) => {
    const mx = Math.max(Math.abs(a), Math.abs(b)) || 1;
    const win = better === 0 || a === b ? null : (better > 0 ? (b > a ? "b" : "a") : (b < a ? "b" : "a"));
    const bar = (ent, v, c) => `<div class="vs-bar" style="--c:${v < 0 ? "var(--neg)" : c}" data-t="${ent === "a" ? "Hoy" : "Con topes"}: ${f(v)}">
        <div class="trk"><div class="fill" style="width:${(Math.abs(v) / mx) * 100}%"></div></div><div class="v ${win === ent ? "win" : ""}">${f(v)}</div></div>`;
    return `<div class="vs-row"><div class="vs-lbl">${l}<small>${u}</small></div><div class="vs-bars">
      ${showA() ? bar("a", a, "var(--a)") : ""}${showB() ? bar("b", b, "var(--b)") : ""}</div></div>`;
  }).join("") + `<div class="legend" style="margin-top:12px">${legendEnt().map(([t, c]) => `<span><i style="--c:${c}"></i>${t}</span>`).join("")}</div>`;
  $("#versus").querySelectorAll(".vs-bar").forEach(b => { b.onmousemove = e => showTip(e, b.dataset.t); b.onmouseleave = hideTip; });

  // cinco insights calculados con el filtro
  const ins = [];
  const bySub = [...groupBy(I, i => C.sb[i])].map(([k, J]) => ({ k, d: sum(J, i => P2(i) - C.p[i]), J }))
    .sort((x, y) => y.d - x.d);
  const tot = bySub.reduce((t, x) => t + x.d, 0);
  if (tot > 0) {
    const t0 = bySub[0], tp = D.topes.find(t => t.sub === DIM.sub[t0.k]);
    ins.push([`${DIM.sub[t0.k]} aporta ${pct(t0.d / tot, 0)} de lo que se gana con topes`,
      `Hoy su descuento promedio es ${pct(sum(t0.J, i => C.d[i]) / 100 / t0.J.length, 0)} y el tope es ${pct(tp.tope, 0)}.`]);
  }
  const bySt = [...groupBy(I, i => C.st[i])].map(([k, J]) => ({ k, p: sum(J, i => C.p[i]), p2: sum(J, P2) })).sort((x, y) => x.p - y.p);
  if (bySt.length && bySt[0].p < 0) ins.push([`${DIM.state[bySt[0].k]} es donde más se pierde, ${money(bySt[0].p)}`,
    `Con topes queda en ${money(bySt[0].p2)}. El descuento ahí es política del estado, no del vendedor.`]);
  const q = lv => { const J = I.filter(lv); return J.length ? sum(J, i => C.q[i]) / J.length : NaN; };
  const q0 = q(i => C.d[i] === 0), q20 = q(i => C.d[i] >= 20);
  if (isFinite(q0) && isFinite(q20)) ins.push([`Sin descuento se llevan ${nf(1).format(q0)} unidades por línea, con 20% o más, ${nf(1).format(q20)}`,
    `El descuento no compra volumen (correlación ${nf(3).format(D.h2_rho)}). Quitarlo donde pierde casi no arriesga ventas.`]);
  const J20 = I.filter(i => C.d[i] === 20);
  if (J20.length) ins.push([`Con 20% exacto pierde ${pct(J20.filter(i => C.p[i] < 0).length / J20.length, 0)} de las líneas`,
    "La regla actual solo marca arriba de 20%, así que ahí no ve nada. El modelo sí."]);
  let dB = 0, dC = 0;
  for (const i of I) { dB += C.p2[i] - C.p[i]; if (HIGH.has(C.st[i])) dC += C.p2[i] - C.p[i]; }
  if (dB > 0) ins.push([`Topes solo en 10 estados capturan ${pct(dC / dB, 0)} del beneficio de aplicarlos en todo el país`,
    "Por eso la recomendación es empezar ahí, en dos olas que sirven de experimento."]);
  $("#insights").innerHTML = ins.slice(0, 5).map(([a, b]) => `<li><div><p>${a}</p><p>${b}</p></div></li>`).join("")
    || "<li><div><p>Sin datos para este corte.</p></div></li>";
}

// ------------------------------------------------------------------ 01 origen
function renderC1(I, A) {
  const years = [...new Set(I.map(i => C.y[i]))].sort();
  const byM = groupBy(I, i => C.y[i] * 100 + C.m[i]);
  const mdata = [...byM].sort((a, b) => a[0] - b[0]).map(([k, J]) => ({ date: new Date(Date.UTC(Math.floor(k / 100), (k % 100) - 1, 1)), p: sum(J, i => C.p[i]), p2: sum(J, P2), s: sum(J, i => C.s[i]) }));
  if (years.length > 1) {
    const y0 = years[0], y1 = years[years.length - 1];
    const Y = y => { const J = I.filter(i => C.y[i] === y); return [sum(J, i => C.s[i]), sum(J, i => C.p[i])]; };
    const [s0, p0] = Y(y0), [s1, p1] = Y(y1);
    $("#h1").textContent = `De ${y0} a ${y1} las ventas crecieron ${pct((s1 - s0) / s0, 0)} y el margen pasó de ${pct(p0 / s0)} a ${pct(p1 / s1)}`;
  } else {
    const worst = mdata.slice().sort((a, b) => (b.p2 - b.p) - (a.p2 - a.p))[0];
    $("#h1").textContent = mdata.length
      ? `En ${periodLabel()} los descuentos que pierden costaron ${money(A.p2 - A.p)}, y ${worst ? MES[worst.date.getUTCMonth()] : ""} fue el mes más caro`
      : "Sin datos para este corte";
  }
  $("#x1").textContent = "Utilidad mensual en dólares. La distancia entre las dos líneas es lo que cuestan los descuentos que pasan el tope. No hay patrón de temporada, se pierde todo el año.";

  const long = mdata.flatMap(d => [showA() && { date: d.date, serie: "Hoy", v: d.p }, showB() && { date: d.date, serie: "Con topes", v: d.p2 }]).filter(Boolean);
  const multi = years.length > 1;
  chart($("#f-mes"), {
    title: "Utilidad mensual, hoy y con topes",
    note: multi ? "La banda marca 2017, el año que el modelo nunca vio." : `Meses de ${periodLabel()}.`,
    legend: legendEnt(),
    plot: box => P({
      height: 300, marginLeft: 56, marginRight: 70,
      x: { type: "utc", label: null, ticks: multi ? 8 : 12, tickFormat: d => MES[d.getUTCMonth()] + (multi && d.getUTCMonth() === 0 ? " " + d.getUTCFullYear() : "") },
      y: { label: "Utilidad", tickFormat: moneyK, ticks: 5, ...grid },
      color: entScale(),
      marks: [
        multi && years.includes(2017) ? Plot.rectX([0], { x1: new Date(Date.UTC(2017, 0, 1)), x2: new Date(Date.UTC(2017, 11, 31)), fill: K.b, fillOpacity: 0.07 }) : null,
        Plot.ruleY([0], { stroke: K.ink3 }),
        Plot.lineY(long, { x: "date", y: "v", stroke: "serie", strokeWidth: 2, curve: "monotone-x" }),
        Plot.text(long, Plot.selectLast({ x: "date", y: "v", z: "serie", text: "serie", fill: "serie", dx: 6, textAnchor: "start", fontWeight: 600 })),
        Plot.tip(long, Plot.pointerX({ x: "date", y: "v", stroke: "serie", title: d => `${d.serie}, ${MES[d.date.getUTCMonth()]} ${d.date.getUTCFullYear()}\n${money(d.v)}` })),
      ],
    }, box),
    table: [["Mes", "Hoy ($)", "Con topes ($)", "Ventas ($)"], mdata.map(d => [`${MES[d.date.getUTCMonth()]} ${d.date.getUTCFullYear()}`, int(d.p), int(d.p2), int(d.s)])],
  });

  const byD = [...groupBy(I, i => C.d[i])].sort((a, b) => a[0] - b[0]).map(([d, J]) => ({
    d, n: J.length, l: J.filter(i => C.p[i] < 0).length / J.length, l2: J.filter(i => P2(i) < -0.005).length / J.length }));
  const dl = byD.flatMap(r => [showA() && { lv: r.d + "%", serie: "Hoy", v: r.l, n: r.n }, showB() && { lv: r.d + "%", serie: "Con topes", v: r.l2, n: r.n }]).filter(Boolean);
  chart($("#f-desc"), {
    title: "Líneas con pérdida según el descuento",
    note: "Desde 30% casi todo pierde. Con 20% ya pierde una parte, y la regla actual no lo marca.",
    legend: legendEnt(),
    plot: box => P({
      height: 300, marginLeft: 44, marginBottom: 36,
      fx: { label: "Descuento original de la línea", padding: 0.15 },
      x: { axis: null, domain: SERIES() },
      y: { label: "Líneas con pérdida", tickFormat: v => pct(v, 0), domain: [0, 1], ticks: 5, ...grid },
      color: entScale(),
      marks: [
        Plot.ruleY([0], { stroke: K.ink3 }),
        Plot.barY(dl, { fx: "lv", x: "serie", y: "v", fill: "serie", insetLeft: 1, insetRight: 1, tip: true,
          title: d => `${d.serie}, descuento ${d.lv}\n${pct(d.v)} de ${int(d.n)} líneas pierden` }),
      ],
    }, box),
    table: [["Descuento", "Líneas", "Pierden hoy", "Pierden con topes"], byD.map(r => [r.d + "%", int(r.n), pct(r.l), pct(r.l2)])],
  });
}

// ------------------------------------------------------------------ 02 mapa
const TILES = { ME: [11, 0], WI: [6, 1], VT: [10, 1], NH: [11, 1], WA: [1, 2], ID: [2, 2], MT: [3, 2], ND: [4, 2], MN: [5, 2], IL: [6, 2], MI: [7, 2], NY: [9, 2], MA: [10, 2],
  OR: [1, 3], NV: [2, 3], WY: [3, 3], SD: [4, 3], IA: [5, 3], IN: [6, 3], OH: [7, 3], PA: [8, 3], NJ: [9, 3], CT: [10, 3], RI: [11, 3],
  CA: [1, 4], UT: [2, 4], CO: [3, 4], NE: [4, 4], MO: [5, 4], KY: [6, 4], WV: [7, 4], VA: [8, 4], MD: [9, 4], DE: [10, 4],
  AZ: [2, 5], NM: [3, 5], KS: [4, 5], AR: [5, 5], TN: [6, 5], NC: [7, 5], SC: [8, 5], DC: [9, 5], OK: [4, 6], LA: [5, 6], MS: [6, 6], AL: [7, 6], GA: [8, 6], TX: [4, 7], FL: [9, 7] };
const ABBR = { Alabama: "AL", Arizona: "AZ", Arkansas: "AR", California: "CA", Colorado: "CO", Connecticut: "CT", Delaware: "DE", "District of Columbia": "DC", Florida: "FL", Georgia: "GA",
  Idaho: "ID", Illinois: "IL", Indiana: "IN", Iowa: "IA", Kansas: "KS", Kentucky: "KY", Louisiana: "LA", Maine: "ME", Maryland: "MD", Massachusetts: "MA", Michigan: "MI", Minnesota: "MN",
  Mississippi: "MS", Missouri: "MO", Montana: "MT", Nebraska: "NE", Nevada: "NV", "New Hampshire": "NH", "New Jersey": "NJ", "New Mexico": "NM", "New York": "NY", "North Carolina": "NC",
  "North Dakota": "ND", Ohio: "OH", Oklahoma: "OK", Oregon: "OR", Pennsylvania: "PA", "Rhode Island": "RI", "South Carolina": "SC", "South Dakota": "SD", Tennessee: "TN", Texas: "TX",
  Utah: "UT", Vermont: "VT", Virginia: "VA", Washington: "WA", "West Virginia": "WV", Wisconsin: "WI", Wyoming: "WY" };
const MCAP = 0.3;
const mColor = (m, ent) => m == null || !isFinite(m) ? K.cell0
  : m < 0 ? d3.interpolateRgb(K.cell0, K.neg)(Math.min(1, 0.25 + 0.75 * (-m / MCAP)))
    : d3.interpolateRgb(K.cell0, ent === "a" ? K.a : K.b)(Math.min(1, 0.15 + 0.85 * (m / MCAP)));

function tileMap(stats, ent) {
  const cs = 34, g = 3, W = 11 * (cs + g), H = 8 * (cs + g);
  const svg = d3.create("svg").attr("viewBox", `0 0 ${W} ${H}`).attr("role", "img")
    .attr("aria-label", `Mapa de margen por estado, ${ent === "a" ? "hoy" : "con topes"}`);
  for (const [name, ab] of Object.entries(ABBR)) {
    const [cx, cy] = TILES[ab]; const st = stats.get(DIM.state.indexOf(name));
    const m = st ? (ent === "a" ? st.m : st.m2) : null;
    const fill = mColor(m, ent);
    const x = (cx - 1) * (cs + g), y = cy * (cs + g);
    const sel = S.s >= 0 && DIM.state[S.s] === name;
    svg.append("rect").attr("x", x).attr("y", y).attr("width", cs).attr("height", cs).attr("rx", 3).attr("fill", fill)
      .attr("class", sel ? "sel" : null).attr("tabindex", st ? 0 : null)
      .on("mousemove", ev => showTip(ev, st ? `<b>${name}</b>${HIGH.has(DIM.state.indexOf(name)) ? " · descuento alto" : ""}<br>Ventas ${money(st.s)}<br>Hoy ${money(st.p)} (${pct(st.m)})<br>Con topes ${money(st.p2)} (${pct(st.m2)})<br><span style="color:var(--ink-3)">Clic para filtrar</span>` : `<b>${name}</b><br>Sin ventas en este corte`))
      .on("mouseleave", hideTip)
      .on("click", () => { if (!st) return; S.s = sel ? -1 : DIM.state.indexOf(name); hideTip(); update(); })
      .on("keydown", ev => { if (ev.key === "Enter" && st) { S.s = sel ? -1 : DIM.state.indexOf(name); update(); } });
    const light = d3.lab(fill).l > 58;
    svg.append("text").attr("x", x + cs / 2).attr("y", y + cs / 2 + 3).attr("text-anchor", "middle")
      .attr("fill", st ? (light ? "#111" : "#f3f1ea") : K.ink3).text(ab);
  }
  return svg.node();
}

function renderC2(I) {
  const stats = new Map([...groupBy(rows({ period: true, only2017: false }).filter(i => (S.c < 0 || C.ca[i] === S.c) && (S.r < 0 || C.rg[i] === S.r)), i => C.st[i])]
    .map(([k, J]) => { const s = sum(J, i => C.s[i]), p = sum(J, i => C.p[i]), s2 = sum(J, S2), p2 = sum(J, P2); return [k, { s, p, s2, p2, m: p / s, m2: p2 / s2 }]; }));
  // el mapa ignora el filtro de estado para que se pueda cambiar de estado con un clic
  const neg = [...stats.values()].filter(v => v.p < 0).length, neg2 = [...stats.values()].filter(v => v.p2 < 0).length;
  const worst = [...stats].sort((a, b) => a[1].p - b[1].p)[0];
  $("#h2").textContent = neg
    ? `${neg} estados pierden dinero hoy y con topes quedan ${neg2}. ${DIM.state[worst[0]]} pierde más que ninguno`
    : "Ningún estado pierde dinero en este corte";
  $("#x2").textContent = `Margen por estado, utilidad entre ventas, ${periodLabel()}${S.r >= 0 ? ", región " + DIM.region[S.r] : ""}${S.c >= 0 ? ", " + DIM.category[S.c] : ""}. Clic en un estado para filtrar todo el tablero.`;

  const fig = $("#f-map");
  fig.innerHTML = "";
  fig.setAttribute("aria-label", "Mapa de margen por estado");
  fig.append(el("h3", {}, "Margen por estado"));
  fig.append(el("p", { className: "note" }, "Rojo es pérdida. Entre más intenso el color, más margen."));
  const maps = el("div", { className: "maps" });
  for (const [ent, name] of [["a", "Hoy"], ["b", "Con topes"]]) {
    if ((ent === "a" && !showA()) || (ent === "b" && !showB())) continue;
    const m = el("div", { className: "map" });
    m.append(el("h4", {}, `<span class="${ent === "a" ? "ta" : "tb"}">${name}</span>`));
    m.append(tileMap(stats, ent));
    maps.append(m);
  }
  fig.append(maps);
  fig.append(el("div", { className: "ramp" }, `-30% <span class="g" style="background:linear-gradient(90deg, ${K.neg}, ${K.cell0} 50%, ${showB() ? K.b : K.a})"></span> +30% de margen`));
  const worst5 = [...stats].sort((a, b) => a[1].p - b[1].p).slice(0, 5).filter(([, v]) => v.p < 0);
  if (worst5.length) {
    const mx = Math.max(...worst5.flatMap(([, v]) => [Math.abs(v.p), Math.abs(v.p2)]));
    const bar = (ent, v) => `<div class="vs-bar" style="--c:${v < 0 ? "var(--neg)" : ent === "a" ? "var(--a)" : "var(--b)"}"><div class="trk"><div class="fill" style="width:${Math.abs(v) / mx * 100}%"></div></div><div class="v">${money(v)}</div></div>`;
    fig.append(el("div", { className: "worst" }, `<h4>Los estados que más pierden, hoy y con topes</h4>` + worst5.map(([k, v]) =>
      `<div class="vs-row"><div class="vs-lbl">${DIM.state[k]}<small>${HIGH.has(k) ? "En la opción C" : "Fuera de la opción C"}</small></div><div class="vs-bars">${showA() ? bar("a", v.p) : ""}${showB() ? bar("b", v.p2) : ""}</div></div>`).join("")));
  }
  const tr = [...stats].sort((a, b) => a[1].p - b[1].p).map(([k, v]) => [DIM.state[k], int(v.s), int(v.p), pct(v.m), int(v.p2), pct(v.m2)]);
  const d = el("details"); d.innerHTML = `<summary>Ver tabla</summary><table><thead><tr><th>Estado</th><th class="n">Ventas ($)</th><th class="n">Hoy ($)</th><th class="n">Margen hoy</th><th class="n">Con topes ($)</th><th class="n">Margen con topes</th></tr></thead><tbody>${tr.map(r => `<tr>${r.map((c, j) => `<td class="${j ? "n" : ""}">${c}</td>`).join("")}</tr>`).join("")}</tbody></table>`;
  fig.append(d);

  const subs = [...groupBy(I, i => C.sb[i])].map(([k, J]) => ({ sub: DIM.sub[k], p: sum(J, i => C.p[i]), p2: sum(J, P2) })).sort((a, b) => a.p - b.p);
  const sl = subs.flatMap(r => [showA() && { sub: r.sub, serie: "Hoy", v: r.p }, showB() && { sub: r.sub, serie: "Con topes", v: r.p2 }]).filter(Boolean);
  chart($("#f-sub"), {
    title: "Utilidad por subcategoría",
    note: "Ordenadas de la que más pierde hoy a la que más gana.",
    legend: legendEnt(),
    plot: box => P({
      height: Math.max(220, subs.length * (SERIES().length * 9 + 9)), marginLeft: 92, marginRight: 12,
      fy: { label: null, domain: subs.map(r => r.sub), padding: 0.12 },
      y: { axis: null, domain: SERIES() },
      x: { label: null, tickFormat: moneyK, ticks: 4, ...grid },
      color: entScale(),
      marks: [
        Plot.barX(sl, { fy: "sub", y: "serie", x: "v", fill: "serie", insetTop: 0.5, insetBottom: 0.5, tip: true, title: d => `${d.sub}, ${d.serie}\n${money(d.v)}` }),
        Plot.ruleX([0], { stroke: K.ink3 }),
      ],
    }, box),
    table: [["Subcategoría", "Hoy ($)", "Con topes ($)", "Diferencia ($)"], subs.map(r => [r.sub, int(r.p), int(r.p2), int(r.p2 - r.p)])],
  });
}

// ------------------------------------------------------------------ 03 modelo
const MNAME = { "Regla descuento > 20%": "Regla actual, >20%", "Regresion logistica": "Regresión logística", "Arbol de decision": "Árbol de decisión",
  "Random forest": "Random forest", "Gradient boosting": "Gradient boosting", "Regla costo histórico": "Regla con costo, sin ML" };
function renderC3() {
  const I = rows({ only2017: true });
  const losses = I.filter(i => C.p[i] < 0);
  const byRule = losses.filter(i => C.d[i] > 20).length, byModel = losses.filter(i => C.pred[i] === 1).length;
  const L20 = losses.filter(i => C.d[i] === 20), m20 = L20.filter(i => C.pred[i] === 1).length;
  $("#h3").textContent = losses.length
    ? `El modelo detecta ${int(byModel)} de ${int(losses.length)} pérdidas de 2017 y la regla actual ${int(byRule)}${L20.length ? `. En 20% de descuento, ${m20} contra 0` : ""}`
    : "No hay líneas con pérdida en este corte de 2017";
  $("#x3").textContent = `Solo 2017, el año de prueba que el modelo nunca vio${filterText()}${S.p !== "2017" ? ". El filtro de periodo no aplica a este capítulo" : ""}. El modelo no usa utilidad, margen ni costo.`;

  const mods = D.modelos.filter(m => MNAME[m.nombre]).map(m => ({ ...m, n: MNAME[m.nombre] })).sort((a, b) => a.f1 - b.f1);
  const fillM = m => m.nombre === D.meta.modelo_elegido ? K.b : m.nombre.startsWith("Regla descuento") ? K.a : K.ctx;
  chart($("#f-mod"), {
    title: "F1 en la prueba de 2017",
    note: `Gradient boosting se eligió por validación, sin ver 2017. Intervalo de 95%, ${nf(3).format(D.ic95.modelo[0])} a ${nf(3).format(D.ic95.modelo[1])} contra ${nf(3).format(D.ic95.regla[0])} a ${nf(3).format(D.ic95.regla[1])} de la regla.`,
    legend: [["Regla actual", K.a], ["Modelo elegido", K.b], ["Otros", K.ctx]],
    plot: box => P({
      height: 250, marginLeft: 150, marginRight: 44,
      y: { label: null, domain: mods.map(m => m.n) },
      x: { label: null, domain: [0.7, 1], ticks: 4, ...grid },
      marks: [
        Plot.barX(mods, { y: "n", x1: 0.7, x2: "f1", fill: fillM, insetTop: 4, insetBottom: 4, tip: true,
          title: m => `${m.n}\nF1 ${nf(3).format(m.f1)} · PR-AUC ${nf(3).format(m.pr_auc)}\nPrecisión ${nf(3).format(m.precision)} · Recall ${nf(3).format(m.recall)}` }),
        Plot.text(mods, { y: "n", x: "f1", text: m => nf(3).format(m.f1), dx: 6, textAnchor: "start", fill: K.ink2 }),
      ],
    }, box),
    table: [["Modelo", "PR-AUC", "F1", "Precisión", "Recall"], mods.slice().reverse().map(m => [m.n, nf(3).format(m.pr_auc), nf(3).format(m.f1), nf(3).format(m.precision), nf(3).format(m.recall)])],
  });

  const lv = [...groupBy(losses, i => C.d[i])].sort((a, b) => a[0] - b[0]).map(([d, J]) => ({
    lv: d + "%", total: J.length, regla: J.filter(i => C.d[i] > 20).length, modelo: J.filter(i => C.pred[i] === 1).length }));
  const dd = lv.flatMap(r => [{ lv: r.lv, serie: "Pérdidas reales", v: r.total }, { lv: r.lv, serie: "Regla actual", v: r.regla }, { lv: r.lv, serie: "Modelo", v: r.modelo }]);
  chart($("#f-det"), {
    title: "Pérdidas detectadas según el descuento",
    note: "Cuántas líneas con pérdida marca cada método antes de vender.",
    legend: [["Pérdidas reales", K.ctx], ["Regla actual", K.a], ["Modelo", K.b]],
    plot: box => P({
      height: 250, marginLeft: 44,
      fx: { label: "Descuento", padding: 0.15 },
      x: { axis: null, domain: ["Pérdidas reales", "Regla actual", "Modelo"] },
      y: { label: "Líneas", ticks: 5, ...grid },
      color: { domain: ["Pérdidas reales", "Regla actual", "Modelo"], range: [K.ctx, K.a, K.b] },
      marks: [
        Plot.ruleY([0], { stroke: K.ink3 }),
        Plot.barY(dd, { fx: "lv", x: "serie", y: "v", fill: "serie", insetLeft: 1, insetRight: 1, tip: true, title: d => `${d.serie}, descuento ${d.lv}\n${int(d.v)} líneas` }),
      ],
    }, box),
    table: [["Descuento", "Pérdidas", "Regla actual", "Modelo"], lv.map(r => [r.lv, int(r.total), int(r.regla), int(r.modelo)])],
  });

  // semáforo con el filtro: líneas y monto perdido por color
  const semRows = [1, 2, 3].map(k => { const J = I.filter(i => C.sem[i] === k); return { k, sem: SEM[k], n: J.length, loss: sum(J, i => Math.max(0, -C.p[i])) }; });
  const tn = I.length || 1, tl = semRows.reduce((t, r) => t + r.loss, 0) || 1;
  const sd = semRows.flatMap(r => [{ row: "Líneas", sem: r.sem, v: r.n / tn, raw: int(r.n) + " líneas" }, { row: "Monto perdido", sem: r.sem, v: r.loss / tl, raw: money(r.loss) }]);
  const rev = (semRows[0].n + semRows[1].n) / tn, revL = (semRows[0].loss + semRows[1].loss) / tl;
  chart($("#f-sem"), {
    title: `Semáforo: ${pct(rev, 0)} de las líneas va a revisión humana y ahí está ${pct(revL)} del monto perdido`,
    note: "Rojo, el descuento pasa el tope. Amarillo, dentro del tope pero el modelo ve riesgo. Verde, sin alerta. En rojo y amarillo decide el gerente comercial.",
    legend: [["Rojo", K.sr], ["Amarillo", K.sy], ["Verde", K.sg]],
    plot: box => P({
      height: 110, marginLeft: 110, marginBottom: 24,
      y: { label: null, domain: ["Líneas", "Monto perdido"] },
      x: { axis: null, domain: [0, 1] },
      color: { domain: ["Rojo", "Amarillo", "Verde"], range: [K.sr, K.sy, K.sg] },
      marks: [
        Plot.barX(sd, Plot.stackX({ y: "row", x: "v", fill: "sem", order: ["Rojo", "Amarillo", "Verde"], insetTop: 6, insetBottom: 6, tip: true, title: d => `${d.sem}, ${d.row}\n${pct(d.v)} · ${d.raw}` })),
        Plot.text(sd.filter(d => d.v > 0.06), Plot.stackX({ y: "row", x: "v", z: "sem", order: ["Rojo", "Amarillo", "Verde"], text: d => pct(d.v, 0), fill: "#111", fontWeight: 700 })),
      ],
    }, box),
    table: [["Semáforo", "Líneas", "Monto perdido ($)"], semRows.map(r => [r.sem, int(r.n), int(r.loss)])],
  });
}

// ------------------------------------------------------------------ 04 topes
function renderC4(I, A) {
  const tps = D.topes.filter(t => S.c < 0 || t.cat === DIM.category[S.c]).sort((a, b) => (b.actual - b.tope) - (a.actual - a.tope));
  const bySub = [...groupBy(I, i => C.sb[i])].map(([k, J]) => ({ sub: DIM.sub[k], d: sum(J, i => P2(i) - C.p[i]) })).sort((a, b) => b.d - a.d);
  $("#h4").textContent = A.aff
    ? `Bajar el descuento al tope en ${int(A.aff)} líneas suma ${money(A.p2 - A.p)}, y ${bySub[0].sub} aporta la mayor parte`
    : "En este corte ninguna línea supera su tope";
  $("#x4").textContent = "El tope es el descuento máximo por subcategoría. Se fijó con 2014 a 2016, como el más conservador entre el costo de los productos y el modelo. Volumen constante.";

  const pts = tps.flatMap(t => [showA() && { sub: t.sub, serie: "Hoy", v: t.actual, t }, showB() && { sub: t.sub, serie: "Con topes", v: Math.min(t.actual, t.tope), t }]).filter(Boolean);
  chart($("#f-topes"), {
    title: "Descuento promedio de hoy contra el tope",
    note: "Ordenadas por la distancia. La línea fina llega al descuento máximo que se ha dado.",
    legend: [...legendEnt(), ["Descuento máximo", K.ctx]],
    plot: box => P({
      height: Math.max(220, tps.length * 24 + 40), marginLeft: 92, marginRight: 24,
      y: { label: null, domain: tps.map(t => t.sub) },
      x: { label: null, tickFormat: v => pct(v, 0), domain: [0, 0.82], ticks: 5, ...grid },
      color: entScale(),
      marks: [
        Plot.ruleY(tps, { y: "sub", x1: 0, x2: "max", stroke: K.ctx, strokeWidth: 1 }),
        Plot.ruleY(tps, { y: "sub", x1: d => Math.min(d.tope, d.actual), x2: "actual", stroke: K.ink3, strokeWidth: 2 }),
        Plot.dot(pts, { y: "sub", x: "v", fill: "serie", r: 5.5, stroke: K.page, strokeWidth: 1.5, tip: true,
          title: d => `${d.sub}\nPromedio hoy ${pct(d.t.actual)} · tope ${pct(d.t.tope, 0)}\nMáximo dado ${pct(d.t.max, 0)} · pierde hoy ${pct(d.t.perdida_hist, 0)} de sus líneas` }),
      ],
    }, box),
    table: [["Subcategoría", "Promedio hoy", "Máximo", "Tope", "Líneas que pierden"], tps.map(t => [t.sub, pct(t.actual), pct(t.max, 0), pct(t.tope, 0), pct(t.perdida_hist, 0)])],
  });

  const base = D.decision.opciones[0].utilidad_2017;
  const sc = D.escenarios.map(e => ({ lbl: pct(e.perdida_volumen, 0), v: e.utilidad }));
  chart($("#f-vol"), {
    title: "¿Y si se pierden ventas por quitar descuento?",
    note: "Utilidad de 2017 con topes en todo el país, perdiendo una parte del volumen de las líneas con tope. La línea es hoy.",
    plot: box => P({
      height: 200, marginLeft: 56, marginBottom: 36, marginRight: 64,
      x: { label: "Volumen perdido en las líneas con tope", domain: sc.map(d => d.lbl), padding: 0.3 },
      y: { label: "Utilidad 2017", tickFormat: moneyK, ticks: 4, ...grid },
      marks: [
        Plot.barY(sc, { x: "lbl", y: "v", fill: K.b, tip: true, title: d => `Volumen perdido ${d.lbl}\nUtilidad ${money(d.v)}` }),
        Plot.ruleY([base], { stroke: K.ink, strokeWidth: 2, strokeDasharray: "4,3" }),
        Plot.text([base], { y: d => d, frameAnchor: "right", textAnchor: "start", dx: 6, text: () => "Hoy " + moneyK(base), fill: K.ink, fontWeight: 600 }),
        Plot.ruleY([0], { stroke: K.ink3 }),
      ],
    }, box),
    table: [["Volumen perdido", "Utilidad 2017 ($)"], sc.map(d => [d.lbl, int(d.v)])],
  });
  $("#opciones").innerHTML = D.decision.opciones.map(o => {
    const rec = o.opcion.startsWith(D.decision.recomendada);
    return `<div class="card ${rec ? "hl" : ""}"><h4>${o.opcion}${rec ? ' <span class="tb">· recomendada</span>' : ""}</h4><div class="big">${money(o.utilidad_2017)}</div><p>${o.riesgo}</p></div>`;
  }).join("");
}

// ------------------------------------------------------------------ 05 entregas
function renderC5(I) {
  const O = I.filter(i => C.o1[i] === 1);
  const modes = DIM.ship.map((name, k) => {
    const J = O.filter(i => C.sm[i] === k), prom = D.promesa[name], p95 = D.p95[name];
    const dist = new Map(); for (const i of J) dist.set(C.dts[i], (dist.get(C.dts[i]) || 0) + 1);
    return { name, n: J.length, prom, p95, ok: J.filter(i => C.dts[i] <= prom).length / J.length, ok95: J.filter(i => C.dts[i] <= p95).length / J.length, dist };
  }).filter(m => m.n);
  const tot = modes.reduce((t, m) => t + m.n, 0);
  const ok = modes.reduce((t, m) => t + m.ok * m.n, 0) / tot, ok95 = modes.reduce((t, m) => t + m.ok95 * m.n, 0) / tot;
  const aucs = D.auc_entregas;
  $("#h5").textContent = tot
    ? `Con la promesa actual llega a tiempo ${pct(ok, 0)} de los pedidos, publicando el percentil 95 llegaría ${pct(ok95, 0)}`
    : "Sin pedidos en este corte";
  $("#x5").textContent = `${int(tot)} pedidos de ${periodLabel()}${filterText()}. El retraso no se puede predecir (AUC de ${nf(2).format(Math.min(...aucs))} a ${nf(2).format(Math.max(...aucs))}), así que se ajusta lo que se promete, no el modelo.`;

  const ser = ["Promesa actual", "Promesa al p95"];
  const pd = modes.flatMap(m => [{ mode: m.name, serie: ser[0], v: m.ok, d: m.prom }, { mode: m.name, serie: ser[1], v: m.ok95, d: m.p95 }]);
  chart($("#f-prom"), {
    title: "Pedidos a tiempo por modalidad",
    note: "La línea vertical es la meta de 95%.",
    legend: [[ser[0], K.a], [ser[1], K.b]],
    plot: box => P({
      height: 260, marginLeft: 108, marginRight: 44,
      fy: { label: null, domain: DIM.ship, padding: 0.18 },
      y: { axis: null, domain: ser },
      x: { label: null, domain: [0, 1], tickFormat: v => pct(v, 0), ticks: 5, ...grid },
      color: { domain: ser, range: [K.a, K.b] },
      marks: [
        Plot.barX(pd, { fy: "mode", y: "serie", x: "v", fill: "serie", insetTop: 1, insetBottom: 1, tip: true, title: d => `${d.mode}, ${d.serie} (${d.d} días)\n${pct(d.v)} a tiempo` }),
        Plot.text(pd, { fy: "mode", y: "serie", x: "v", text: d => pct(d.v, 0), dx: 5, textAnchor: "start", fill: K.ink2, fontSize: 11 }),
        Plot.ruleX([0.95], { stroke: K.ink, strokeDasharray: "3,3" }),
      ],
    }, box),
    table: [["Modalidad", "Pedidos", "Promesa actual (días)", "A tiempo", "Promesa p95 (días)", "A tiempo"], modes.map(m => [m.name, int(m.n), m.prom, pct(m.ok), m.p95, pct(m.ok95)])],
  });

  const cells = modes.flatMap(m => d3.range(0, 8).map(d => ({ mode: m.name, d, v: (m.dist.get(d) || 0) / m.n, prom: m.prom, p95: m.p95 })));
  chart($("#f-dias"), {
    title: "Días de envío por modalidad",
    note: "Porcentaje de pedidos de cada modalidad. El marco gris es la promesa actual y el amarillo la del percentil 95.",
    plot: box => P({
      height: 260, marginLeft: 108, marginBottom: 36,
      x: { label: "Días entre pedido y envío", domain: d3.range(0, 8), tickSize: 0 },
      y: { label: null, domain: modes.map(m => m.name), tickSize: 0 },
      color: { type: "linear", domain: [0, 1], range: [K.cell0, K.a], legend: false },
      marks: [
        Plot.cell(cells, { x: "d", y: "mode", fill: "v", inset: 1.5, rx: 3, tip: true, title: c => `${c.mode}, ${c.d} días\n${pct(c.v)} de los pedidos` }),
        Plot.cell(cells.filter(c => c.d === c.prom), { x: "d", y: "mode", stroke: K.ink2, strokeWidth: 2, inset: 1, rx: 3, fill: "none" }),
        Plot.cell(cells.filter(c => c.d === c.p95), { x: "d", y: "mode", stroke: K.b, strokeWidth: 2, inset: 3.5, rx: 2, fill: "none" }),
        Plot.text(cells.filter(c => c.v >= 0.005), { x: "d", y: "mode", text: c => pct(c.v, 0), fill: c => c.v > 0.5 ? K.page : K.ink, fontSize: 11 }),
      ],
    }, box),
    table: [["Modalidad", ...d3.range(0, 8).map(d => d + " días")], modes.map(m => [m.name, ...d3.range(0, 8).map(d => pct((m.dist.get(d) || 0) / m.n, 0))])],
  });
}

// ------------------------------------------------------------------ 06 clientes
const ACCION = { "Alto valor rentable": "Proteger. Servicio y sin descuento extra.", "Cazadores de descuento": "Corregir. Aquí se aplican los topes primero.",
  "Inactivos": "Reactivar con campaña, sin descuento alto.", "Compradores ocasionales": "Crecer la frecuencia de compra." };
function renderC6(I) {
  const tc = new Set(I.map(i => C.cu[i])).size || 1, ts = sum(I, i => C.s[i]) || 1, tl = sum(I, i => Math.max(0, -C.p[i])) || 1;
  const gs = DIM.cluster.map((name, k) => {
    const J = I.filter(i => C.cl[i] === k);
    return { name, cli: new Set(J.map(i => C.cu[i])).size / tc, s: sum(J, i => C.s[i]) / ts, l: sum(J, i => Math.max(0, -C.p[i])) / tl,
      p: sum(J, i => C.p[i]), p2: sum(J, P2), d: J.length ? sum(J, i => C.d[i]) / 100 / J.length : 0 };
  });
  const cz = gs.find(g => g.name === "Cazadores de descuento");
  $("#h6").textContent = `Cazadores de descuento son ${pct(cz.cli, 0)} de los clientes y generan ${pct(cz.l, 0)} del monto perdido`;
  $("#x6").textContent = `Cuatro grupos de K-Means según recencia, frecuencia, monto, margen y descuento. Clientes con compras en ${periodLabel()}${filterText()}.`;
  const order = gs.slice().sort((a, b) => a.p - b.p).map(g => g.name);
  const gl = gs.flatMap(g => [showA() && { g: g.name, serie: "Hoy", v: g.p }, showB() && { g: g.name, serie: "Con topes", v: g.p2 }]).filter(Boolean);
  chart($("#f-grp"), {
    title: "Utilidad por grupo de clientes",
    note: "Los topes cambian sobre todo al grupo que vive del descuento.",
    legend: legendEnt(),
    plot: box => P({
      height: 260, marginLeft: 160, marginRight: 70,
      fy: { label: null, domain: order, padding: 0.2 },
      y: { axis: null, domain: SERIES() },
      x: { label: null, tickFormat: moneyK, ticks: 4, insetLeft: 52, ...grid },
      color: entScale(),
      marks: [
        Plot.barX(gl, { fy: "g", y: "serie", x: "v", fill: "serie", insetTop: 1, insetBottom: 1, tip: true, title: d => `${d.g}, ${d.serie}\n${money(d.v)}` }),
        Plot.text(gl.filter(d => d.v >= 0), { fy: "g", y: "serie", x: "v", text: d => moneyK(d.v), dx: 5, textAnchor: "start", fill: K.ink2, fontSize: 11 }),
        Plot.text(gl.filter(d => d.v < 0), { fy: "g", y: "serie", x: "v", text: d => moneyK(d.v), dx: -5, textAnchor: "end", fill: K.ink2, fontSize: 11 }),
        Plot.ruleX([0], { stroke: K.ink3 }),
      ],
    }, box),
    table: [["Grupo", "Clientes", "Ventas", "Monto perdido", "Hoy ($)", "Con topes ($)"], gs.map(g => [g.name, pct(g.cli, 0), pct(g.s, 0), pct(g.l, 0), int(g.p), int(g.p2)])],
  });
  $("#grupos").innerHTML = gs.map(g => `<div class="card ${g.name === "Cazadores de descuento" ? "hl" : ""}"><h4>${g.name}</h4>
    <p class="num">${pct(g.cli, 0)} de clientes · ${pct(g.s, 0)} de ventas · <span class="tn">${pct(g.l, 0)} del monto perdido</span> · descuento ${pct(g.d, 0)}</p>
    <p>${ACCION[g.name] || ""}</p></div>`).join("");
}

// ------------------------------------------------------------------ controles
function fillControls() {
  $("#f-rg").innerHTML = `<option value="-1">Regiones</option>` + DIM.region.map((r, k) => `<option value="${k}">${r}</option>`).join("");
  $("#f-ca").innerHTML = `<option value="-1">Categorías</option>` + DIM.category.map((r, k) => `<option value="${k}">${r}</option>`).join("");
  $("#states").innerHTML = DIM.state.map(s => `<option value="${s}">`).join("");
  $("#toc").innerHTML = [...document.querySelectorAll("main section")].map((s, k) => `<a href="#${s.id}" data-sec="${s.id}"><b>0${k}</b>${s.dataset.name}</a>`).join("");
  $("#toc").addEventListener("click", ev => { const a = ev.target.closest("a"); if (!a) return; ev.preventDefault(); document.getElementById(a.dataset.sec).scrollIntoView({ behavior: "smooth" }); });
  $("#f-per").onchange = e => { S.p = e.target.value; update(); };
  $("#f-rg").onchange = e => { S.r = +e.target.value; update(); };
  $("#f-ca").onchange = e => { S.c = +e.target.value; update(); };
  $("#f-st").onchange = e => { const k = DIM.state.indexOf(e.target.value); if (k >= 0) { S.s = k; update(); } };
  $("#f-st-x").onclick = () => { S.s = -1; update(); };
  document.querySelectorAll("[data-ent]").forEach(b => b.onclick = () => { S.e = b.dataset.ent; update(); });
  document.querySelectorAll("[data-pol]").forEach(b => b.onclick = () => { S.pol = b.dataset.pol; update(); });
  $("#theme").onclick = () => { S.th = S.th === "dark" ? "light" : "dark"; update(); };
  const io = new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting) document.querySelectorAll("#toc a").forEach(a => a.classList.toggle("on", a.dataset.sec === e.target.id));
  }), { rootMargin: "-40% 0px -55% 0px" });
  document.querySelectorAll("main section").forEach(s => io.observe(s));
  let t; addEventListener("resize", () => { clearTimeout(t); t = setTimeout(render, 200); });
}
function syncControls() {
  document.documentElement.dataset.theme = S.th;
  $("#theme").textContent = S.th === "dark" ? "Claro" : "Oscuro";
  $("#f-per").value = S.p; $("#f-rg").value = S.r; $("#f-ca").value = S.c;
  $("#f-st").value = S.s >= 0 ? DIM.state[S.s] : "";
  $("#f-st-x").hidden = S.s < 0;
  document.querySelectorAll("[data-ent]").forEach(b => b.setAttribute("aria-pressed", b.dataset.ent === S.e));
  document.querySelectorAll("[data-pol]").forEach(b => b.setAttribute("aria-pressed", b.dataset.pol === S.pol));
  $("#printfilters").textContent = `Filtros: ${periodLabel()}${filterText() || ", todo el país"}. Topes en ${polLabel()}.`;
}

function render() {
  K = COL();
  const I = rows(), A = agg(I);
  renderHero(A); renderC0(I, A); renderC1(I, A); renderC2(I); renderC3(); renderC4(I, A); renderC5(I); renderC6(I);
}
function update() { writeHash(); syncControls(); render(); }

// ------------------------------------------------------------------ arranque
readHash();
if (S.only) {
  document.documentElement.classList.add("only");
  const sec = document.getElementById(S.only); if (sec) sec.classList.add("shown");
}
$("#gen").textContent = D.meta.generado;
$("#in-n").textContent = int(D.meta.lineas);
fillControls();
syncControls();
render();
window.ROLU = { S, D, agg, rows, update };
