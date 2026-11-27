"""Demandes de partenariat (marques, vendeurs indépendants, professionnels).

Le formulaire de la page « Marques » enregistre des coordonnées professionnelles pour
pouvoir répondre. Stockage : base Postgres (DATABASE_URL) si elle existe, sinon en
mémoire (perdu au redémarrage : l'adresse e-mail de contact reste affichée sur la page).
"""

import datetime as dt
import logging
import os
import re
import threading
import time
from collections import defaultdict, deque
from dataclasses import dataclass

log = logging.getLogger("trichosens.partenaires")

TYPES = {
    "marque": "Marque de soins capillaires",
    "vendeur": "Vendeur ou boutique indépendante",
    "professionnel": "Professionnel (coiffeur, trichologue…)",
    "autre": "Autre",
}
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
LIMITES = {"marque": 80, "nom": 80, "email": 120, "site": 200, "message": 2000}


class DemandeInvalide(ValueError):
    def __init__(self, erreurs: dict[str, str]):
        super().__init__("; ".join(erreurs.values()))
        self.erreurs = erreurs


@dataclass
class Demande:
    marque: str
    nom: str
    email: str
    site: str
    type: str
    message: str
    cree_le: dt.datetime | None = None


def valider(form: dict) -> Demande:
    def champ(cle: str) -> str:
        v = form.get(cle) or ""
        return " ".join(str(v).split())[:LIMITES.get(cle, 200)] if cle != "message" \
            else str(v).strip()[:LIMITES["message"]]

    d = Demande(marque=champ("marque"), nom=champ("nom"), email=champ("email"),
                site=champ("site"), type=str(form.get("type") or "autre"), message=champ("message"))
    erreurs = {}
    if not d.marque:
        erreurs["marque"] = "Indiquez le nom de votre marque ou de votre activité."
    if not EMAIL_RE.match(d.email):
        erreurs["email"] = "Indiquez une adresse e-mail valide pour que nous puissions vous répondre."
    if d.type not in TYPES:
        d.type = "autre"
    if d.site and not d.site.startswith(("http://", "https://")):
        d.site = "https://" + d.site
    if form.get("accord") != "oui":
        erreurs["accord"] = "Merci d'accepter que nous gardions ces informations pour vous répondre."
    if erreurs:
        raise DemandeInvalide(erreurs)
    return d


class Memoire:
    persistant = False

    def __init__(self) -> None:
        self.demandes: list[Demande] = []

    def ajouter(self, d: Demande) -> None:
        self.demandes.append(d)

    def lister(self) -> list[Demande]:
        return sorted(self.demandes, key=lambda d: d.cree_le, reverse=True)


class BaseSQL:
    persistant = True
    CREATION = (
        "CREATE TABLE IF NOT EXISTS demandes_partenaires ("
        " cree_le TEXT NOT NULL, marque TEXT NOT NULL, nom TEXT NOT NULL DEFAULT '',"
        " email TEXT NOT NULL, site TEXT NOT NULL DEFAULT '', type TEXT NOT NULL,"
        " message TEXT NOT NULL DEFAULT '')"
    )

    def __init__(self, connecter, marque: str = "%s") -> None:
        self._connecter, self._m = connecter, marque
        with self._connecter() as conn:
            conn.execute(self.CREATION)
            conn.commit()

    def ajouter(self, d: Demande) -> None:
        m = self._m
        with self._connecter() as conn:
            conn.execute(
                "INSERT INTO demandes_partenaires (cree_le, marque, nom, email, site, type, message)"
                f" VALUES ({m}, {m}, {m}, {m}, {m}, {m}, {m})",
                (d.cree_le.isoformat(), d.marque, d.nom, d.email, d.site, d.type, d.message))
            conn.commit()

    def lister(self) -> list[Demande]:
        with self._connecter() as conn:
            lignes = conn.execute(
                "SELECT cree_le, marque, nom, email, site, type, message FROM demandes_partenaires"
                " ORDER BY cree_le DESC LIMIT 500").fetchall()
        return [Demande(marque=m, nom=n, email=e, site=s, type=t, message=msg,
                        cree_le=dt.datetime.fromisoformat(c)) for c, m, n, e, s, t, msg in lignes]


class Limiteur:
    """Au plus N demandes par heure et par adresse (contre les envois automatiques)."""

    def __init__(self, par_heure: int = 5) -> None:
        self.par_heure = par_heure
        self._hits: dict[str, deque] = defaultdict(deque)
        self._lock = threading.Lock()

    def autorise(self, ip: str) -> bool:
        maintenant = time.time()
        with self._lock:
            hits = self._hits[ip]
            while hits and maintenant - hits[0] > 3600:
                hits.popleft()
            if len(hits) >= self.par_heure:
                return False
            hits.append(maintenant)
            return True


def _creer():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        try:
            import psycopg

            return BaseSQL(lambda: psycopg.connect(url, connect_timeout=10))
        except Exception as e:
            log.error("Base injoignable, demandes de partenariat en mémoire : %s", e)
    return Memoire()


stockage = _creer()
limiteur = Limiteur()


def enregistrer(d: Demande) -> None:
    d.cree_le = dt.datetime.now(dt.timezone.utc)
    stockage.ajouter(d)
    log.info("Nouvelle demande de partenariat : %s (%s)", d.marque, d.type)
