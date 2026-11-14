"""Alternatives naturelles : recettes maison, cures de compléments et gestes naturels.

Les ingrédients à acheter et les compléments sont des produits du catalogue
(catégories « ingredient » et « complement ») : leurs liens d'achat passent par
`/acheter/...`, comme les autres produits.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .catalog import Product
    from .questionnaire import Answers

Condition = Callable[["Answers"], bool]

BOUCLES = {"ondule", "boucle", "frise", "crepu"}


def _toujours(a: "Answers") -> bool:
    return True


def _pas_enceinte(a: "Answers") -> bool:
    return "grossesse" not in a.periodes


def _cuir_calme(a: "Answers") -> bool:
    return (a.cuir_chevelu != "sensible" and "rougeurs" not in a.demangeaisons_details
            and "plaques" not in a.demangeaisons_details)


@dataclass(frozen=True)
class Recette:
    id: str
    titre: str
    # Étape de la routine que la recette peut remplacer (catégorie de produit).
    categorie: str
    besoins: tuple[str, ...]
    # (ingrédient, identifiant du produit à acheter, ou "" si on l'a dans sa cuisine)
    ingredients: tuple[tuple[str, str], ...]
    etapes: tuple[str, ...]
    frequence: str
    conservation: str = ""
    precaution: str = ""
    pour: Condition = _toujours
    douleurs: tuple[str, ...] = ()


RECETTES: dict[str, Recette] = {r.id: r for r in (
    Recette(
        "gel_lin", "Gel de lin maison", "coiffant", ("definition",),
        (("2 cuillères à soupe de graines de lin", "divers-graines-lin"),
         ("25 cl d'eau", ""),
         ("1 cuillère à café de gel d'aloe vera (facultatif)", "aromazone-aloe")),
        ("Faites frémir les graines dans l'eau 8 à 10 minutes en remuant.",
         "Arrêtez quand le mélange a la consistance d'un blanc d'œuf.",
         "Filtrez aussitôt (passoire fine ou collant), laissez refroidir, ajoutez l'aloe vera.",
         "Appliquez par sections sur cheveux trempés, comme un gel."),
        "À chaque lavage, à la place du coiffant.",
        conservation="1 semaine au réfrigérateur, dans un pot propre.",
        pour=lambda a: a.texture in BOUCLES,
        douleurs=("definition", "frisottis"),
    ),
    Recette(
        "spray_aloe", "Spray hydratant à l'aloe vera", "leave_in", ("hydratation",),
        (("3 cuillères à soupe de gel d'aloe vera", "aromazone-aloe"),
         ("1 cuillère à café de glycérine végétale", "aromazone-glycerine"),
         ("15 cl d'eau minérale", "")),
        ("Mélangez le tout dans un flacon vaporisateur propre.",
         "Vaporisez sur les longueurs humides ou entre deux lavages, puis froissez."),
        "Après le lavage et pour réhydrater entre deux lavages.",
        conservation="5 jours au réfrigérateur (sans conservateur).",
        precaution="Par temps très sec (chauffage, grand froid), mettez moitié moins de "
                   "glycérine : elle pourrait assécher au lieu d'hydrater.",
        douleurs=("secheresse", "frisottis"),
    ),
    Recette(
        "masque_aloe_miel", "Masque hydratant aloe vera et miel", "masque", ("hydratation",),
        (("3 cuillères à soupe de gel d'aloe vera", "aromazone-aloe"),
         ("1 cuillère à soupe de miel", ""),
         ("1 cuillère à soupe d'huile de jojoba ou de coco", "aromazone-jojoba")),
        ("Mélangez jusqu'à obtenir une texture lisse.",
         "Appliquez sur cheveux humides, des longueurs aux pointes.",
         "Couvrez d'un bonnet ou d'une serviette chaude, laissez poser 20 à 30 minutes, "
         "puis rincez et lavez."),
        "1 fois par semaine, à la place du masque.",
        conservation="À préparer juste avant l'emploi.",
        douleurs=("secheresse", "frisottis", "demelage"),
    ),
    Recette(
        "masque_avocat", "Masque nourrissant avocat et huile", "masque", ("nutrition",),
        (("½ avocat bien mûr", ""),
         ("1 cuillère à soupe d'huile de coco", "aromazone-coco"),
         ("1 cuillère à soupe de miel", "")),
        ("Mixez finement : les morceaux d'avocat se rincent mal.",
         "Appliquez sur les longueurs, laissez poser 30 minutes sous un bonnet.",
         "Rincez abondamment, puis faites votre shampoing."),
        "1 fois par semaine ou tous les 15 jours.",
        conservation="À préparer juste avant l'emploi.",
        pour=lambda a: a.texture in {"boucle", "frise", "crepu"} or a.epaisseur == "epais",
        douleurs=("secheresse", "pointes", "terne"),
    ),
    Recette(
        "masque_oeuf", "Masque fortifiant œuf et yaourt", "masque", ("proteines", "reparation"),
        (("1 œuf", ""), ("2 cuillères à soupe de yaourt nature", "")),
        ("Battez l'œuf et le yaourt ensemble.",
         "Appliquez sur les longueurs, laissez poser 20 minutes.",
         "Rincez à l'eau fraîche ou tiède, jamais chaude (l'œuf cuirait), puis lavez."),
        "1 fois toutes les 2 semaines au plus.",
        conservation="À préparer juste avant l'emploi.",
        precaution="Si vos cheveux deviennent rêches ou cassants, ils ont reçu trop de "
                   "protéines : espacez et revenez à un masque hydratant.",
        douleurs=("casse", "pointes"),
    ),
    Recette(
        "bain_huile", "Bain d'huile avant le shampoing", "huile", ("nutrition", "reparation"),
        (("Huile de coco (cheveux épais, frisés, crépus)", "aromazone-coco"),
         ("ou huile de jojoba (cheveux fins)", "aromazone-jojoba")),
        ("Appliquez l'huile sur les longueurs sèches ou légèrement humides.",
         "Laissez poser 30 minutes, ou toute une nuit sous un bonnet.",
         "Faites ensuite votre shampoing habituel."),
        "1 fois par semaine, avant le lavage.",
        douleurs=("secheresse", "pointes", "casse"),
    ),
    Recette(
        "lavage_rhassoul", "Lavage au rhassoul", "shampoing", ("cuir_chevelu",),
        (("2 à 3 cuillères à soupe de rhassoul", "aromazone-rhassoul"),
         ("Eau tiède", "")),
        ("Mélangez avec de l'eau tiède jusqu'à obtenir une pâte fluide.",
         "Appliquez sur le cuir chevelu et les longueurs mouillés, massez doucement.",
         "Laissez poser 5 minutes, puis rincez très longtemps."),
        "1 lavage sur 2, en alternance avec votre shampoing.",
        conservation="Poudre : se garde au sec. Pâte : à préparer à chaque fois.",
        pour=lambda a: a.cuir_chevelu in {"normal", "gras", "pellicules"},
        douleurs=("alourdis", "demangeaisons", "pellicules"),
    ),
    Recette(
        "rincage_cidre", "Rinçage au vinaigre de cidre", "shampoing_clarifiant",
        ("nutrition",),
        (("1 cuillère à soupe de vinaigre de cidre", "divers-vinaigre-cidre"),
         ("50 cl d'eau", "")),
        ("Après le shampoing et le soin, versez le mélange sur les longueurs.",
         "Laissez agir 1 minute, puis rincez légèrement à l'eau fraîche."),
        "1 fois par semaine ou après un lavage au rhassoul.",
        precaution="À éviter sur un cuir chevelu irrité ou avec des plaies.",
        pour=_cuir_calme,
        douleurs=("terne", "alourdis", "demelage", "pellicules"),
    ),
    Recette(
        "lotion_romarin", "Massage du cuir chevelu au romarin", "soin_cuir", ("cuir_chevelu",),
        (("Hydrolat de romarin à verbénone", "aromazone-hydrolat-romarin"),
         ("Quelques gouttes d'huile de ricin pour les tempes (facultatif)", "aromazone-ricin")),
        ("Vaporisez l'hydrolat raie par raie sur le cuir chevelu propre.",
         "Massez du bout des doigts 3 à 5 minutes, en petits cercles.",
         "Sur les tempes clairsemées, ajoutez une goutte d'huile de ricin."),
        "3 fois par semaine, pendant au moins 3 mois.",
        conservation="Hydrolat : au réfrigérateur après ouverture, 2 mois environ.",
        precaution="Déconseillé pendant la grossesse, l'allaitement et chez l'enfant.",
        pour=lambda a: _pas_enceinte(a) and "post_partum" not in a.periodes
        and a.age != "moins_18" and _cuir_calme(a),
        douleurs=("chute", "pousse"),
    ),
    Recette(
        "aloe_cuir", "Soin apaisant à l'aloe vera pour le cuir chevelu", "soin_cuir",
        ("cuir_chevelu",),
        (("Gel d'aloe vera pur", "aromazone-aloe"),),
        ("Testez d'abord une noisette dans le pli du coude, 24 heures avant.",
         "Appliquez raie par raie sur le cuir chevelu, sans masser fort.",
         "Laissez poser 30 minutes, puis lavez avec un shampoing doux."),
        "1 à 2 fois par semaine, tant que le cuir chevelu démange.",
        conservation="Au réfrigérateur après ouverture : effet fraîcheur garanti.",
        pour=lambda a: "plaques" not in a.demangeaisons_details,
        douleurs=("demangeaisons", "pellicules"),
    ),
    Recette(
        "eau_riz", "Eau de riz", "apres_shampoing", ("proteines",),
        (("3 cuillères à soupe de riz", ""), ("50 cl d'eau", "")),
        ("Rincez le riz, puis laissez-le tremper 30 minutes dans l'eau.",
         "Filtrez : c'est l'eau qu'on utilise.",
         "Après le shampoing, versez-la sur les longueurs, laissez agir 5 à 10 minutes, rincez."),
        "1 fois toutes les 2 semaines.",
        conservation="24 heures au réfrigérateur.",
        precaution="Riche en amidon et en protéines : sur une porosité faible, elle peut "
                   "rigidifier les cheveux. Arrêtez s'ils deviennent rêches.",
        pour=lambda a: a.porosite != "faible",
        douleurs=("casse", "pousse"),
    ),
)}


def recettes_pour(a: "Answers", besoins: dict[str, int],
                  categories_routine: set[str], nombre: int = 4) -> list[Recette]:
    """Les recettes les plus utiles pour ce profil, une par étape de routine au plus."""
    notes = []
    for r in RECETTES.values():
        if not r.pour(a):
            continue
        score = sum(besoins.get(b, 0) for b in r.besoins) / len(r.besoins)
        if r.categorie in categories_routine:
            score += 20
        score += 15 * len(set(r.douleurs) & set(a.preoccupations))
        notes.append((score, r))
    notes.sort(key=lambda x: -x[0])
    choisies: list[Recette] = []
    for _, r in notes:
        if r.categorie not in {c.categorie for c in choisies}:
            choisies.append(r)
        if len(choisies) == nombre:
            break
    return choisies


# --- Cures de compléments alimentaires --------------------------------------------

@dataclass
class Cure:
    titre: str
    pourquoi: str
    duree: str
    produits: list[str] = field(default_factory=list)


AVERTISSEMENT_CURE = (
    "Un complément alimentaire ne remplace pas une alimentation variée. Respectez la dose "
    "indiquée, ne cumulez pas plusieurs compléments qui contiennent les mêmes vitamines, et "
    "demandez conseil à votre pharmacien ou médecin, surtout si vous prenez un traitement."
)

DECLENCHEURS = {"chute", "casse", "pousse", "terne", "pointes"}
CARENCES = {"carence_fer", "carence_vitd", "carence_autre", "regime"}
PERIODES_CURE = {"post_partum", "stress", "menopause"}


def cures_pour(a: "Answers", saison: str | None = None) -> tuple[list[Cure], str]:
    """Cures conseillées et message de prudence (ou raison de ne rien proposer)."""
    if "grossesse" in a.periodes:
        return [], ("Pendant la grossesse, ne prenez aucun complément alimentaire sans l'avis "
                    "de votre médecin ou de votre sage-femme : certains sont déconseillés.")
    if a.age == "moins_18":
        return [], ("Avant 18 ans, une alimentation variée suffit en général. Parlez-en à votre "
                    "médecin avant de prendre un complément.")
    from .sante import FACTEURS
    facteurs = [FACTEURS[f] for f in a.sante if f != "aucun"]
    bloquants = [f for f in facteurs if f.sans_cure]
    if bloquants:
        return [], (bloquants[0].note_cure or
                    "Parlez-en au médecin qui suit votre maladie avant de prendre un "
                    "complément alimentaire : certains interagissent avec les traitements.")
    raisons = set(a.preoccupations) & DECLENCHEURS
    periodes = set(a.periodes) & PERIODES_CURE
    carences = set(a.sante) & CARENCES
    automne = saison == "automne" and "chute_automne" in a.saisons_sensibles
    if not (raisons or periodes or automne or carences):
        return [], ""

    pourquoi = ("La biotine, le zinc et le sélénium contribuent au maintien de cheveux "
                "normaux ; les acides aminés soufrés (cystine, méthionine) sont les briques de "
                "la kératine.")
    if automne:
        pourquoi += " Une cure en septembre-octobre accompagne la chute saisonnière."
    cures = [
        Cure("Cure fortifiante cheveux", pourquoi, "3 mois (la durée d'un cycle de pousse).",
             ["arkopharma-forcapil", "phyto-phytophanere"]),
        Cure("Alternative naturelle : levure de bière",
             "Riche en vitamines du groupe B, la levure de bière est la cure la plus simple "
             "et la plus économique.", "3 mois.", ["divers-levure-biere"]),
    ]
    if "carence_fer" in a.sante:
        cures.insert(0, Cure(
            "Fer, sur avis médical",
            "Le fer contribue à la formation normale des globules rouges et à réduire la "
            "fatigue ; corriger un manque est souvent la clé d'une chute chez les femmes. Le "
            "fer bisglycinate est en général mieux toléré.",
            "La durée fixée par votre médecin (souvent 3 mois), avec un nouveau dosage ensuite.",
            ["divers-fer-bisglycinate"]))
    if "carence_vitd" in a.sante:
        cures.insert(0, Cure(
            "Vitamine D, après dosage",
            "La vitamine D contribue au fonctionnement normal du système immunitaire. Un "
            "manque est fréquent en hiver.",
            "La dose et la durée indiquées par votre médecin.", ["divers-vitamine-d3"]))
    if {"carence_autre", "regime"} & set(a.sante):
        cures.append(Cure(
            "Zinc",
            "Le zinc contribue au maintien de cheveux et d'ongles normaux. Ne le cumulez pas "
            "avec une cure fortifiante qui en contient déjà.",
            "2 à 3 mois.", ["divers-zinc"]))
    message = AVERTISSEMENT_CURE
    notes = [f.note_cure for f in facteurs if f.note_cure]
    if {"fatigue", "regles_abondantes"} & set(a.sante) and "carence_fer" not in a.sante:
        notes.append("Fatigue ou règles abondantes : faites doser votre ferritine avant de "
                     "prendre du fer.")
    if notes:
        message = " ".join(notes) + " " + message
    if "post_partum" in a.periodes:
        message = ("Si vous allaitez, demandez l'avis de votre médecin ou de votre sage-femme "
                   "avant toute cure. " + message)
    if "traitement" in a.periodes:
        message = ("Vous suivez un nouveau traitement : vérifiez avec votre pharmacien qu'il "
                   "n'y a pas d'interaction. " + message)
    if "chute" in a.preoccupations:
        message += (" Si la chute est importante, un bilan sanguin (fer et ferritine, "
                    "vitamine D, thyroïde) permet d'en trouver la cause : ne prenez pas de fer "
                    "sans carence confirmée.")
    return cures, message


# --- Gestes naturels au quotidien -------------------------------------------------

def conseils_naturels(a: "Answers") -> list[str]:
    conseils = [
        "Dans l'assiette : des protéines à chaque repas (œufs, légumineuses, poisson), du fer "
        "(lentilles, viande rouge, épinards avec une source de vitamine C), du zinc (graines "
        "de courge, fruits de mer) et des oméga-3 (poissons gras, noix, huile de colza).",
        "Buvez régulièrement dans la journée : un corps déshydraté se voit aussi sur les "
        "cheveux.",
    ]
    if set(a.preoccupations) & {"chute", "pousse"} or a.objectif == "longueur":
        conseils.append("Massez votre cuir chevelu 5 minutes par jour, du bout des doigts : "
                        "c'est gratuit et cela entretient la circulation.")
    if "stress" in a.periodes or "chute" in a.preoccupations:
        conseils.append("Le stress et le manque de sommeil font tomber les cheveux 2 à 3 mois "
                        "plus tard : marche, respiration, coucher régulier aident aussi vos "
                        "cheveux.")
    if a.texture in BOUCLES:
        conseils.append("Une taie d'oreiller en soie ou en satin garde l'hydratation de vos "
                        "boucles pendant la nuit, sans aucun produit.")
    return conseils


def produits_recette(r: Recette, catalog: list["Product"]) -> list[tuple[str, "Product | None"]]:
    par_id = {p.id: p for p in catalog}
    return [(texte, par_id.get(pid)) for texte, pid in r.ingredients]
