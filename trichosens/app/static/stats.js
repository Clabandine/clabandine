// Statistiques anonymes : un nom d'événement et une valeur courte, rien d'autre
// (pas d'identifiant, pas de texte saisi). Une seule fois par page et par valeur.
window.tsStat = (function () {
  const deja = new Set();
  return function (nom, valeur) {
    const cle = nom + ":" + (valeur || "");
    if (deja.has(cle)) return;
    deja.add(cle);
    const corps = JSON.stringify({ nom: nom, valeur: valeur || "" });
    try {
      if (navigator.sendBeacon) {
        navigator.sendBeacon("/api/evenement", new Blob([corps], { type: "application/json" }));
      } else {
        fetch("/api/evenement", { method: "POST", body: corps, keepalive: true,
          headers: { "Content-Type": "application/json" } });
      }
    } catch (e) { /* les statistiques ne doivent jamais gêner la personne */ }
  };
})();
