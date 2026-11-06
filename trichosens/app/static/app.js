// Petites animations communes : apparition des blocs au défilement.
(function () {
  "use strict";
  const els = document.querySelectorAll(".reveal");
  if (!("IntersectionObserver" in window) || matchMedia("(prefers-reduced-motion: reduce)").matches) {
    els.forEach((el) => el.classList.add("visible"));
    return;
  }
  const io = new IntersectionObserver((entries) => {
    entries.forEach((e) => {
      if (e.isIntersecting) {
        e.target.classList.add("visible");
        io.unobserve(e.target);
      }
    });
  }, { threshold: 0.12 });
  els.forEach((el) => io.observe(el));
})();

// Carrousel de l'accueil : défilement automatique, glissement au doigt, points de navigation.
(function () {
  "use strict";
  document.querySelectorAll("[data-carousel]").forEach((root) => {
    const track = root.querySelector(".carousel-track");
    const slides = Array.from(track.children);
    const dots = Array.from(root.querySelectorAll(".carousel-dots button"));
    if (slides.length < 2) return;
    let index = 0;
    let timer = null;
    const reduce = matchMedia("(prefers-reduced-motion: reduce)").matches;

    function go(i, smooth = true) {
      index = (i + slides.length) % slides.length;
      track.scrollTo({ left: slides[index].offsetLeft, behavior: smooth && !reduce ? "smooth" : "auto" });
    }
    function mark() {
      const i = Math.round(track.scrollLeft / track.clientWidth);
      index = Math.max(0, Math.min(slides.length - 1, i));
      dots.forEach((d, k) => d.toggleAttribute("aria-current", k === index));
    }
    function start() {
      if (reduce) return;
      stop();
      timer = setInterval(() => go(index + 1), 4500);
    }
    function stop() { if (timer) clearInterval(timer); timer = null; }

    dots.forEach((d, k) => d.addEventListener("click", () => { go(k); start(); }));
    track.addEventListener("scroll", () => requestAnimationFrame(mark), { passive: true });
    track.addEventListener("pointerdown", stop);
    track.addEventListener("touchstart", stop, { passive: true });
    track.addEventListener("touchend", () => setTimeout(start, 3000), { passive: true });
    root.addEventListener("mouseenter", stop);
    root.addEventListener("mouseleave", start);
    track.addEventListener("keydown", (e) => {
      if (e.key === "ArrowRight") { go(index + 1); stop(); }
      if (e.key === "ArrowLeft") { go(index - 1); stop(); }
    });
    document.addEventListener("visibilitychange", () => (document.hidden ? stop() : start()));
    start();
  });
})();
