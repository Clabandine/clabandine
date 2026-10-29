"""Catalogue de produits.

Pour l'instant, le catalogue est un fichier JSON d'exemples génériques
(`data/produits.json`). Il sera remplacé par les produits des marques partenaires.
"""

import json
from dataclasses import asdict, dataclass, field
from functools import lru_cache
from pathlib import Path

CATALOG_PATH = Path(__file__).parent / "data" / "produits.json"

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


@dataclass(frozen=True)
class Product:
    id: str
    nom: str
    categorie: str
    description: str
    besoins: tuple[str, ...]
    poids: str = "moyen"  # leger, moyen ou riche
    textures: tuple[str, ...] = ()  # vide = toutes les textures
    cuir_chevelu: tuple[str, ...] = ()  # vide = tous les cuirs chevelus
    sans_parfum: bool = False
    prix: float | None = None
    ingredients_cles: tuple[str, ...] = field(default=())

    def to_dict(self) -> dict:
        return asdict(self)


def parse_product(raw: dict) -> Product:
    if raw["categorie"] not in CATEGORIES:
        raise ValueError(f"Catégorie inconnue pour {raw['id']} : {raw['categorie']}")
    data = dict(raw)
    for key in ("besoins", "textures", "cuir_chevelu", "ingredients_cles"):
        data[key] = tuple(data.get(key, ()))
    return Product(**data)


@lru_cache
def load_catalog(path: Path = CATALOG_PATH) -> list[Product]:
    with open(path, encoding="utf-8") as f:
        return [parse_product(p) for p in json.load(f)]
