/* Final al llegar al fondo: explosión, cinco hallazgos y pantalla de gracias.
   Los hallazgos se editan aquí. Las cifras se leen de data.js para que no se desfasen. */
(() => {
  const D = window.DATA;
  const nf = (v, d = 0) => new Intl.NumberFormat("es-MX", { minimumFractionDigits: d, maximumFractionDigits: d }).format(v);
  const money = v => "$" + nf(Math.round(v));
  const pct = v => nf(v * 100) + "%";
  const mod = n => D.modelos.find(m => m.nombre === n);
  const cz = D.grupos.find(g => g.nombre === "Cazadores de descuento");

  const TITULO = "Cinco cosas que nos llevamos";
  const HALLAZGOS = [
    { t: "Topes, no más ventas", p: `Con topes la utilidad de 2017 pasa de ${money(D.decision.opciones[0].utilidad_2017)} a ${money(D.escenarios[0].utilidad)} sin vender una pieza más.` },
    { t: "El descuento no compra volumen", p: `Correlación de ${nf(D.h2_rho, 3)} entre descuento y unidades. Quitarlo donde pierde casi no cuesta ventas.` },
    { t: "El modelo ve lo que la regla no", p: `F1 de ${nf(mod(D.meta.modelo_elegido).f1, 3)} contra ${nf(mod("Regla descuento > 20%").f1, 3)}. En 20% de descuento detecta ${D.descuento_20.modelo_detecta} de ${D.descuento_20.perdidas} pérdidas y la regla ninguna.` },
    { t: "Un grupo concentra el problema", p: `Cazadores de descuento son ${pct(cz.clientes_pct)} de los clientes y ${pct(cz.perdidas_pct)} del monto perdido.` },
    { t: "Prometer lo que se cumple", p: "El retraso no se puede predecir. Publicando el percentil 95 de cada modalidad, se cumple arriba de 95%." },
  ];
  const CIERRE = "Recomendación, opción C. Topes en 10 estados en dos olas. El modelo propone, decide una persona.";

  const html = document.documentElement;
  const finale = document.getElementById("finale");
  const thanks = document.getElementById("thanks");
  const canvas = document.getElementById("boom");
  const main = document.querySelector("main");
  const capture = /(^|[#&])only=/.test(location.hash) || navigator.webdriver;
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;
  if (capture) return;

  finale.innerHTML = `<div class="fin-box">
      <div class="kicker">Rolulabo · Hallazgos</div>
      <h2 id="fin-t">${TITULO}</h2>
      <div class="fin-grid">${HALLAZGOS.map((h, k) => `<article><div class="n">0${k + 1}</div><h3>${h.t}</h3><p>${h.p}</p></article>`).join("")}</div>
      <p style="margin-top:32px;font-size:18px;color:#f3f1ea;font-weight:600">${CIERRE}</p>
      <div class="fin-btns"><button class="fill" id="fin-ty">Gracias por su atención</button><button class="line" id="fin-back">Volver</button></div>
    </div>`;
  const word = "¡Gracias!";
  thanks.innerHTML = `<div class="ty"><div class="glow"></div><div class="ring"></div>
      <h2>${[...word].map((c, k) => `<span class="${k > 0 && k < word.length - 1 ? "" : "y"}" style="animation-delay:${k * 0.08}s, ${0.8 + k * 0.12}s">${c}</span>`).join("")}</h2>
      <p>Gabriel · Eduardo · Emiliano · Rodrigo</p></div>`;

  let armed = true, open = false;

  function explode(done) {
    if (reduced) return done();
    const SC = 6, w = Math.ceil(innerWidth / SC), h = Math.ceil(innerHeight / SC);
    canvas.width = w; canvas.height = h; canvas.style.display = "block";
    const ctx = canvas.getContext("2d");
    const pal = ["#f5c400", "#f5c400", "#f3f1ea", "#8f8a7f", "#ef5b5b", "#ffe680"];
    const cx = w / 2, cy = h * 0.55;
    const parts = Array.from({ length: 260 }, () => {
      const a = Math.random() * Math.PI * 2, v = 0.6 + Math.random() * 3.2;
      return { x: cx, y: cy, vx: Math.cos(a) * v, vy: Math.sin(a) * v - 1.2, life: 40 + Math.random() * 40, c: pal[(Math.random() * pal.length) | 0], s: Math.random() < 0.3 ? 2 : 1 };
    });
    let f = 0;
    (function frame() {
      ctx.clearRect(0, 0, w, h);
      if (f < 14) { ctx.fillStyle = `rgba(245,196,0,${0.35 * (1 - f / 14)})`; ctx.fillRect(0, 0, w, h); }
      const r = f * 4.5;
      if (f < 26) { ctx.strokeStyle = `rgba(243,241,234,${1 - f / 26})`; ctx.lineWidth = 2; ctx.beginPath(); ctx.arc(cx, cy, r, 0, Math.PI * 2); ctx.stroke(); }
      for (const p of parts) {
        if (p.life <= 0) continue;
        p.x += p.vx; p.y += p.vy; p.vy += 0.06; p.vx *= 0.985; p.life--;
        ctx.globalAlpha = Math.min(1, p.life / 20); ctx.fillStyle = p.c; ctx.fillRect(p.x | 0, p.y | 0, p.s, p.s);
      }
      ctx.globalAlpha = 1;
      main.style.transform = f < 30 ? `translate(${(Math.random() - 0.5) * (30 - f) * 0.6}px, ${(Math.random() - 0.5) * (30 - f) * 0.6}px)` : "";
      f++;
      if (f === 34) done();
      if (f < 80) requestAnimationFrame(frame); else { canvas.style.display = "none"; main.style.transform = ""; }
    })();
  }

  function showFinale() {
    open = true; armed = false;
    explode(() => {
      finale.classList.add("on");
      html.classList.add("locked");
      document.getElementById("fin-ty").focus();
    });
  }
  function closeFinale() {
    finale.classList.remove("on"); thanks.classList.remove("on");
    html.classList.remove("locked");
    open = false;
    scrollBy({ top: -Math.min(500, innerHeight * 0.6), behavior: "smooth" });
  }
  function showThanks() {
    finale.classList.remove("on");
    thanks.classList.add("on");
    const ty = thanks.querySelector(".ty");
    ty.querySelectorAll(".confetti").forEach(c => c.remove());
    // reinicia las animaciones de las letras
    ty.querySelectorAll("h2 span").forEach(s => { s.style.animation = "none"; void s.offsetWidth; s.style.animation = ""; });
    if (!reduced) {
      const pal = ["#f5c400", "#f3f1ea", "#8f8a7f", "#ffe680", "#ef5b5b"];
      for (let k = 0; k < 140; k++) {
        const c = document.createElement("i");
        c.className = "confetti";
        c.style.left = Math.random() * 100 + "vw";
        c.style.background = pal[k % pal.length];
        c.style.animationDuration = 2.6 + Math.random() * 3 + "s";
        c.style.animationDelay = Math.random() * 1.6 + "s";
        c.style.transform = `rotate(${Math.random() * 360}deg)`;
        ty.append(c);
      }
    }
  }
  document.getElementById("fin-back").onclick = closeFinale;
  document.getElementById("fin-ty").onclick = showThanks;
  thanks.onclick = closeFinale;
  addEventListener("keydown", e => { if (open && e.key === "Escape") closeFinale(); });

  // atajo para ensayar: #fin=1 abre los hallazgos directo, #fin=2 la pantalla de gracias
  const fin = (location.hash.match(/(^|[#&])fin=(\d)/) || [])[2];
  if (fin) { armed = false; open = true; finale.classList.add("on"); html.classList.add("locked"); if (fin === "2") showThanks(); }

  new IntersectionObserver(es => es.forEach(e => {
    if (e.isIntersecting && armed && !open && window.INTRO_DONE && scrollY > 400) showFinale();
    if (!e.isIntersecting && !open) armed = true;
  })).observe(document.getElementById("sentinel"));
})();
