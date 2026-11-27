// Application TrichoSens : ouverture rapide et suivi disponible hors connexion.
// Servi à l'adresse /sw.js (portée : tout le site). La version change à chaque mise en
// ligne, ce qui renouvelle le cache.
const VERSION = "trichosens-__VERSION__";
const PAGES = ["/", "/diagnostic", "/suivi", "/application", "/hors-ligne"];
const FICHIERS = [
  "/static/style.css", "/static/app.js", "/static/stats.js", "/static/installer.js",
  "/static/diagnostic.js", "/static/resultat.js", "/static/suivi.js",
  "/static/img/logo.svg", "/static/img/logo-blanc.svg", "/static/img/favicon.svg",
  "/static/img/icone-192.png",
];
// Jamais en cache : espace admin, API, liens d'achat, fichiers agenda.
const RESEAU_SEUL = ["/admin", "/api/", "/acheter/", "/rappels.ics", "/sw.js"];

self.addEventListener("install", (event) => {
  event.waitUntil(
    caches.open(VERSION).then((cache) =>
      // Un fichier manquant ne doit pas empêcher l'installation.
      Promise.all([...PAGES, ...FICHIERS].map((url) => cache.add(url).catch(() => null)))
    ).then(() => self.skipWaiting())
  );
});

self.addEventListener("activate", (event) => {
  event.waitUntil(
    caches.keys()
      .then((cles) => Promise.all(cles.filter((c) => c !== VERSION).map((c) => caches.delete(c))))
      .then(() => self.clients.claim())
  );
});

function enCache(requete, reponse) {
  if (reponse && reponse.ok) {
    const copie = reponse.clone();
    caches.open(VERSION).then((cache) => cache.put(requete, copie));
  }
  return reponse;
}

self.addEventListener("fetch", (event) => {
  const req = event.request;
  if (req.method !== "GET") return;
  const url = new URL(req.url);

  if (url.origin === self.location.origin) {
    if (RESEAU_SEUL.some((p) => url.pathname.startsWith(p))) return;

    // Pages : le réseau d'abord (contenu à jour), le cache si la connexion manque.
    if (req.mode === "navigate") {
      event.respondWith(
        fetch(req)
          .then((rep) => (PAGES.includes(url.pathname) ? enCache(new Request(url.pathname), rep) : rep))
          .catch(() => caches.match(url.pathname).then((rep) => rep || caches.match("/hors-ligne")))
      );
      return;
    }

    // Styles, scripts, images : tout de suite depuis le cache, mis à jour en arrière-plan.
    if (url.pathname.startsWith("/static/")) {
      event.respondWith(
        caches.match(req).then((cache) => {
          const reseau = fetch(req).then((rep) => enCache(req, rep)).catch(() => cache);
          return cache || reseau;
        })
      );
    }
    return;
  }

  // Polices Google : gardées en cache après le premier chargement.
  if (url.hostname === "fonts.googleapis.com" || url.hostname === "fonts.gstatic.com") {
    event.respondWith(
      caches.match(req).then((cache) => cache || fetch(req).then((rep) => {
        const copie = rep.clone();
        caches.open(VERSION).then((c) => c.put(req, copie));
        return rep;
      }))
    );
  }
});
