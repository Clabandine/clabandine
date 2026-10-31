"""Catalogue de produits.

Le catalogue est le tableau `data/produits.csv` (séparateur « ; »), modifiable dans
Google Sheets ou Excel. Une ligne = un produit. Dans les colonnes à plusieurs
valeurs, séparez les valeurs par « | ». La colonne `types` accepte des plages :
« 3A-4C » veut dire « de 3A à 4C ». Une colonne vide veut dire « tous ».
"""

import csv
import datetime as dt
import re
import unicodedata
from dataclasses import asdict, dataclass, replace
from functools import lru_cache
from pathlib import Path

from .hair_types import HAIR_TYPES

CATALOG_PATH = Path(__file__).parent / "data" / "produits.csv"
LIENS_PATH = Path(__file__).parent / "data" / "liens.csv"

CATEGORIES = {
    "shampoing": "Shampoing",
    "apres_shampoing": "Après-shampoing",
    "masque": "Masque",
    "leave_in": "Soin sans rinçage",
    "coiffant": "Coiffant",
    "huile": "Huile ou beurre",
    "protecteur_thermique": "Protecteur thermique",
    "soin_cuir": "Soin du cuir chevelu",
    "shampoing_clarifiant": "Shampoing clarifiant",
    "accessoire": "Accessoire",
}
POIDS = {"leger", "moyen", "riche"}
SAISONS = {"hiver", "printemps", "ete", "automne"}
CUIRS = {"normal", "sec", "gras", "sensible", "pellicules"}
TYPE_CODES = list(HAIR_TYPES)  # dans l'ordre, de 1A à 4C


@dataclass(frozen=True)
class Offre:
    """Un revendeur qui vend le produit (lien d'achat, affilié ou non)."""

    id: str
    produit_id: str
    marchand: str
    url: str
    prix: float | None = None
    affilie: bool = False

    @property
    def recherche(self) -> bool:
        """Lien vers une page de recherche (et non vers la fiche du produit)."""
        return "/s?" in self.url

    @property
    def amazon(self) -> bool:
        return "amazon." in self.url


@dataclass(frozen=True)
class Product:
    id: str
    marque: str
    nom: str
    categorie: str
    description: str
    besoins: tuple[str, ...]
    poids: str = "moyen"
    types: tuple[str, ...] = ()  # vide = tous les types
    cuir_chevelu: tuple[str, ...] = ()  # vide = tous les cuirs chevelus
    sans_parfum: bool | None = None
    sans_sulfates: bool | None = None
    sans_silicones: bool | None = None
    vegan: bool | None = None
    saisons: tuple[str, ...] = ()
    prix: float | None = None
    contenance: str = ""
    ingredients_cles: tuple[str, ...] = ()
    a_verifier: bool = True
    verifie_le: dt.date | None = None
    offres: tuple[Offre, ...] = ()

    @property
    def nom_complet(self) -> str:
        return f"{self.marque} – {self.nom}"

    @property
    def labels(self) -> list[str]:
        out = []
        if self.sans_sulfates:
            out.append("Sans sulfates")
        if self.sans_silicones:
            out.append("Sans silicones")
        if self.sans_parfum:
            out.append("Sans parfum")
        if self.vegan:
            out.append("Vegan")
        return out

    def to_dict(self) -> dict:
        d = asdict(self)
        d["labels"] = self.labels
        return d


def _list(value: str) -> tuple[str, ...]:
    return tuple(v.strip() for v in (value or "").split("|") if v.strip())


def _bool(value: str) -> bool | None:
    value = (value or "").strip().lower()
    if value in {"oui", "o", "yes", "true", "1"}:
        return True
    if value in {"non", "n", "no", "false", "0"}:
        return False
    return None  # inconnu


def parse_types(value: str) -> tuple[str, ...]:
    """« 3A-4C|1B » -> ('1B', '3A', '3B', '3C', '4A', '4B', '4C')."""
    codes: set[str] = set()
    for part in _list(value.replace(",", "|")):
        part = part.upper()
        if part in {"TOUS", "TOUT"}:
            return ()
        if "-" in part:
            start, end = (p.strip() for p in part.split("-", 1))
            if start not in HAIR_TYPES or end not in HAIR_TYPES:
                raise ValueError(f"Plage de types inconnue : {part}")
            i, j = TYPE_CODES.index(start), TYPE_CODES.index(end)
            codes.update(TYPE_CODES[min(i, j): max(i, j) + 1])
        elif part in HAIR_TYPES:
            codes.add(part)
        else:
            raise ValueError(f"Type inconnu : {part}")
    return tuple(c for c in TYPE_CODES if c in codes)


def _saison(value: str) -> str:
    return value.strip().lower().replace("é", "e")


