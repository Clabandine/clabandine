"""Statistiques anonymes pour le tableau de bord admin.

On ne compte que des événements agrégés par jour (« diagnostic terminé », « type 3C »,
« clic sur tel produit »…) : aucun identifiant, aucune adresse IP, aucun prénom, aucune
donnée de santé. Rien ne permet de retrouver une personne.

Stockage :
- si la variable DATABASE_URL est définie (base Postgres, par exemple Neon), les
  compteurs y sont gardés durablement ;
- sinon, ils restent en mémoire et repartent à zéro au redémarrage du site.

Les écritures sont regroupées et envoyées toutes les quelques secondes par un fil
séparé : les pages ne sont jamais ralenties par la base.
"""

import atexit
import datetime as dt
import logging
import os
import re
import threading
from collections import Counter

log = logging.getLogger("trichosens.stats")

Cle = tuple[dt.date, str, str]  # (jour, événement, valeur)

VALEUR_RE = re.compile(r"^[A-Za-z0-9_.-]{0,60}$")

# Événements envoyés par le navigateur (étapes, onglets, partage…) : liste fermée.
EVENEMENTS_NAVIGATEUR = {
    "etape_vue", "onglet_resultat", "fiche_pdf", "partage", "avis_clic", "texte_utilise",
    "test_maison", "aide_type", "installer_clic", "app_installee",
}


def aujourd_hui() -> dt.date:
    return dt.datetime.now(dt.timezone.utc).date()


class Memoire:
    """Stockage en mémoire (repart à zéro au redémarrage)."""

    persistant = False

    def __init__(self) -> None:
        self.donnees: Counter[Cle] = Counter()

    def ecrire(self, lots: Counter[Cle]) -> None:
        self.donnees.update(lots)

    def lire(self, depuis: dt.date) -> list[tuple[dt.date, str, str, int]]:
        return [(j, e, v, n) for (j, e, v), n in self.donnees.items() if j >= depuis]


class BaseSQL:
    """Stockage en base Postgres (ou SQLite pour les tests)."""

    persistant = True

    CREATION = (
        "CREATE TABLE IF NOT EXISTS stats ("
        " jour DATE NOT NULL, evenement TEXT NOT NULL, valeur TEXT NOT NULL DEFAULT '',"
        " nombre INTEGER NOT NULL DEFAULT 0, PRIMARY KEY (jour, evenement, valeur))"
    )

    def __init__(self, connecter, marque: str = "%s") -> None:
        self._connecter = connecter
        self._m = marque
        with self._connecter() as conn:
            conn.execute(self.CREATION)
            conn.commit()

    def ecrire(self, lots: Counter[Cle]) -> None:
        m = self._m
        sql = (f"INSERT INTO stats (jour, evenement, valeur, nombre) VALUES ({m}, {m}, {m}, {m}) "
               "ON CONFLICT (jour, evenement, valeur) "
               "DO UPDATE SET nombre = stats.nombre + excluded.nombre")
        with self._connecter() as conn:
            for (jour, evt, val), n in lots.items():
                conn.execute(sql, (jour.isoformat(), evt, val, n))
            conn.commit()

    def lire(self, depuis: dt.date) -> list[tuple[dt.date, str, str, int]]:
        with self._connecter() as conn:
            lignes = conn.execute(
                f"SELECT jour, evenement, valeur, nombre FROM stats WHERE jour >= {self._m}",
                (depuis.isoformat(),)).fetchall()
        return [(j if isinstance(j, dt.date) else dt.date.fromisoformat(j), e, v, n)
                for j, e, v, n in lignes]


def _postgres(url: str) -> BaseSQL:
    import psycopg

    return BaseSQL(lambda: psycopg.connect(url, connect_timeout=10))


