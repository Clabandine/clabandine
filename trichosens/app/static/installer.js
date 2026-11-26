// Installer TrichoSens sur l'écran d'accueil (application web).
(function () {
  "use strict";

  if ("serviceWorker" in navigator) {
    window.addEventListener("load", () => navigator.serviceWorker.register("/sw.js").catch(() => {}));
  }

  const stat = (nom) => { if (window.tsStat) window.tsStat(nom); };
  const installee = matchMedia("(display-mode: standalone)").matches || window.navigator.standalone === true;
  if (installee) {
    document.documentElement.classList.add("app-installee");
    return; // déjà dans l'application : pas de bouton « Installer »
  }

  const ua = navigator.userAgent;
  const ios = /iphone|ipad|ipod/i.test(ua) || (/macintosh/i.test(ua) && "ontouchend" in document);
  let invite = null;

  function afficher() {
    document.querySelectorAll(".installer-bloc").forEach((b) => (b.hidden = false));
  }
  function masquer() {
    document.querySelectorAll(".installer-bloc").forEach((b) => (b.hidden = true));
  }

  // Android et ordinateur (Chrome, Edge, Samsung Internet) : le navigateur propose l'installation.
  window.addEventListener("beforeinstallprompt", (e) => {
    e.preventDefault();
    invite = e;
    afficher();
  });
  // iPhone et iPad : pas d'installation automatique, on explique le geste.
  if (ios) {
    document.documentElement.classList.add("ios");
    afficher();
  }

  document.addEventListener("click", async (e) => {
    const bouton = e.target.closest("[data-installer]");
    if (!bouton) return;
    e.preventDefault();
    stat("installer_clic");
    if (invite) {
      invite.prompt();
      const choix = await invite.userChoice;
      invite = null;
      if (choix.outcome === "accepted") masquer();
      return;
    }
    const aide = document.getElementById("installer-aide");
    if (aide && typeof aide.showModal === "function") aide.showModal();
    else window.location.href = "/application";
  });

  document.addEventListener("click", (e) => {
    if (e.target.closest("[data-fermer-aide]")) document.getElementById("installer-aide").close();
  });

  window.addEventListener("appinstalled", () => {
    stat("app_installee");
    masquer();
  });
})();