def parse_product(row: dict) -> Product:
    pid = (row.get("id") or "").strip()
    errors = []
    categorie = (row.get("categorie") or "").strip()
    if categorie not in CATEGORIES:
        errors.append(f"catégorie inconnue « {categorie} »")
    poids = (row.get("poids") or "moyen").strip() or "moyen"
    if poids not in POIDS:
        errors.append(f"poids inconnu « {poids} »")
    cuirs = _list(row.get("cuir_chevelu", ""))
    if set(cuirs) - CUIRS:
        errors.append(f"cuir chevelu inconnu : {', '.join(set(cuirs) - CUIRS)}")
    saisons = tuple(_saison(s) for s in _list(row.get("saisons", "")))
    if set(saisons) - SAISONS:
        errors.append(f"saison inconnue : {', '.join(set(saisons) - SAISONS)}")
    try:
        types = parse_types(row.get("types", ""))
    except ValueError as e:
        errors.append(str(e))
        types = ()
    prix_txt = (row.get("prix_indicatif") or "").strip().replace(",", ".")
    try:
        prix = float(prix_txt) if prix_txt else None
    except ValueError:
        errors.append(f"prix illisible « {prix_txt} »")
        prix = None
    date_txt = (row.get("date_verification") or "").strip()
    verifie_le = None
    if date_txt:
        try:
            verifie_le = (dt.datetime.strptime(date_txt, "%d/%m/%Y").date() if "/" in date_txt
                          else dt.date.fromisoformat(date_txt))
        except ValueError:
            errors.append(f"date de vérification illisible « {date_txt} » (format 2026-11-30 ou 30/11/2026)")
    if errors:
        raise ValueError(f"Produit {pid or '(sans id)'} : " + " ; ".join(errors))

    return Product(
        id=pid,
        marque=row["marque"].strip(),
        nom=row["nom"].strip(),
        categorie=categorie,
        description=(row.get("description") or "").strip(),
        besoins=_list(row.get("besoins", "")),
        poids=poids,
        types=types,
        cuir_chevelu=cuirs,
        sans_parfum=_bool(row.get("sans_parfum", "")),
        sans_sulfates=_bool(row.get("sans_sulfates", "")),
        sans_silicones=_bool(row.get("sans_silicones", "")),
        vegan=_bool(row.get("vegan", "")),
        saisons=saisons,
        prix=prix,
        contenance=(row.get("contenance") or "").strip(),
        ingredients_cles=_list(row.get("ingredients_cles", "")),
        a_verifier=_bool(row.get("a_verifier", "")) is not False,
        verifie_le=verifie_le,
    )


def _slug(text: str) -> str:
    text = unicodedata.normalize("NFKD", text).encode("ascii", "ignore").decode()
    return re.sub(r"[^a-z0-9]+", "-", text.lower()).strip("-")


def load_offres(path: Path, produits: set[str]) -> dict[str, list[Offre]]:
    """Lit liens.csv : une ligne = un revendeur pour un produit."""
    offres: dict[str, list[Offre]] = {}
    if not path.exists():
        return offres
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f, delimiter=";") if (r.get("produit_id") or "").strip()]
    ids = set()
    for n, row in enumerate(rows, start=2):
        pid = row["produit_id"].strip()
        marchand = (row.get("marchand") or "").strip()
        url = (row.get("url") or "").strip()
        where = f"liens.csv, ligne {n}"
        if pid not in produits:
            raise ValueError(f"{where} : produit inconnu « {pid} »")
        if not marchand:
            raise ValueError(f"{where} : marchand manquant")
        if not url.startswith("https://"):
            raise ValueError(f"{where} : l'adresse doit commencer par https://")
        if _bool(row.get("actif", "")) is False:
            continue
        prix_txt = (row.get("prix") or "").strip().replace(",", ".")
        try:
            prix = float(prix_txt) if prix_txt else None
        except ValueError:
            raise ValueError(f"{where} : prix illisible « {prix_txt} »")
        oid = f"{pid}--{_slug(marchand)}"
        if oid in ids:
            raise ValueError(f"{where} : deux liens pour {marchand} sur le même produit")
        ids.add(oid)
        offres.setdefault(pid, []).append(Offre(
            id=oid, produit_id=pid, marchand=marchand, url=url, prix=prix,
            affilie=_bool(row.get("affilie", "")) is True,
        ))
    for pid in offres:  # le moins cher d'abord
        offres[pid].sort(key=lambda o: (o.prix is None, o.prix or 0))
    return offres


@lru_cache
def load_catalog(path: Path = CATALOG_PATH, liens: Path = LIENS_PATH) -> list[Product]:
    # utf-8-sig : accepte les fichiers enregistrés par Excel.
    with open(path, encoding="utf-8-sig", newline="") as f:
        rows = [r for r in csv.DictReader(f, delimiter=";") if (r.get("id") or "").strip()]
    products = [parse_product(r) for r in rows]
    ids = [p.id for p in products]
    doubles = {i for i in ids if ids.count(i) > 1}
    if doubles:
        raise ValueError(f"Identifiants en double : {', '.join(sorted(doubles))}")
    offres = load_offres(liens, set(ids))
    return [replace(p, offres=tuple(offres.get(p.id, ()))) for p in products]


def offres_par_id(catalog: list[Product]) -> dict[str, Offre]:
    return {o.id: o for p in catalog for o in p.offres}


# Une fiche doit être revérifiée au moins tous les 6 mois (formules et prix changent).
VERIFICATION_MAX_JOURS = 183


def raison_a_revoir(p: Product, today: dt.date | None = None) -> str | None:
    """Pourquoi la fiche produit doit être revue, ou None si elle est à jour."""
    today = today or dt.date.today()
    if p.verifie_le is None:
        return "Jamais vérifiée"
    if p.a_verifier:
        return "Marquée « à vérifier »"
    if (today - p.verifie_le).days > VERIFICATION_MAX_JOURS:
        return f"Dernière vérification le {p.verifie_le.strftime('%d/%m/%Y')} (plus de 6 mois)"
    if not p.offres:
        return "Aucun lien d'achat"
    return None
