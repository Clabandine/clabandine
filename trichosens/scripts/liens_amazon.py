"""Ajoute un lien Amazon (recherche, avec votre identifiant Partenaires) pour chaque
produit du catalogue qui n'a pas encore de lien sur cette boutique Amazon.

Lancer depuis le dossier trichosens/ :

    python scripts/liens_amazon.py                       # amazon.fr (France, Belgique…)
    python scripts/liens_amazon.py --boutique ca --tag votre-id-20   # amazon.ca

Chaque boutique Amazon demande son propre compte Partenaires (et son propre identifiant).
Les liens sont rattachés aux pays indiqués dans la colonne « pays » de liens.csv : le
résultat du diagnostic montre ceux du pays de livraison choisi par la personne.

Pour un meilleur taux de conversion, remplacez ensuite le lien de recherche par le
lien direct de la fiche produit, créé depuis la barre SiteStripe d'Amazon Partenaires.
Ne renseignez pas de prix pour Amazon : son règlement interdit d'afficher un prix
qui ne vient pas de son interface officielle.
"""

import argparse
import csv
import sys
from pathlib import Path
from urllib.parse import urlencode

AMAZON_TAG = "trichosens-21"
DATA = Path(__file__).resolve().parent.parent / "app" / "data"

# boutique : (domaine, nom du marchand dans liens.csv, pays desservis)
BOUTIQUES = {
    "fr": ("www.amazon.fr", "Amazon", "FR|BE|LU|MC"),
    "be": ("www.amazon.com.be", "Amazon Belgique", "BE"),
    "de": ("www.amazon.de", "Amazon Allemagne", "DE|CH|AT"),
    "uk": ("www.amazon.co.uk", "Amazon Royaume-Uni", "GB"),
    "ca": ("www.amazon.ca", "Amazon Canada", "CA"),
    "us": ("www.amazon.com", "Amazon États-Unis", "US"),
}


def recherche(marque: str, nom: str, domaine: str = "www.amazon.fr", tag: str = AMAZON_TAG) -> str:
    query = nom if marque.lower() in {"divers", ""} else f"{marque} {nom}"
    return f"https://{domaine}/s?" + urlencode({"k": query, "tag": tag})


def main(argv: list[str] | None = None) -> None:
    parser = argparse.ArgumentParser(description=__doc__.split("\n\n")[0])
    parser.add_argument("--boutique", choices=sorted(BOUTIQUES), default="fr")
    parser.add_argument("--tag", default=None,
                        help="identifiant Partenaires de cette boutique (obligatoire hors amazon.fr)")
    args = parser.parse_args(argv)
    if args.boutique != "fr" and not args.tag:
        parser.error("indiquez l'identifiant Partenaires de cette boutique avec --tag")
    domaine, marchand, pays = BOUTIQUES[args.boutique]
    tag = args.tag or AMAZON_TAG

    with open(DATA / "produits.csv", encoding="utf-8-sig", newline="") as f:
        produits = [r for r in csv.DictReader(f, delimiter=";") if r.get("id")]
    liens_path = DATA / "liens.csv"
    with open(liens_path, encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f, delimiter=";")
        fields = reader.fieldnames
        liens = list(reader)
    deja = {r["produit_id"] for r in liens if r.get("marchand", "").strip() == marchand}
    ajouts = [
        {"produit_id": p["id"], "marchand": marchand,
         "url": recherche(p["marque"], p["nom"], domaine, tag),
         "prix": "", "affilie": "oui", "actif": "", "awin_mid": "", "pays": pays}
        for p in produits if p["id"] not in deja and p.get("categorie") != "coffret"
    ]
    with open(liens_path, "w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields, delimiter=";", lineterminator="\n")
        w.writeheader()
        w.writerows(liens + ajouts)
    print(f"{len(ajouts)} liens {marchand} ajoutés", file=sys.stderr)


if __name__ == "__main__":
    main()
