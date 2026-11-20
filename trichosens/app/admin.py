"""Préparation des chiffres du tableau de bord admin (à partir des statistiques anonymes)."""

import csv
import io

from .catalog import load_catalog
from .engine import PHASES
from .hair_types import FAMILLES, HAIR_TYPES
from .pain_points import PAIN_POINTS
from .questionnaire import QUESTIONS_BY_ID, STEPS
from .stats import Statistiques, synthese

PERIODES = (7, 30, 90)


def _options(qid: str) -> dict[str, str]:
    return {o.value: o.label for o in QUESTIONS_BY_ID[qid].options}


def libelles() -> dict[str, dict[str, str]]:
    produits = {p.id: p.nom_complet for p in load_catalog()}
    return {
        "diagnostic_termine": {"adulte": "Adulte", "enfant": "Enfant", "ado": "Ado"},
        "diagnostic_ouvert": {"": "Sans parcours précisé", "adulte": "Adulte", "enfant": "Enfant",
                              "ado": "Ado"},
        "type": {c: f"{c} · {t.nom}" for c, t in HAIR_TYPES.items()},
        "famille": {f: x.label for f, x in FAMILLES.items()},
        "gene": {p: x.label for p, x in PAIN_POINTS.items()},
        "objectif": _options("objectif"),
        "cuir_chevelu": _options("cuir_chevelu"),
        "porosite": {"faible": "Faible", "moyenne": "Moyenne", "forte": "Forte",
                     "inconnue": "Je ne sais pas"},
        "elasticite": _options("elasticite"),
        "budget": _options("budget"),
        "preference": _options("preferences"),
        "age": _options("age"),
        "age_jeune": _options("age_jeune"),
        "fiabilite": {"elevee": "Élevée", "bonne": "Bonne", "a_preciser": "À préciser"},
        "phase": PHASES,
        "etape_vue": {s.id: s.titre for s in STEPS},
        "onglet_resultat": {"synthese": "Synthèse", "problemes": "Problèmes", "routine": "Routine",
                            "produits": "Produits", "naturel": "Naturel",
                            "complements": "Compléments", "conseils": "Conseils",
                            "suivi": "Suivi & rappels"},
        "test_maison": {"epaisseur": "Épaisseur (test du fil)",
                        "densite": "Densité (queue de cheval)",
                        "porosite": "Porosité (verre d'eau)", "elasticite": "Élasticité"},
        "texte_utilise": {"regles": "Analyse par mots-clés", "ia": "Analyse par l'IA"},
        "analyse_texte": {"regles": "Analyse par mots-clés", "ia": "Analyse par l'IA"},
        "aide_type": {"un_type": "Un type trouvé", "deux_types": "Deux types trouvés"},
        "analyse_photo": {"exploitable": "Photo exploitable", "inexploitable": "Photo à refaire"},
        "clic_produit": produits,
    }


def _liste(rep: list[tuple[str, int]], noms: dict[str, str]) -> list[dict]:
    """Lignes d'un classement : libellé, nombre, part du total et largeur de barre."""
    total = sum(n for _, n in rep) or 1
    maxi = max((n for _, n in rep), default=1) or 1
    return [{"label": noms.get(v, v or "—"), "n": n, "part": round(100 * n / total),
             "largeur": round(100 * n / maxi)} for v, n in rep]


def _taux(a: int, b: int) -> str:
    return f"{round(100 * a / b)} %" if b else "—"


