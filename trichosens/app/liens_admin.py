"""Liens d'achat ajustés depuis l'espace admin.

Remplacer un lien de recherche Amazon par la fiche exacte du produit, ou ajouter un
revendeur officiel, sans toucher aux fichiers : les ajustements sont gardés dans la base
de données et appliqués par-dessus liens.csv. L'export /admin/liens.csv donne le fichier
complet, à remettre dans le projet pour les garder pour de bon.
"""

import csv
import datetime as dt
import io
import logging
import os
import re
import threading
from dataclasses import dataclass, replace
from urllib.parse import parse_qs, urlsplit

from .catalog import AMAZON_DOMAINES, Offre, Product, _slug

log = logging.getLogger("trichosens.liens")

TAG_AMAZON_FR = "trichosens-21"
ASIN_RE = re.compile(r"/(?:dp|gp/product|gp/aw/d)/([A-Z0-9]{10})(?:[/?]|$)", re.IGNORECASE)


class LienInvalide(ValueError):
    pass


@dataclass
class Ajustement:
    produit_id: str
    marchand: str
    url: str
    pays: tuple[str, ...] = ()
    affilie: bool = True
    cree_le: dt.datetime | None = None


def normaliser(url: str) -> tuple[str, bool]:
    """Nettoie l'adresse ; pour Amazon, garde la fiche exacte et ajoute l'identifiant.

    Renvoie (adresse, affiliée).
    """
    url = (url or "").strip()
    if not url.startswith("https://"):
        raise LienInvalide("L'adresse doit commencer par https://")
    parts = urlsplit(url)
    hote = parts.netloc.lower()
    if hote.endswith(("amzn.to", "amzn.eu", "a.co")):
        raise LienInvalide("C'est un lien court Amazon : ouvrez-le, puis copiez l'adresse complète de la "
                           "fiche (celle qui contient /dp/…).")
    if any(hote.endswith(d) for d in AMAZON_DOMAINES):
        m = ASIN_RE.search(parts.path)
        if not m:
            raise LienInvalide("Ce lien Amazon ne pointe pas vers une fiche produit (il doit contenir /dp/…).")
        asin = m.group(1).upper()
        hote = hote if hote.startswith("www.") else "www." + hote
        tag = parse_qs(parts.query).get("tag", [""])[0]
        if hote == "www.amazon.fr":
            tag = TAG_AMAZON_FR
        if not tag:
            raise LienInvalide("Pour cette boutique Amazon, collez le lien avec votre identifiant "
                               "Partenaires (paramètre tag=…).")
        return f"https://{hote}/dp/{asin}?tag={tag}", True
    return url, False


class Memoire:
    persistant = False

    def __init__(self) -> None:
        self.ajustements: dict[tuple[str, str], Ajustement] = {}

    def enregistrer(self, a: Ajustement) -> None:
        self.ajustements[(a.produit_id, a.marchand)] = a

    def retirer(self, produit_id: str, marchand: str) -> None:
        self.ajustements.pop((produit_id, marchand), None)

    def lister(self) -> list[Ajustement]:
        return list(self.ajustements.values())


