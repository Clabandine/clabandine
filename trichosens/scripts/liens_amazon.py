"""Ajoute un lien Amazon (recherche, avec votre identifiant Partenaires) pour chaque
produit du catalogue qui n'a pas encore de lien Amazon.

Lancer depuis le dossier trichosens/ :  python scripts/liens_amazon.py

Pour un meilleur taux de conversion, remplacez ensuite le lien de recherche par le
lien direct de la fiche produit, créé depuis la barre SiteStripe d'Amazon Partenaires.
Ne renseignez pas de prix pour Amazon : son règlement interdit d'afficher un prix
qui ne vient pas de son interface officielle.
"""

import csv
import sys
from pathlib import Path
from urllib.parse import urlencode

AMAZON_TAG = "trichosens-21"
DATA = Path(__file__).resolve().parent.parent / "app" / "data"


def recherche(marque: str, nom: str) -> str:
    query = nom if marque.lower() in {"divers", ""} else f"{marque} {nom}"
    return "https://www.amazon.fr/s?" + urlencode({"k": query, "tag": AMAZON_TAG})


def main() -> None:
    with open(DATA / "produits.csv", encoding="utf-8-sig", newline="") as f:
        produits = [r for r in csv.DictReader(f, delimiter=";") if r.get("id")]
    liens_path = DATA / "liens.csv"
    with open(liens_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        fields = reader.fieldnames
        liens = list(reader)
    deja = {r["produit_id"] for r in liens if r.get("marchand", "").strip().lower() == "amazon"}
    ajouts = [
        {"produit_id": p["id"], "marchand": "Amazon", "url": recherche(p["marque"], p["nom"]),
         "prix": "", "affilie": "oui", "actif": "", "awin_mid": ""}
        for p in produits if p["id"] not in deja
    ]
    with open(liens_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(liens + ajouts)
    print(f"{len(ajouts)} liens Amazon ajoutés", file=sys.stderr)


if __name__ == "__main__":
    main()