def _courbe(points: list, hauteur: int = 140, largeur: int = 640) -> dict:
    """Colonnes d'un graphique en barres (SVG), une par jour."""
    n = len(points) or 1
    maxi = max((v for _, v in points), default=0)
    plafond = max(1, maxi)
    # Graduation ronde : au plus 4 intervalles, sur des nombres ronds.
    pas = next(p for p in (1, 2, 5, 10, 20, 25, 50, 100, 200, 250, 500, 1000, 2000, 5000)
               if plafond <= p * 4)
    plafond = -(-plafond // pas) * pas
    pas_x = largeur / n
    epaisseur = max(2.0, min(24.0, pas_x - 2))
    barres = []
    for i, (jour, v) in enumerate(points):
        h = round(hauteur * v / plafond, 1)
        barres.append({"x": round(i * pas_x + (pas_x - epaisseur) / 2, 1), "y": round(hauteur - h, 1),
                       "l": round(epaisseur, 1), "h": h, "v": v, "jour": jour})
    reperes = [{"y": round(hauteur - hauteur * v / plafond, 1), "v": v}
               for v in range(0, plafond + 1, pas)]
    etiquettes = [points[0][0], points[len(points) // 2][0], points[-1][0]] if points else []
    return {"barres": barres, "reperes": reperes, "largeur": largeur, "hauteur": hauteur,
            "etiquettes": etiquettes, "total": sum(v for _, v in points)}


def tableau(statistiques: Statistiques, jours: int) -> dict:
    s = synthese(statistiques.lire(jours), jours)
    t, rep = s["totaux"], s["repartition"]
    noms = libelles()
    ouverts, termines = t["diagnostic_ouvert"], t["diagnostic_termine"]
    revenus = sum(n for v, n in rep.get("phase", []) if v in {"entretien", "ajustement"})

    # Entonnoir : étapes dans l'ordre du parcours, rapportées à la première.
    vues = dict(rep.get("etape_vue", []))
    etapes = [(st.id, st.titre, vues.get(st.id, 0)) for st in STEPS if vues.get(st.id)]
    premiere = etapes[0][2] if etapes else 0
    entonnoir = [{"label": titre, "n": n, "part": round(100 * n / premiere) if premiere else 0}
                 for _, titre, n in etapes]

    def liste(evt: str) -> list[dict]:
        return _liste(rep.get(evt, []), noms.get(evt, {}))

    return {
        "jours": jours,
        "periodes": PERIODES,
        "persistant": statistiques.stockage.persistant,
        "erreur": statistiques.erreur,
        "depuis": statistiques.depuis,
        "chiffres": [
            {"label": "Visites de l'accueil", "valeur": t["visite_accueil"]},
            {"label": "Diagnostics commencés", "valeur": ouverts},
            {"label": "Diagnostics terminés", "valeur": termines,
             "detail": f"{_taux(termines, ouverts)} des diagnostics commencés"},
            {"label": "Clics vers les produits", "valeur": t["clic_produit"],
             "detail": f"{_taux(t['clic_produit'], termines)} par diagnostic terminé"
             if termines else ""},
            {"label": "Personnes qui reviennent", "valeur": revenus,
             "detail": "diagnostic refait sur le même appareil"},
            {"label": "Avis donnés (clics)", "valeur": t["avis_clic"]},
            {"label": "Fiches PDF et partages", "valeur": t["fiche_pdf"] + t["partage"]},
            {"label": "Rappels ajoutés à l'agenda", "valeur": t["rappels_telecharges"]},
        ],
        "courbe": _courbe(s["courbe"].get("diagnostic_termine",
                                          [(j, 0) for j in s["calendrier"]])),
        "entonnoir": entonnoir,
        "sections": [
            ("Parcours", liste("diagnostic_termine")),
            ("Types de cheveux", liste("type")),
            ("Familles", liste("famille")),
            ("Gênes signalées", liste("gene")),
            ("Objectifs", liste("objectif")),
            ("Cuir chevelu", liste("cuir_chevelu")),
            ("Fiabilité des diagnostics", liste("fiabilite")),
            ("Porosité", liste("porosite")),
            ("Élasticité", liste("elasticite")),
            ("Tests maison faits", liste("test_maison")),
            ("Texte libre utilisé", liste("texte_utilise")),
            ("Aide « Je ne suis pas sûre de mon type »", liste("aide_type")),
            ("Onglets du résultat consultés", liste("onglet_resultat")),
            ("Produits les plus cliqués", liste("clic_produit")[:15]),
            ("Revendeurs", liste("clic_marchand")),
            ("Âge (adultes)", liste("age")),
            ("Âge (enfants et ados)", liste("age_jeune")),
            ("Budget", liste("budget")),
            ("Préférences", liste("preference")),
            ("Programme (première fois ou retour)", liste("phase")),
            ("Analyses photo", liste("analyse_photo")),
        ],
        "erreurs_formulaire": t["erreur_formulaire"],
    }


def export_csv(statistiques: Statistiques, jours: int) -> str:
    """Toutes les lignes brutes (jour, événement, valeur, nombre) pour Excel ou Google Sheets."""
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=";")
    w.writerow(["jour", "evenement", "valeur", "nombre"])
    for jour, evt, val, n in sorted(statistiques.lire(jours)):
        w.writerow([jour.isoformat(), evt, val, n])
    return sortie.getvalue()
