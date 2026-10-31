"""Contrôle du catalogue : liens d'achat morts et fiches produits à revoir.

Lancer depuis le dossier trichosens/ :  python scripts/verifier_catalogue.py

Le script est lancé chaque semaine par GitHub (.github/workflows/trichosens-verification.yml).
Il écrit un rapport et se termine en erreur s'il trouve un lien mort : GitHub prévient
alors par e-mail. Les fiches à revoir sont listées, sans provoquer d'erreur.
"""

import os
import sys
import time
import urllib.error
import urllib.request
from dataclasses import dataclass
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent.parent))

from app.catalog import load_catalog, raison_a_revoir  # noqa: E402

USER_AGENT = ("Mozilla/5.0 (compatible; TrichoSens-verification/1.0; "
              "+https://github.com/Clabandine/clabandine)")


@dataclass
class Resultat:
    statut: str  # ok, mort, non_verifiable, recherche
    detail: str = ""


def verifier_lien(url: str, timeout: float = 15, essais: int = 2) -> Resultat:
    # Une page de recherche existe toujours : rien à contrôler.
    if "/s?" in url and "amazon." in url:
        return Resultat("recherche", "lien de recherche")
    dernier = ""
    for essai in range(essais):
        req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT,
                                                   "Accept-Language": "fr-FR,fr;q=0.9"})
        try:
            with urllib.request.urlopen(req, timeout=timeout) as r:
                return Resultat("ok", str(r.status))
        except urllib.error.HTTPError as e:
            if e.code in (404, 410):
                return Resultat("mort", f"erreur {e.code} : page introuvable")
            dernier = f"erreur {e.code}"  # 403, 429, 503… : souvent un blocage anti-robot
        except (urllib.error.URLError, TimeoutError, OSError) as e:
            dernier = f"injoignable ({getattr(e, 'reason', e)})"
        if essai + 1 < essais:
            time.sleep(2)
    return Resultat("non_verifiable", dernier)


def rapport() -> tuple[str, int]:
    catalog = load_catalog()
    morts, douteux, a_revoir = [], [], []
    nb_liens = 0
    for p in catalog:
        for o in p.offres:
            nb_liens += 1
            r = verifier_lien(o.url)
            if r.statut == "mort":
                morts.append((p, o, r))
            elif r.statut == "non_verifiable":
                douteux.append((p, o, r))
        raison = raison_a_revoir(p)
        if raison:
            a_revoir.append((p, raison))

    lignes = ["# Contrôle du catalogue TrichoSens", "",
              f"{len(catalog)} produits, {nb_liens} liens d'achat.", ""]
    lignes += ["## Liens morts", ""]
    if morts:
        lignes += ["Ces liens mènent à une page introuvable : remplacez-les ou mettez `actif` à "
                   "`non` dans `app/data/liens.csv`.", ""]
        lignes += [f"- **{p.nom_complet}** chez {o.marchand} : {r.detail} — {o.url}"
                   for p, o, r in morts]
    else:
        lignes.append("Aucun lien mort. ✅")
    if douteux:
        lignes += ["", "## Liens non vérifiables", "",
                   "Le site a bloqué le contrôle automatique (fréquent chez Amazon). "
                   "Vérifiez-les à la main de temps en temps.", ""]
        lignes += [f"- {p.nom_complet} chez {o.marchand} : {r.detail}" for p, o, r in douteux]
    lignes += ["", f"## Fiches produits à revoir ({len(a_revoir)})", ""]
    if a_revoir:
        lignes += ["Après vérification d'une fiche (composition, prix, types de cheveux), mettez "
                   "`a_verifier` à `non` et la date du jour dans `date_verification`.", ""]
        lignes += [f"- {p.nom_complet} : {raison}" for p, raison in a_revoir]
    else:
        lignes.append("Toutes les fiches sont à jour. ✅")
    return "\n".join(lignes) + "\n", len(morts)


def main() -> None:
    texte, nb_morts = rapport()
    print(texte)
    resume = os.environ.get("GITHUB_STEP_SUMMARY")
    if resume:
        with open(resume, "a", encoding="utf-8") as f:
            f.write(texte)
    sys.exit(1 if nb_morts else 0)


if __name__ == "__main__":
    main()
