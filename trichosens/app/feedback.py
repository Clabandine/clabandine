"""Lien vers le questionnaire d'avis, pré-rempli avec le résultat du diagnostic.

Dans Google Forms, créez un lien pré-rempli (menu ⋮ > « Obtenir le lien prérempli ») en
tapant ces mots-repères dans des questions à réponse courte ou longue :

    TS_RESUME     résumé complet : type, gênes, priorités, phase, photo
    TS_TYPE       type de cheveux (ex. 3C)
    TS_PROBLEMES  ce qui gêne, avec l'intensité
    TS_PRIORITES  les 3 besoins prioritaires
    TS_PRODUITS   les produits recommandés
    TS_PHASE      la phase du programme
    TS_ID         référence courte du diagnostic

Collez ce lien dans la variable AVIS_URL (Render > Environment). Chaque bouton « Donner
mon avis » remplacera les mots-repères par le résultat de la personne. Aucune donnée
personnelle n'est transmise (ni âge, ni période de vie, ni photo).
"""

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from .engine import NEEDS, PHASES, Diagnostic

REPERES = ("TS_RESUME", "TS_TYPE", "TS_PROBLEMES", "TS_PRIORITES", "TS_PRODUITS",
           "TS_PHASE", "TS_ID")


def valeurs(d: Diagnostic) -> dict[str, str]:
    problemes = ", ".join(f"{p.label} ({p.intensite_label.lower()})" for p in d.douleurs) or "Aucun"
    priorites = ", ".join(NEEDS[p] for p in d.priorites)
    produits = ", ".join(dict.fromkeys(
        s.produit.nom_complet for s in d.routine if s.produit))
    phase = PHASES[d.phase]
    photo = "oui" if d.photo and d.photo.exploitable else "non"
    ref = str(d.suivi.get("id", ""))[:8]
    return {
        "TS_TYPE": d.type_code,
        "TS_PROBLEMES": problemes,
        "TS_PRIORITES": priorites,
        "TS_PRODUITS": produits,
        "TS_PHASE": phase,
        "TS_ID": ref,
        "TS_RESUME": (f"Type {d.type_code} · Gêne : {problemes} · Priorités : {priorites}"
                      f" · {phase} · Photo : {photo}"
                      f" · Fiabilité {d.fiabilite.get('score', '?')}/100 · Réf. {ref}"),
    }


def lien_avis(url: str, d: Diagnostic) -> str:
    """Remplace les mots-repères du lien pré-rempli par le résultat du diagnostic."""
    if not url or not any(r in url for r in REPERES):
        return url
    parts = urlsplit(url)
    vals = valeurs(d)
    query = [(k, vals.get(v, v)) for k, v in parse_qsl(parts.query, keep_blank_values=True)]
    return urlunsplit(parts._replace(query=urlencode(query)))
