// Page de résultat en onglets. Sans JavaScript, toutes les sections restent visibles.
(function () {
  "use strict";

  const nav = document.querySelector(".tabs");
  if (!nav) return;
  const tabs = Array.from(nav.querySelectorAll("[role=tab]"));
  const panels = Array.from(document.querySelectorAll(".tab-panel"));
  const ids = tabs.map((t) => t.dataset.tab);

  document.body.classList.add("tabbed");
  nav.hidden = false;

  function show(id, { focus = false, scroll = true } = {}) {
    if (!ids.includes(id)) id = ids[0];
    tabs.forEach((t) => {
      const on = t.dataset.tab === id;
      t.setAttribute("aria-selected", on ? "true" : "false");
      t.tabIndex = on ? 0 : -1;
      if (on) {
        t.scrollIntoView({ block: "nearest", inline: "center", behavior: "smooth" });
        if (focus) t.focus();
      }
    });
    panels.forEach((p) => {
      const on = p.id === "panel-" + id;
      p.hidden = !on;
      if (on) {
        p.classList.remove("enter");
        void p.offsetWidth; // relance l'animation d'entrée
        p.classList.add("enter");
      }
    });
    try { history.replaceState(null, "", "#" + id); } catch (e) { /* ignoré */ }
    if (scroll) {
      // Amène le haut de l'onglet sous l'en-tête, pour voir tout de suite son contenu.
      const header = document.querySelector(".site-header");
      const offset = header ? header.offsetHeight : 0;
      const top = nav.offsetTop - offset;
      window.scrollTo({ top: Math.max(0, top), behavior: "smooth" });
    }
  }

  nav.addEventListener("click", (e) => {
    const t = e.target.closest("[role=tab]");
    if (t) show(t.dataset.tab);
  });

  // Flèches gauche/droite entre les onglets (accessibilité clavier).
  nav.addEventListener("keydown", (e) => {
    const i = tabs.indexOf(document.activeElement);
    if (i < 0) return;
    if (e.key === "ArrowRight" || e.key === "ArrowLeft") {
      e.preventDefault();
      const next = (i + (e.key === "ArrowRight" ? 1 : -1) + tabs.length) % tabs.length;
      show(tabs[next].dataset.tab, { focus: true });
    }
  });

  // Boutons « Voir la suite » et liens vers un produit.
  document.addEventListener("click", (e) => {
    const b = e.target.closest("[data-goto]");
    if (!b) return;
    show(b.dataset.goto);
    if (b.dataset.product) {
      const card = document.getElementById("produit-" + b.dataset.product);
      if (card) {
        setTimeout(() => {
          card.scrollIntoView({ behavior: "smooth", block: "center" });
          card.classList.remove("flash");
          void card.offsetWidth;
          card.classList.add("flash");
        }, 150);
      }
    }
  });

  show(location.hash.slice(1), { scroll: false });
})();