class Statistiques:
    def __init__(self, stockage=None, intervalle: float = 5.0) -> None:
        self.stockage = stockage or Memoire()
        self.intervalle = intervalle
        self.depuis = dt.datetime.now(dt.timezone.utc)
        self._attente: Counter[Cle] = Counter()
        self._verrou = threading.Lock()
        self._fil: threading.Thread | None = None
        self._arret = threading.Event()
        self.erreur = ""

    # --- Écriture -------------------------------------------------------------

    def compter(self, evenement: str, valeur: str = "", nombre: int = 1) -> None:
        valeur = str(valeur or "")[:60]
        if not VALEUR_RE.match(valeur):
            valeur = "autre"
        with self._verrou:
            self._attente[(aujourd_hui(), evenement, valeur)] += nombre
        self._demarrer()

    def vider(self) -> None:
        """Envoie au stockage tout ce qui est en attente."""
        with self._verrou:
            lots, self._attente = self._attente, Counter()
        if not lots:
            return
        try:
            self.stockage.ecrire(lots)
            self.erreur = ""
        except Exception as e:  # base injoignable : on garde les compteurs pour plus tard
            log.warning("Statistiques non enregistrées : %s", e)
            self.erreur = "La base de données ne répond pas : les chiffres récents sont en attente."
            with self._verrou:
                self._attente.update(lots)

    def _demarrer(self) -> None:
        if self._fil is None and self.stockage.persistant:
            self._fil = threading.Thread(target=self._boucle, daemon=True, name="stats")
            self._fil.start()
        elif not self.stockage.persistant:
            self.vider()

    def _boucle(self) -> None:
        while not self._arret.wait(self.intervalle):
            self.vider()

    # --- Lecture --------------------------------------------------------------

    def lire(self, jours: int) -> list[tuple[dt.date, str, str, int]]:
        self.vider()
        depuis = aujourd_hui() - dt.timedelta(days=jours - 1)
        try:
            return self.stockage.lire(depuis)
        except Exception as e:
            log.warning("Lecture des statistiques impossible : %s", e)
            self.erreur = "La base de données ne répond pas."
            return []


def creer() -> Statistiques:
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        try:
            return Statistiques(_postgres(url))
        except Exception as e:
            log.error("Base de statistiques injoignable, compteurs en mémoire : %s", e)
            s = Statistiques()
            s.erreur = "La base de données n'a pas pu être jointe au démarrage : chiffres en mémoire."
            return s
    return Statistiques()


stats = creer()
atexit.register(stats.vider)


# --- Synthèse pour le tableau de bord -------------------------------------------------

def synthese(lignes: list[tuple[dt.date, str, str, int]], jours: int) -> dict:
    """Totaux, répartitions et courbe jour par jour à partir des lignes brutes."""
    totaux: Counter[str] = Counter()
    par_valeur: dict[str, Counter[str]] = {}
    par_jour: dict[str, Counter[dt.date]] = {}
    for jour, evt, val, n in lignes:
        totaux[evt] += n
        par_valeur.setdefault(evt, Counter())[val] += n
        par_jour.setdefault(evt, Counter())[jour] += n
    fin = aujourd_hui()
    calendrier = [fin - dt.timedelta(days=i) for i in range(jours - 1, -1, -1)]
    return {
        "totaux": totaux,
        "repartition": {e: c.most_common() for e, c in par_valeur.items()},
        "courbe": {e: [(j, c.get(j, 0)) for j in calendrier] for e, c in par_jour.items()},
        "calendrier": calendrier,
    }


def enregistrer_diagnostic(a, d) -> None:
    """Compte un diagnostic terminé et son profil (anonyme, sans données de santé)."""
    c = stats.compter
    c("diagnostic_termine", a.pour)
    c("mode", a.mode)
    c("type", a.type_cheveux)
    c("famille", a.famille)
    if a.type_secondaire:
        c("deux_types", "oui")
    for p in a.preoccupations:
        c("gene", p)
    c("objectif", a.objectif)
    c("cuir_chevelu", a.cuir_chevelu)
    c("porosite", a.porosite)
    c("elasticite", a.elasticite)
    c("fiabilite", d.fiabilite.get("niveau", ""))
    c("phase", d.phase)  # « entretien » ou « ajustement » : la personne revient
    c("budget", a.budget)
    for pref in a.preferences:
        c("preference", pref)
    if a.pour == "adulte" and a.age != "nc":
        c("age", a.age)
    if a.age_jeune:
        c("age_jeune", a.age_jeune)
    if d.photo and d.photo.exploitable:
        c("photo", "oui")
    # Volontairement absents : prénom, périodes de vie, santé, texte libre.