class BaseSQL:
    persistant = True
    CREATION = (
        "CREATE TABLE IF NOT EXISTS liens_ajustes ("
        " produit_id TEXT NOT NULL, marchand TEXT NOT NULL, url TEXT NOT NULL,"
        " pays TEXT NOT NULL DEFAULT '', affilie BOOLEAN NOT NULL, cree_le TEXT NOT NULL,"
        " PRIMARY KEY (produit_id, marchand))"
    )

    def __init__(self, connecter, marque: str = "%s") -> None:
        self._connecter, self._m = connecter, marque
        with self._connecter() as conn:
            conn.execute(self.CREATION)
            conn.commit()

    def enregistrer(self, a: Ajustement) -> None:
        m = self._m
        with self._connecter() as conn:
            conn.execute(
                "INSERT INTO liens_ajustes (produit_id, marchand, url, pays, affilie, cree_le)"
                f" VALUES ({m}, {m}, {m}, {m}, {m}, {m}) ON CONFLICT (produit_id, marchand) DO UPDATE SET"
                " url = excluded.url, pays = excluded.pays, affilie = excluded.affilie,"
                " cree_le = excluded.cree_le",
                (a.produit_id, a.marchand, a.url, "|".join(a.pays), a.affilie, a.cree_le.isoformat()))
            conn.commit()

    def retirer(self, produit_id: str, marchand: str) -> None:
        with self._connecter() as conn:
            conn.execute(f"DELETE FROM liens_ajustes WHERE produit_id = {self._m} AND marchand = {self._m}",
                         (produit_id, marchand))
            conn.commit()

    def lister(self) -> list[Ajustement]:
        with self._connecter() as conn:
            lignes = conn.execute(
                "SELECT produit_id, marchand, url, pays, affilie, cree_le FROM liens_ajustes").fetchall()
        return [Ajustement(p, m, u, tuple(x for x in pays.split("|") if x), bool(a),
                           dt.datetime.fromisoformat(c)) for p, m, u, pays, a, c in lignes]


def _creer():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        try:
            import psycopg

            return BaseSQL(lambda: psycopg.connect(url, connect_timeout=10))
        except Exception as e:
            log.error("Base injoignable, liens ajustés en mémoire : %s", e)
    return Memoire()


stockage = _creer()
_verrou = threading.Lock()
_cache: dict = {"cle": None, "catalogue": None, "version": 0}


def _changement() -> None:
    with _verrou:
        _cache["version"] += 1


def ajuster(produit_id: str, marchand: str, url: str, pays: tuple[str, ...] = ()) -> Ajustement:
    propre, affilie = normaliser(url)
    a = Ajustement(produit_id, marchand.strip() or "Amazon", propre, pays, affilie,
                   dt.datetime.now(dt.timezone.utc))
    stockage.enregistrer(a)
    _changement()
    return a


def retirer(produit_id: str, marchand: str) -> None:
    stockage.retirer(produit_id, marchand)
    _changement()


def catalogue_complet(base: list[Product]) -> list[Product]:
    """Le catalogue avec les liens ajustés : même lien remplacé, nouveau revendeur ajouté."""
    with _verrou:
        cle = (id(base), _cache["version"])
        if _cache["cle"] == cle:
            return _cache["catalogue"]
    try:
        ajustements = stockage.lister()
    except Exception as e:
        log.warning("Liens ajustés illisibles, liens du fichier utilisés : %s", e)
        return base
    par_produit: dict[str, list[Ajustement]] = {}
    for a in ajustements:
        par_produit.setdefault(a.produit_id, []).append(a)
    resultat = []
    for p in base:
        if p.id not in par_produit:
            resultat.append(p)
            continue
        offres = {o.marchand: o for o in p.offres}
        for a in par_produit[p.id]:
            ancienne = offres.get(a.marchand)
            offres[a.marchand] = Offre(
                id=f"{p.id}--{_slug(a.marchand)}", produit_id=p.id, marchand=a.marchand, url=a.url,
                prix=ancienne.prix if ancienne else None, affilie=a.affilie,
                pays=a.pays or (ancienne.pays if ancienne else ()))
        triees = sorted(offres.values(), key=lambda o: (not o.trichosens, o.prix is None, o.prix or 0))
        resultat.append(replace(p, offres=tuple(triees)))
    with _verrou:
        _cache.update(cle=cle, catalogue=resultat)
    return resultat


def export_csv(catalogue: list[Product]) -> str:
    """liens.csv complet (fichier + ajustements), à remettre dans app/data/."""
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=";", lineterminator="\n")
    w.writerow(["produit_id", "marchand", "url", "prix", "affilie", "actif", "awin_mid", "pays"])
    for p in catalogue:
        for o in p.offres:
            w.writerow([p.id, o.marchand, o.url, f"{o.prix:.2f}" if o.prix else "",
                        "oui" if o.affilie else "non", "", "", "|".join(o.pays)])
    return sortie.getvalue()
