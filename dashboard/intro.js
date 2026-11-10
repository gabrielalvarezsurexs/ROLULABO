/* Pantalla de entrada. No aparece en modo captura (#only=, #nointro o navegador automatizado). */
(() => {
  history.scrollRestoration = "manual";
  const intro = document.getElementById("intro");
  const html = document.documentElement;
  const capture = /(^|[#&])(only|nointro)=/.test(location.hash) || navigator.webdriver;
  if (capture) { intro.remove(); window.INTRO_DONE = true; return; }

  scrollTo(0, 0);
  intro.hidden = false;
  html.classList.add("locked");
  const go = document.getElementById("go");
  go.focus({ preventScroll: true });
  const reduced = matchMedia("(prefers-reduced-motion: reduce)").matches;

  let closing = false;
  function close() {
    if (closing) return;
    closing = true;
    if (!reduced) {
      intro.classList.add("flash");
      intro.querySelector(".in-box").classList.add("shake");
    }
    setTimeout(() => intro.classList.add("out"), reduced ? 0 : 320);
    setTimeout(() => {
      intro.remove();
      html.classList.remove("locked");
      scrollTo(0, 0);
      window.INTRO_DONE = true;
    }, reduced ? 50 : 780);
  }
  go.addEventListener("click", close);
  addEventListener("keydown", e => { if (!closing && e.key === "Escape") close(); });
})();
