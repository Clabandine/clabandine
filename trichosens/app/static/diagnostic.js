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

  // Avant de passer à l'étape suivante (ex. : lire le texte libre s'il vient d'être écrit).
  let avantSuite = () => Promise.resolve();

  form.addEventListener("click", (e) => {
    if (e.target.matches("[data-next]")) {
      const panel = panels[current];
      avantSuite(panel).then(() => {
        if (panels[current] === panel && validatePanel(panel)) show(current + 1);
      });
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

  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s == null ? "" : String(s);
    return div.innerHTML;
  }

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
    updateDependants();
  }
  form.querySelectorAll('input[name="famille"]').forEach((r) =>
    r.addEventListener("change", () => showFamily(r.value))
  );

  // --- Questions qui dépendent d'une autre réponse ----------------------------

  const checkedValue = (name) => {
    const el = form.querySelector(`input[name="${name}"]:checked`);
    return el ? el.value : "";
  };

  function hideAndClear(el, hide) {
    el.hidden = hide;
    if (hide) el.querySelectorAll("input").forEach((i) => {
      if (i.type === "radio" && i.value === "") i.checked = true;
      else i.checked = false;
    });
  }

  function renumber() {
    let n = 0;
    form.querySelectorAll(".question").forEach((q) => {
      if (q.hidden) return;
      const num = q.querySelector("legend .num");
      if (num) num.textContent = ++n;
    });
  }

  function updateDependants() {
    // Détails des démangeaisons : seulement si « Démangeaisons » est coché.
    const pains = Array.from(form.querySelectorAll('input[name="preoccupations"]:checked')).map((i) => i.value);
    form.querySelectorAll(".question[data-show-if]").forEach((q) =>
      hideAndClear(q, !q.dataset.showIf.split(" ").some((v) => pains.includes(v)))
    );

    // Second type et situations propres au type : après le choix du type.
    const type = checkedValue("type_cheveux");
    const famille = type ? type[0] : checkedValue("famille");
    const second = form.querySelector(".q-type_secondaire");
    if (second) {
      hideAndClear(second, !type);
      second.querySelectorAll(".chip[data-value]").forEach((c) => {
        const same = c.dataset.value === type;
        c.hidden = same;
        if (same) c.querySelector("input").checked = false;
      });
      if (type && !checkedValue("type_secondaire")) second.querySelector('input[value=""]').checked = true;
    }
    const spec = form.querySelector(".q-specifiques");
    if (spec) {
      const sec = checkedValue("type_secondaire");
      const familles = [famille, sec ? sec[0] : ""].filter(Boolean);
      let visible = 0;
      spec.querySelectorAll(".option[data-familles]").forEach((o) => {
        const ok = familles.some((f) => o.dataset.familles.includes(f));
        hideAndClear(o, !ok);
        if (ok) visible++;
      });
      spec.hidden = visible === 0;
    }
    renumber();
  }

  form.addEventListener("change", (e) => {
    if (["preoccupations", "type_cheveux", "type_secondaire"].includes(e.target.name)) updateDependants();
  });

  const checkedFamily = form.querySelector('input[name="famille"]:checked');
  if (checkedFamily) showFamily(checkedFamily.value);
  else updateDependants();

  // --- Aide pour trouver son type ----------------------------------------------

  const helper = form.querySelector(".type-helper");
  if (helper) {
    const tailleBox = helper.querySelector(".helper-taille");
    const result = helper.querySelector(".helper-result");
    const error = helper.querySelector(".helper-error");
    const value = (name) => {
      const el = helper.querySelector(`input[name="${name}"]:checked`);
      return el ? el.value : "";
    };

    helper.addEventListener("change", (e) => {
      if (e.target.name === "aide_forme") {
        tailleBox.hidden = false;
        helper.querySelectorAll(".helper-tailles").forEach((g) => (g.hidden = g.dataset.forme !== e.target.value));
      }
      error.hidden = true;
    });

    helper.querySelector("[data-trouver]").addEventListener("click", async () => {
      const forme = value("aide_forme");
      const payload = {
        forme, taille: value("aide_taille_" + forme),
        retractation: value("aide_retractation"), textures: value("aide_textures") || "une",
      };
      if (!payload.forme || !payload.taille) {
        error.textContent = "Répondez au moins aux questions 1 et 2.";
        error.hidden = false;
        return;
      }
      try {
        const response = await fetch("/api/trouver-type", {
          method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(payload),
        });
        const r = await response.json();
        if (!response.ok) throw new Error(r.detail || "");
        result.innerHTML =
          `<p><strong>Type ${escapeHtml(r.type)}${r.secondaire ? " avec une part de " + escapeHtml(r.secondaire) : ""}</strong></p>` +
          `<p>${escapeHtml(r.explication)}</p>` +
          '<button type="button" class="button" data-appliquer>Choisir ce résultat</button>';
        result.hidden = false;
        result.querySelector("[data-appliquer]").addEventListener("click", () => {
          const fam = form.querySelector(`input[name="famille"][value="${r.type[0]}"]`);
          if (fam) { fam.checked = true; showFamily(r.type[0]); }
          const radio = form.querySelector(`input[name="type_cheveux"][value="${r.type}"]`);
          if (radio) radio.checked = true;
          updateDependants();
          const sec = form.querySelector(`input[name="type_secondaire"][value="${r.secondaire || ""}"]`);
          if (sec) sec.checked = true;
          updateDependants();
          helper.open = false;
          const chosen = radio && radio.closest(".option");
          if (chosen) chosen.scrollIntoView({ behavior: "smooth", block: "center" });
        });
      } catch (err) {
        error.textContent = "Le calcul n'a pas abouti. Réessayez dans un instant.";
        error.hidden = false;
      }
    });
  }

  // --- Pré-remplissage automatique à partir d'un texte libre ----------------------
  // Les réponses suggérées sont cochées et marquées ; la personne les confirme, les
  // modifie ou en coche d'autres. Une suggestion décochée n'est jamais recochée.

  const texteBox = form.querySelector(".texte-box");
  if (texteBox) {
    const area = texteBox.querySelector("#description");
    const compteur = texteBox.querySelector(".texte-compteur");
    const statut = texteBox.querySelector(".texte-status");
    const resumeBox = texteBox.querySelector(".texte-resume");
    const iaBox = texteBox.querySelector("#texte-ia");
    const suggerees = new Map(); // "nom=valeur" -> input coché d'après le texte
    const refusees = new Set();  // suggestions décochées ou changées par la personne
    let dernierTexte = "";
    let minuteur = null;
    let enCours = null;

    const cle = (input) => input.name + "=" + input.value;

    function marquer(input) {
      const el = input.closest(".pain, .option");
      if (!el || el.querySelector(".text-badge")) return;
      const badge = document.createElement("em");
      badge.className = "text-badge";
      badge.textContent = "D'après votre texte";
      (el.querySelector(".option-text") || el.querySelector(".pain-head > span") || el).appendChild(badge);
    }

    function demarquer(input) {
      const el = input.closest(".pain, .option");
      const badge = el && el.querySelector(".text-badge");
      if (badge) badge.remove();
    }

    function cocher(name, value, { siVide = false } = {}) {
      const input = form.querySelector(`input[name="${name}"][value="${value}"]`);
      if (!input || refusees.has(cle(input))) return false;
      if (input.closest(".question[hidden], .option[hidden], .chip[hidden]") || input.disabled) return false;
      const deja = form.querySelector(`input[name="${name}"]:checked`);
      if (siVide && deja && deja !== input && deja.value !== "" && !suggerees.has(cle(deja))) return false;
      if (!input.checked) {
        input.checked = true;
        input.dispatchEvent(new Event("change", { bubbles: true }));
      }
      suggerees.set(cle(input), input);
      marquer(input);
      return true;
    }

    // Ce que la personne change elle-même devient sa réponse.
    form.addEventListener("change", (e) => {
      if (!e.isTrusted || !e.target.name) return;
      suggerees.forEach((input, k) => {
        if (input.name === e.target.name && !input.checked) {
          refusees.add(k);
          suggerees.delete(k);
          demarquer(input);
        }
      });
      if (suggerees.has(cle(e.target))) { suggerees.delete(cle(e.target)); demarquer(e.target); }
    });

    function appliquer(res) {
      const r = res.reponses;
      const voulues = new Set();
      const noter = (name, values) => (values || []).forEach((v) => voulues.add(name + "=" + v));
      noter("preoccupations", r.preoccupations);
      (r.preoccupations || []).forEach((p) => voulues.add(`gene_${p}=${res.intensites[p] || "beaucoup"}`));
      ["demangeaisons_details", "specifiques", "traitements", "periodes"].forEach((q) => noter(q, r[q]));
      ["type_cheveux", "type_secondaire", "epaisseur", "densite", "porosite", "cuir_chevelu",
        "chaleur", "objectif", "age"].forEach((q) => r[q] && voulues.add(q + "=" + r[q]));
      const famille = r.type_cheveux ? r.type_cheveux[0] : r.famille;
      if (famille) voulues.add("famille=" + famille);

      // Les anciennes suggestions qui ne correspondent plus au texte sont retirées.
      suggerees.forEach((input, k) => {
        if (voulues.has(k)) return;
        if (input.type === "radio" && input.name === "type_secondaire") {
          const non = form.querySelector('input[name="type_secondaire"][value=""]');
          if (non) non.checked = true;
        } else {
          input.checked = false;
        }
        input.dispatchEvent(new Event("change", { bubbles: true }));
        demarquer(input);
        suggerees.delete(k);
      });

      (r.preoccupations || []).forEach((p) => {
        if (cocher("preoccupations", p)) {
          const niveau = form.querySelector(`input[name="gene_${p}"]:checked`);
          if (!niveau || suggerees.has(cle(niveau))) cocher("gene_" + p, res.intensites[p] || "beaucoup");
        }
      });
      updateDependants();
      (r.demangeaisons_details || []).forEach((v) => cocher("demangeaisons_details", v));
      const typeChoisi = form.querySelector('input[name="type_cheveux"]:checked');
      if (famille && (!typeChoisi || suggerees.has(cle(typeChoisi)))) {
        const fam = form.querySelector(`input[name="famille"][value="${famille}"]`);
        if (fam && !refusees.has(cle(fam))) {
          fam.checked = true;
          showFamily(famille);
          suggerees.set(cle(fam), fam);
          marquer(fam);
        }
        if (r.type_cheveux) cocher("type_cheveux", r.type_cheveux);
      }
      updateDependants();
      if (r.type_secondaire) cocher("type_secondaire", r.type_secondaire, { siVide: true });
      updateDependants();
      (r.specifiques || []).forEach((v) => cocher("specifiques", v));
      ["epaisseur", "densite", "porosite", "cuir_chevelu", "chaleur", "objectif", "age"].forEach((q) => {
        if (r[q]) cocher(q, r[q], { siVide: true });
      });
      ["traitements", "periodes"].forEach((q) => (r[q] || []).forEach((v) => cocher(q, v)));
      updateDependants();

      afficherResume(res);
      if (res.note) resumeBox.innerHTML += `<p class="help">${escapeHtml(res.note)}</p>`;
      resumeBox.hidden = false;
    }

    // Résumé construit à partir des cases réellement pré-cochées (et non refusées).
    function etiquette(input) {
      const el = input.closest(".pain, .option, .chip");
      const nom = el && (el.querySelector("strong") || el.querySelector("span"));
      return nom ? nom.textContent.trim() : input.value;
    }

    function afficherResume(res) {
      const items = [];
      suggerees.forEach((input) => {
        if (!input.checked || input.name.startsWith("gene_")) return;
        if (input.name === "famille" && form.querySelector('input[name="type_cheveux"]:checked')) return;
        let texte = etiquette(input);
        if (input.name === "preoccupations") {
          const niveau = form.querySelector(`input[name="gene_${input.value}"]:checked`);
          if (niveau) texte += " (" + etiquette(niveau).toLowerCase() + ")";
        }
        items.push(texte);
      });
      resumeBox.innerHTML = !items.length
        ? "<p>Nous n'avons rien repéré de précis pour l'instant : répondez simplement aux questions.</p>"
        : '<p class="texte-disclaimer">✍️ <strong>D’après votre texte, nous avons pré-coché quelques réponses.</strong> ' +
          "Confirmez-les, modifiez-les ou cochez-en d'autres à chaque étape.</p>" +
          '<div class="chips">' + items.map((x) => `<span class="chip static">${escapeHtml(x)}</span>`).join("") + "</div>" +
          (res.metisse ? "<p>Cheveux métissés : l'aide « Je ne suis pas sûre de mon type » de l'étape « Vos cheveux » vous aidera à préciser vos deux types.</p>" : "");
    }

    function analyser() {
      clearTimeout(minuteur);
      const texte = area.value.trim();
      if (texte.length < 15 || texte === dernierTexte) return enCours || Promise.resolve();
      dernierTexte = texte;
      statut.textContent = "Lecture de votre texte…";
      enCours = fetch("/api/analyse-texte", {
        method: "POST", headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ texte, ia: Boolean(iaBox && iaBox.checked) }),
      })
        .then((response) => response.json().then((res) => {
          if (!response.ok) throw new Error(res.detail || "");
          statut.textContent = "";
          if (area.value.trim() === texte) appliquer(res);
        }))
        .catch(() => {
          statut.textContent = "Nous n'avons pas pu lire votre texte : répondez directement aux questions.";
        })
        .finally(() => { enCours = null; });
      return enCours;
    }

    area.addEventListener("input", () => {
      compteur.textContent = area.value.length + " / 1500";
      clearTimeout(minuteur);
      // Avec l'IA, on attend la fin de la saisie pour limiter les appels.
      if (!(iaBox && iaBox.checked)) minuteur = setTimeout(analyser, 1200);
    });
    area.addEventListener("blur", analyser);
    if (iaBox) iaBox.addEventListener("change", () => { dernierTexte = ""; analyser(); });
    avantSuite = (panel) => (panel.contains(texteBox) ? analyser() : Promise.resolve());
  }

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
      alourdis: "Cheveux alourdis", pellicules: "Pellicules",
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
