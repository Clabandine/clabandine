// Questionnaire en plusieurs étapes et analyse photo.
// Sans JavaScript, toutes les questions s'affichent sur une seule page.
(function () {
  "use strict";

  const form = document.getElementById("diagnostic-form");
  if (!form) return;

  const panels = Array.from(form.querySelectorAll(".step-panel"));
  const submit = form.querySelector(".submit");
  let current = 0;

  // --- Étapes ---------------------------------------------------------------

  document.querySelectorAll(".js-only").forEach((el) => (el.hidden = false));
  form.classList.add("wizard");
  document.getElementById("step-total").textContent = panels.length;

  const stepper = Array.from(document.querySelectorAll(".stepper li"));

  function show(index) {
    const forward = index >= current;
    current = index;
    panels.forEach((p, i) => {
      p.hidden = i !== index;
      if (i === index) {
        p.classList.remove("enter-left", "enter-right");
        void p.offsetWidth; // relance l'animation
        p.classList.add(forward ? "enter-right" : "enter-left");
      }
    });
    stepper.forEach((li, i) => {
      li.classList.toggle("done", i < index);
      li.classList.toggle("current", i === index);
    });
    submit.hidden = index !== panels.length - 1;
    document.getElementById("step-num").textContent = index + 1;
    document.getElementById("step-name").textContent = panels[index].dataset.title;
    document.getElementById("progress-fill").style.width = ((index + 1) / panels.length) * 100 + "%";
    window.scrollTo({ top: 0, behavior: "smooth" });
  }

  function setError(container, message) {
    const p = container.querySelector(":scope > .error");
    container.classList.toggle("has-error", Boolean(message));
    if (p) {
      p.textContent = message || "";
      p.hidden = !message;
    }
  }

  function validatePanel(panel) {
    let ok = true;
    panel.querySelectorAll(".question").forEach((q) => {
      let message = "";
      const checked = q.querySelectorAll(`input[name="${q.dataset.question}"]:checked`);
      if (q.dataset.required === "true" && checked.length === 0) {
        message = "Choisissez une réponse pour continuer.";
      }
      if (q.dataset.question === "preoccupations") {
        q.querySelectorAll(".pain").forEach((pain) => {
          const box = pain.querySelector('input[type="checkbox"]');
          const level = pain.querySelector('input[type="radio"]:checked');
          const missing = box.checked && !level;
          pain.classList.toggle("has-error", missing);
          if (missing && !message) message = "Dites-nous à quel point chaque point vous gêne.";
        });
      }
      setError(q, message);
      if (message) ok = false;
    });
    if (!ok) {
      const first = panel.querySelector(".has-error");
      if (first) first.scrollIntoView({ behavior: "smooth", block: "center" });
    }
    return ok;
  }

  form.addEventListener("click", (e) => {
    if (e.target.matches("[data-next]")) {
      if (validatePanel(panels[current])) show(current + 1);
    } else if (e.target.matches("[data-prev]")) {
      show(current - 1);
    }
  });

  form.addEventListener("submit", (e) => {
    const bad = panels.findIndex((p) => !validatePanel(p));
    if (bad !== -1) {
      e.preventDefault();
      show(bad);
      validatePanel(panels[bad]);
      return;
    }
    submit.disabled = true;
    submit.textContent = "Préparation de votre diagnostic…";
    // Écran d'attente animé pendant le calcul du résultat.
    const screen = document.getElementById("loading-screen");
    if (screen) {
      screen.hidden = false;
      const msgs = ["Nous étudions votre type de cheveux", "Nous analysons ce qui vous gêne",
        "Nous composons votre routine", "Nous choisissons vos produits"];
      const line = document.getElementById("loading-step");
      let k = 0;
      setInterval(() => { k = (k + 1) % msgs.length; line.textContent = msgs[k]; }, 900);
    }
  });

  // Une réponse efface le message d'erreur de sa question.
  form.addEventListener("change", (e) => {
    const q = e.target.closest(".question");
    if (q && q.classList.contains("has-error")) validatePanel(q.closest(".step-panel"));
  });

  // Au maximum N choix pour les questions à choix multiples limités.
  form.querySelectorAll(".question[data-max]").forEach((q) => {
    const max = Number(q.dataset.max);
    const boxes = Array.from(q.querySelectorAll(`input[name="${q.dataset.question}"]`));
    const update = () => {
      const n = boxes.filter((b) => b.checked).length;
      boxes.forEach((b) => (b.disabled = !b.checked && n >= max));
    };
    boxes.forEach((b) => b.addEventListener("change", update));
    update();
  });

  // Type de cheveux : choisir la famille (1 à 4), puis le type (A, B ou C).
  const subtypeLabel = form.querySelector(".subtype-label");
  function showFamily(famille) {
    form.querySelectorAll(".subtype-group").forEach((g) => {
      const active = g.dataset.famille === famille;
      g.classList.toggle("active", active);
      // Un type d'une autre famille n'a plus de sens : on le décoche.
      if (!active) g.querySelectorAll("input").forEach((i) => (i.checked = false));
    });
    if (subtypeLabel) subtypeLabel.hidden = !famille;
  }
  form.querySelectorAll('input[name="famille"]').forEach((r) =>
    r.addEventListener("change", () => showFamily(r.value))
  );
  const checkedFamily = form.querySelector('input[name="famille"]:checked');
  if (checkedFamily) showFamily(checkedFamily.value);

  // Après une erreur côté serveur, ouvrir la première étape concernée.
  const firstError = panels.findIndex((p) => p.querySelector(".has-error"));
  show(firstError === -1 ? 0 : firstError);

  // --- Photo ----------------------------------------------------------------

  const input = document.getElementById("photo-input");
  if (!input) return;

  const preview = document.getElementById("photo-preview");
  const dropText = document.getElementById("photo-drop-text");
  const consent = document.getElementById("photo-consent");
  const button = document.getElementById("photo-analyse");
  const status = document.getElementById("photo-status");
  const result = document.getElementById("photo-result");
  const hidden = document.getElementById("analyse-photo");
  let file = null;

  const FAMILY_LABELS = { 1: "raides (lisses)", 2: "ondulés", 3: "bouclés", 4: "crépus et frisés" };
  const LABELS = {
    signe: {
      secheresse: "Sécheresse", frisottis: "Frisottis", pointes: "Pointes abîmées", casse: "Casse",
      terne: "Manque d'éclat", definition: "Boucles peu définies", volume: "Manque de volume",
      alourdis: "Cheveux alourdis",
    },
    intensite: { leger: "léger", modere: "modéré", marque: "marqué" },
  };

  function refreshButton() {
    button.disabled = !(file && consent.checked);
  }

  input.addEventListener("change", () => {
    file = input.files && input.files[0];
    if (file) {
      preview.src = URL.createObjectURL(file);
      preview.hidden = false;
      dropText.textContent = "Changer de photo";
    }
    refreshButton();
  });
  consent.addEventListener("change", refreshButton);

  // Réduit la photo dans le navigateur avant l'envoi (plus rapide sur mobile).
  function shrink(f) {
    return new Promise((resolve) => {
      const img = new Image();
      img.onload = () => {
        const max = 1568;
        const scale = Math.min(1, max / Math.max(img.width, img.height));
        const canvas = document.createElement("canvas");
        canvas.width = Math.round(img.width * scale);
        canvas.height = Math.round(img.height * scale);
        canvas.getContext("2d").drawImage(img, 0, 0, canvas.width, canvas.height);
        canvas.toBlob((blob) => resolve(blob || f), "image/jpeg", 0.85);
      };
      img.onerror = () => resolve(f); // format non lu par le navigateur : on envoie tel quel
      img.src = URL.createObjectURL(f);
    });
  }

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s == null ? "" : String(s);
    return div.innerHTML;
  }

  function suggest(question, value) {
    const option = form.querySelector(`.question[data-question="${question}"] .option[data-value="${value}"]`);
    if (!option) return;
    option.querySelector(".ai-badge").hidden = false;
    const radio = option.querySelector("input");
    const group = form.querySelectorAll(`input[name="${question}"]`);
    if (!Array.from(group).some((r) => r.checked)) radio.checked = true;
  }

  function suggestType(code) {
    const family = form.querySelector(`input[name="famille"][value="${code[0]}"]`);
    if (!family) return;
    family.closest(".option").querySelector(".ai-badge").hidden = false;
    const typeChosen = form.querySelector('input[name="type_cheveux"]:checked');
    if (!typeChosen) {
      family.checked = true;
      showFamily(code[0]);
    }
    suggest("type_cheveux", code);
  }

  function render(a) {
    form.querySelectorAll(".ai-badge").forEach((b) => (b.hidden = true));
    if (!a.exploitable) {
      result.innerHTML =
        `<p><strong>Cette photo ne permet pas une bonne analyse.</strong></p>` +
        `<p>${escapeHtml(a.conseil_photo || "Essayez une photo plus nette, à la lumière du jour.")}</p>`;
      result.hidden = false;
      return;
    }
    let html = "<h3>Ce que l'IA observe</h3>";
    if (a.type_cheveux) {
      html += `<p>Vos cheveux ressemblent au <strong>type ${a.type_cheveux}</strong>, ` +
        `${FAMILY_LABELS[a.type_cheveux[0]]} ` +
        `(confiance ${a.confiance_type === "elevee" ? "élevée" : a.confiance_type}).</p>`;
    }
    html += "<ul>" + a.observations.map((o) => `<li>${escapeHtml(o)}</li>`).join("") + "</ul>";
    if (a.signes.length) {
      html += '<div class="chips">' + a.signes.map((s) =>
        `<span class="chip static">${LABELS.signe[s.signe]} · ${LABELS.intensite[s.intensite]}</span>`
      ).join("") + "</div>";
    }
    if (a.alerte_medicale) html += `<p class="alert">${escapeHtml(a.alerte_medicale)}</p>`;
    html += '<p class="help">Les réponses suggérées par l\'IA sont marquées dans les étapes suivantes. ' +
      "Vous pouvez toujours les modifier.</p>";
    result.innerHTML = html;
    result.hidden = false;

    if (a.type_cheveux && a.confiance_type !== "faible") suggestType(a.type_cheveux);
    if (a.epaisseur && a.epaisseur !== "indetermine") suggest("epaisseur", a.epaisseur);
    if (a.densite && a.densite !== "indetermine") suggest("densite", a.densite);
  }

  button.addEventListener("click", async () => {
    if (!file) return;
    button.disabled = true;
    status.textContent = "Analyse en cours… cela prend environ 20 secondes.";
    status.classList.add("loading");
    result.hidden = true;
    try {
      const data = new FormData();
      data.append("photo", await shrink(file), "photo.jpg");
      data.append("consentement", "oui");
      const response = await fetch("/api/analyse-photo", { method: "POST", body: data });
      const body = await response.json().catch(() => ({}));
      if (!response.ok) throw new Error(body.detail || "L'analyse n'a pas pu aboutir.");
      hidden.value = JSON.stringify(body);
      status.textContent = body.exploitable ? "Analyse terminée ✓" : "";
      render(body);
      const next = panels[current].querySelector("[data-next]");
      if (next && body.exploitable) next.textContent = "Continuer";
    } catch (err) {
      status.textContent = err.message + " Vous pouvez aussi continuer sans photo.";
    } finally {
      status.classList.remove("loading");
      refreshButton();
    }
  });

  // Analyse déjà faite (retour après une erreur du formulaire).
  if (hidden.value) {
    try { render(JSON.parse(hidden.value)); } catch (e) { hidden.value = ""; }
  }
})();
