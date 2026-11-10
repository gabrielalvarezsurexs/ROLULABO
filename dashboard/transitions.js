/* Impacto visual al avanzar: portada por capítulo con número gigante y titular enorme, cintas amarillas
   entre capítulos, cada capítulo entra distinto, gráficas que se dibujan y barra de progreso.
   No corre en modo captura (#only=) ni con movimiento reducido. #go=c3 salta a un capítulo. */
(() => {
  const html = document.documentElement;
  if (/(^|[#&])only=/.test(location.hash) || navigator.webdriver || matchMedia("(prefers-reduced-motion: reduce)").matches) return;
  const FX = ["rise", "slide", "zoom", "tilt", "wipe", "blur", "drop"];
  const secs = [...document.querySelectorAll("main section")];
  const marqs = [];

  // cifras del titular en amarillo, también cuando un filtro lo reescribe
  const hl = h => {
    if (h.querySelector("em")) return;
    h.innerHTML = h.textContent.replace(/-?\$[\d,.]*\d(?: mil| M)?|\d[\d,.]*%?/g, m => (/^20\d\d$/.test(m) ? m : `<em>${m}</em>`));
  };

  secs.forEach((s, k) => {
    s.dataset.fx = FX[k % FX.length];
    const head = [...s.querySelectorAll(":scope > .ch-num, :scope > h2, :scope > .ctx")];
    const op = Object.assign(document.createElement("div"), { className: "opener" });
    op.dataset.n = "0" + k;
    s.prepend(op); op.append(...head);
    [...head, ...s.querySelectorAll(":scope > .grid > *")].forEach((e, i) => { e.dataset.r = i % 2 ? "b" : "a"; e.style.setProperty("--i", i); });
    const h2 = op.querySelector("h2");
    hl(h2); new MutationObserver(() => hl(h2)).observe(h2, { childList: true });
    if (k) {
      const m = Object.assign(document.createElement("div"), { className: "marq" });
      m.setAttribute("aria-hidden", "true");
      m.innerHTML = `<span>${(`0${k} ${s.dataset.name} · `).repeat(14)}</span>`;
      s.before(m); marqs.push(m);
    }
  });
  const h1 = document.querySelector(".hero h1");
  h1.innerHTML = h1.textContent.replace(/(más utilidad\.)/, "<em>$1</em>");
  html.classList.add("fx");

  const io = new IntersectionObserver(es => es.forEach(e => e.target.classList.toggle("in", e.isIntersecting)),
    { rootMargin: "-18% 0px -18% 0px" });
  secs.forEach(s => io.observe(s));

  const bar = document.body.appendChild(Object.assign(document.createElement("div"), { id: "prog" }));
  let tick = false;
  const onScroll = () => {
    if (tick) return; tick = true;
    requestAnimationFrame(() => {
      tick = false;
      bar.style.transform = `scaleX(${scrollY / Math.max(1, document.body.scrollHeight - innerHeight)})`;
      for (const s of [...secs, ...marqs]) {
        const r = s.getBoundingClientRect();
        if (r.bottom > 0 && r.top < innerHeight) s.style.setProperty("--p", ((innerHeight - r.top) / (innerHeight + r.height)).toFixed(3));
      }
    });
  };
  addEventListener("scroll", onScroll, { passive: true });
  const go = (location.hash.match(/(^|[#&])go=(c\d)/) || [])[2];
  if (go) document.getElementById(go)?.scrollIntoView();
  onScroll();
})();

/* Extras: portadas amarillas alternadas, cursor que invierte colores y tarjetas que se inclinan con el mouse. */
(() => {
  const html = document.documentElement;
  if (!html.classList.contains("fx")) return;
  document.querySelectorAll(".opener").forEach((o, k) => { if (k % 2) { o.classList.add("inv"); o.parentElement.previousElementSibling?.classList.add("alt"); } });
  if (!matchMedia("(pointer: fine)").matches) return;
  const cur = document.body.appendChild(Object.assign(document.createElement("div"), { id: "cur" }));
  let x = innerWidth / 2, y = innerHeight / 2, tx = x, ty = y, big = 1, tb = 1;
  addEventListener("mousemove", e => {
    tx = e.clientX; ty = e.clientY;
    tb = e.target.closest("button, a, select, input, summary, .map rect") ? 3.2 : e.target.closest("figure, .profile, .card, #versus") ? 1.8 : 1;
    const c = e.target.closest(".profile, .insights li, .card");
    document.querySelectorAll(".tilted").forEach(t => { if (t !== c) { t.style.transform = ""; t.classList.remove("tilted"); } });
    if (c) {
      const r = c.getBoundingClientRect();
      c.classList.add("tilted");
      c.style.transform = `perspective(900px) rotateY(${((e.clientX - r.left) / r.width - 0.5) * 7}deg) rotateX(${(0.5 - (e.clientY - r.top) / r.height) * 7}deg) translateY(-3px)`;
    }
  });
  (function loop() {
    x += (tx - x) * 0.18; y += (ty - y) * 0.18; big += (tb - big) * 0.15;
    cur.style.transform = `translate(${x - 9}px, ${y - 9}px) scale(${big.toFixed(3)})`;
    requestAnimationFrame(loop);
  })();
})();
