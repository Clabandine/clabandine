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
    if (window.tsStat) window.tsStat("onglet_resultat", id);
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

// Fiche PDF (impression du navigateur) et partage du résumé.
(function () {
  "use strict";
  const status = document.querySelector(".share-status");
  const say = (msg) => { if (status) { status.textContent = msg; setTimeout(() => (status.textContent = ""), 4000); } };

  document.querySelectorAll("[data-print]").forEach((b) =>
    b.addEventListener("click", () => { if (window.tsStat) window.tsStat("fiche_pdf"); window.print(); })
  );

  document.querySelectorAll("[data-share]").forEach((b) =>
    b.addEventListener("click", async () => {
      if (window.tsStat) window.tsStat("partage");
      const text = b.dataset.text;
      if (navigator.share) {
        try {
          await navigator.share({ title: "Ma routine TrichoSens", text });
          return;
        } catch (e) {
          if (e && e.name === "AbortError") return; // partage annulé
        }
      }
      try {
        await navigator.clipboard.writeText(text);
        say("Résumé copié : collez-le dans un message.");
      } catch (e) {
        say("Le partage n'est pas disponible sur cet appareil.");
      }
    })
  );

  // --- Liens d'achat selon le pays de livraison ------------------------------------
  // Chaque lien porte ses pays (data-pays) ; on garde ceux du pays choisi. Sans lien
  // pour ce pays, on montre ceux de France avec la mention « Livraison depuis la France ».
  const choix = document.getElementById("pays-livraison");
  const PAYS = choix ? Array.from(choix.options).map((o) => o.value) : [];
  function paysParDefaut() {
    try {
      const garde = localStorage.getItem("ts_pays");
      if (garde && PAYS.includes(garde)) return garde;
    } catch (e) { /* stockage indisponible */ }
    for (const lang of navigator.languages || [navigator.language || ""]) {
      const region = (lang.split("-")[1] || "").toUpperCase();
      if (region) return PAYS.includes(region) ? region : "AUTRE";
    }
    return "FR";
  }
  function appliquerPays(pays) {
    document.querySelectorAll(".offres").forEach((bloc) => {
      const offres = Array.from(bloc.querySelectorAll(".offre"));
      const pour = (code) => offres.filter((o) => o.dataset.pays === "*" || o.dataset.pays.split(" ").includes(code));
      let visibles = pour(pays);
      const repli = visibles.length === 0;
      if (repli) visibles = pour("FR");
      if (bloc.classList.contains("petit")) visibles = visibles.slice(0, 1);
      offres.forEach((o) => { o.hidden = !visibles.includes(o); });
      offres.forEach((o) => o.querySelector(".buy").classList.remove("first"));
      if (visibles[0] && !bloc.classList.contains("petit")) visibles[0].querySelector(".buy").classList.add("first");
      const note = bloc.querySelector(".offre-note");
      if (note) note.hidden = !(repli && pays !== "FR" && visibles.length);
    });
  }
  if (choix) {
    choix.closest(".pays-choix").hidden = false;
    choix.value = paysParDefaut();
    appliquerPays(choix.value);
    choix.addEventListener("change", () => {
      try { localStorage.setItem("ts_pays", choix.value); } catch (e) { /* rien */ }
      appliquerPays(choix.value);
    });
  }

  // --- Inscription aux conseils et rappels par e-mail ---------------------------------
  document.querySelectorAll("form[data-inscription]").forEach((f) => {
    f.addEventListener("submit", async (e) => {
      e.preventDefault();
      const statut = f.querySelector(".inscription-statut");
      const champ = (n) => f.querySelector(`[name="${n}"]`);
      const type = champ("type_cheveux");
      const donnees = {
        email: champ("email").value,
        conseils: champ("conseils").checked,
        partenaires: champ("partenaires").checked,
        type_cheveux: type && type.checked ? type.value : "",
        site: champ("site").value,
      };
      const bouton = f.querySelector('button[type="submit"]');
      bouton.disabled = true;
      try {
        const rep = await fetch("/api/inscription", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(donnees),
        });
        const res = await rep.json();
        if (!rep.ok) throw new Error(res.detail || "L'inscription n'a pas abouti.");
        statut.textContent = res.message;
        statut.classList.add("ok");
        f.querySelectorAll("label, button").forEach((el) => (el.hidden = true));
      } catch (err) {
        statut.textContent = err.message;
        bouton.disabled = false;
      }
    });
  });
})();
