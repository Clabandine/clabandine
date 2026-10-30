// Suivi capillaire : l'historique des diagnostics et le journal de pousse sont gardés
// dans le navigateur (localStorage). Rien n'est envoyé sur nos serveurs, sauf le résumé
// du dernier diagnostic, au moment d'en faire un nouveau, pour comparer.
(function () {
  "use strict";

  const KEY = "trichosens_historique";
  const KEY_JOURNAL = "trichosens_journal";
  const MAX = 30;

  function load(key) {
    try {
      const data = JSON.parse(localStorage.getItem(key) || "[]");
      return Array.isArray(data) ? data : [];
    } catch (e) {
      return [];
    }
  }
  function save(key, value) {
    try {
      localStorage.setItem(key, JSON.stringify(value));
      return true;
    } catch (e) {
      return false;
    }
  }
  const byDate = (a, b) => (a.date < b.date ? -1 : a.date > b.date ? 1 : 0);
  function frDate(iso) {
    const [y, m, d] = iso.split("-");
    return `${d}/${m}/${y}`;
  }
  function escapeHtml(s) {
    const div = document.createElement("div");
    div.textContent = s == null ? "" : String(s);
    return div.innerHTML;
  }

  // --- Page de résultat : enregistrer le diagnostic ---------------------------
  const data = document.getElementById("suivi-data");
  if (data) {
    let entry = null;
    try { entry = JSON.parse(data.textContent); } catch (e) { /* ignoré */ }
    if (entry && entry.id) {
      const history = load(KEY);
      if (!history.some((h) => h.id === entry.id)) {
        history.push(entry);
        history.sort(byDate);
        const ok = save(KEY, history.slice(-MAX));
        const status = document.getElementById("suivi-status");
        if (!ok && status) {
          status.textContent = "Votre navigateur n'a pas permis d'enregistrer ce diagnostic " +
            "(navigation privée ?). Le suivi ne sera pas disponible.";
        }
      }
    }
  }

  // --- Questionnaire : joindre le diagnostic précédent ------------------------
  const precedent = document.getElementById("precedent");
  if (precedent) {
    const history = load(KEY);
    const last = history[history.length - 1];
    if (last) {
      precedent.value = JSON.stringify(last);
      const info = document.querySelector(".suivi-info");
      if (info) {
        info.querySelector("span").textContent = frDate(last.date);
        info.hidden = false;
      }
    }
  }

  // --- Page « Mon suivi » -----------------------------------------------------
  const root = document.getElementById("suivi-root");
  if (!root) return;
  const labels = JSON.parse(document.getElementById("suivi-labels").textContent);
  const LEVEL = { un_peu: 1, beaucoup: 2, enormement: 3 };

  function dots(level) {
    const n = LEVEL[level] || 0;
    if (!n) return '<span class="dots none" title="Absent">–</span>';
    return `<span class="dots l${n}" title="${labels.intensites[level]}">${"●".repeat(n)}</span>`;
  }

  function renderHistory() {
    const history = load(KEY).sort(byDate);
    if (!history.length) {
      root.innerHTML =
        '<section class="card"><p>Vous n\'avez pas encore de diagnostic enregistré sur cet appareil.</p>' +
        '<p><a class="button" href="/diagnostic">Faire mon premier diagnostic</a></p></section>';
      return;
    }
    const last = history[history.length - 1];
    let nextIso = last.prochain_point;
    if (!nextIso) {
      const next = new Date(last.date);
      next.setDate(next.getDate() + 28);
      nextIso = next.toISOString().slice(0, 10);
    }
    const late = nextIso <= new Date().toISOString().slice(0, 10);
    const shown = history.slice(-6);

    let html = '<section class="card">';
    html += `<h2>${history.length} diagnostic${history.length > 1 ? "s" : ""}</h2>`;
    html += `<p>Dernier diagnostic le <strong>${frDate(last.date)}</strong> · type ${escapeHtml(last.type_cheveux)}` +
      ` · ${escapeHtml(labels.phases[last.phase] || "")}</p>`;
    html += late
      ? '<p class="key-tip">📅 C\'est le moment de refaire le point : <a href="/diagnostic">refaire mon diagnostic</a>.</p>'
      : `<p class="key-tip">📅 Prochain point conseillé vers le <strong>${frDate(nextIso)}</strong>.</p>`;
    html += "</section>";

    // Évolution des points de douleur.
    const pains = [...new Set(shown.flatMap((h) => Object.keys(h.intensites || {})))];
    if (pains.length) {
      html += '<section class="card"><h2>Ce qui vous gêne, au fil du temps</h2><div class="table-wrap"><table class="timeline">';
      html += "<thead><tr><th></th>" + shown.map((h) => `<th>${frDate(h.date).slice(0, 5)}</th>`).join("") + "</tr></thead><tbody>";
      for (const p of pains) {
        html += `<tr><th>${escapeHtml(labels.douleurs[p] || p)}</th>` +
          shown.map((h) => `<td>${dots((h.intensites || {})[p])}</td>`).join("") + "</tr>";
      }
      html += "</tbody></table></div><p class=\"help\">● un peu · ●● beaucoup · ●●● énormément</p></section>";
    }

    // Évolution des besoins entre le premier et le dernier diagnostic.
    if (history.length > 1) {
      const first = history[0];
      const rows = Object.keys(last.besoins || {})
        .filter((k) => first.besoins && k in first.besoins)
        .map((k) => [k, first.besoins[k], last.besoins[k]])
        .filter(([, a, b]) => a || b)
        .sort((x, y) => y[2] - x[2]);
      html += '<section class="card"><h2>Les besoins de vos cheveux</h2>';
      html += `<p class="help">Du ${frDate(first.date)} au ${frDate(last.date)}.</p><ul class="needs-evo">`;
      for (const [k, a, b] of rows) {
        const diff = b - a;
        const cls = diff < 0 ? "down" : diff > 0 ? "up" : "same";
        const sign = diff > 0 ? "+" : "";
        html += `<li><span>${escapeHtml(labels.besoins[k] || k)}</span><span>${a} → <strong>${b}</strong></span>` +
          `<span class="delta ${cls}">${diff ? sign + diff : "="}</span></li>`;
      }
      html += '</ul><p class="help">Un besoin qui baisse est bon signe : vos cheveux en ont moins besoin.</p></section>';
    }
    root.innerHTML = html;
  }

  // Journal de pousse.
  const form = document.getElementById("journal-form");
  const list = document.getElementById("journal-list");
  form.date.value = new Date().toISOString().slice(0, 10);

  function renderJournal() {
    const journal = load(KEY_JOURNAL).sort(byDate);
    if (!journal.length) {
      list.innerHTML = '<p class="help">Aucune mesure pour l\'instant.</p>';
      return;
    }
    let html = "";
    const measures = journal.filter((j) => j.longueur);
    if (measures.length >= 2) {
      const a = measures[0];
      const b = measures[measures.length - 1];
      const days = (new Date(b.date) - new Date(a.date)) / 86400000;
      if (days >= 20) {
        const perMonth = ((b.longueur - a.longueur) / days) * 30;
        html += `<p class="key-tip">Pousse moyenne : <strong>${perMonth.toFixed(1).replace(".", ",")} cm par mois</strong>` +
          ` (moyenne habituelle : environ 1 cm).</p>`;
      }
    }
    html += '<ul class="journal">' + journal.slice().reverse().map((j, i) =>
      `<li><span>${frDate(j.date)}</span>` +
      `<strong>${j.longueur ? String(j.longueur).replace(".", ",") + " cm" : ""}</strong>` +
      `<span>${escapeHtml(j.note || "")}</span>` +
      `<button type="button" class="link" data-del="${journal.length - 1 - i}" aria-label="Supprimer">✕</button></li>`
    ).join("") + "</ul>";
    list.innerHTML = html;
  }

  form.addEventListener("submit", (e) => {
    e.preventDefault();
    const longueur = form.longueur.value ? Number(form.longueur.value) : null;
    const note = form.note.value.trim();
    if (!longueur && !note) return;
    const journal = load(KEY_JOURNAL);
    journal.push({ date: form.date.value, longueur, note });
    save(KEY_JOURNAL, journal.sort(byDate));
    form.longueur.value = "";
    form.note.value = "";
    renderJournal();
  });
  list.addEventListener("click", (e) => {
    const i = e.target.dataset && e.target.dataset.del;
    if (i === undefined) return;
    const journal = load(KEY_JOURNAL).sort(byDate);
    journal.splice(Number(i), 1);
    save(KEY_JOURNAL, journal);
    renderJournal();
  });

  // Export, import, effacement.
  document.getElementById("export").addEventListener("click", () => {
    const blob = new Blob([JSON.stringify({ historique: load(KEY), journal: load(KEY_JOURNAL) }, null, 2)],
      { type: "application/json" });
    const a = document.createElement("a");
    a.href = URL.createObjectURL(blob);
    a.download = `trichosens-suivi-${new Date().toISOString().slice(0, 10)}.json`;
    a.click();
  });
  const importFile = document.getElementById("import-file");
  document.getElementById("import-btn").addEventListener("click", () => importFile.click());
  importFile.addEventListener("change", async () => {
    const file = importFile.files[0];
    if (!file) return;
    try {
      const data = JSON.parse(await file.text());
      const merge = (key, items, keyOf) => {
        const current = load(key);
        const seen = new Set(current.map(keyOf));
        for (const it of items || []) if (it && it.date && !seen.has(keyOf(it))) current.push(it);
        save(key, current.sort(byDate).slice(-200));
      };
      merge(KEY, data.historique, (h) => h.id);
      merge(KEY_JOURNAL, data.journal, (j) => `${j.date}|${j.longueur}|${j.note}`);
      renderHistory();
      renderJournal();
    } catch (e) {
      alert("Ce fichier ne peut pas être importé.");
    }
  });
  document.getElementById("clear").addEventListener("click", () => {
    if (!confirm("Effacer tout votre suivi sur cet appareil ? Cette action est définitive.")) return;
    try {
      localStorage.removeItem(KEY);
      localStorage.removeItem(KEY_JOURNAL);
    } catch (e) { /* ignoré */ }
    renderHistory();
    renderJournal();
  });

  renderHistory();
  renderJournal();
})();
