"""Moteur de diagnostic TrichoSens.

À partir des réponses au questionnaire, le moteur :
1. calcule les besoins du cheveu (hydratation, protéines, etc.) sur 100 ;
2. construit une routine de soins adaptée ;
3. choisit, pour chaque étape, le produit du catalogue qui convient le mieux ;
4. ajoute des conseils et, si besoin, des alertes santé.

Les règles sont volontairement simples et lisibles : elles pourront être
affinées avec des experts (trichologues, coiffeurs) puis avec les données.
"""

import datetime as dt
import uuid
from dataclasses import dataclass, field

from . import naturel, profil, sante, seasons
from .reminders import jours_suggeres
from .catalog import Product, load_catalog
from .evolution import Evolution, ResumeSuivi, compare
from .hair_types import FAMILLES, HAIR_TYPES, TYPE_POIDS, TYPE_POINTS, HairType
from .pain_points import INTENSITE_FACTEUR, PAIN_POINTS, PainReport, explain
from .photo import AnalysePhoto
from .photo import is_enabled as photo_disponible
from .questionnaire import Answers
from .specifiques import DETAILS_DEMANGEAISONS, SPECIFICITES

# --- Besoins -----------------------------------------------------------------

NEEDS: dict[str, str] = {
    "hydratation": "Hydratation",
    "nutrition": "Nutrition",
    "proteines": "Protéines",
    "reparation": "Réparation",
    "cuir_chevelu": "Soin du cuir chevelu",
    "protection": "Protection thermique",
    "definition": "Définition des boucles",
    "volume": "Volume",
}

# Un score brut de MAX_RAW (ou plus) correspond à un besoin de 100/100.
MAX_RAW = 10

TEXTURE_POINTS = {
    "lisse": {"hydratation": 1},
    "ondule": {"hydratation": 2, "definition": 1},
    "boucle": {"hydratation": 3, "nutrition": 2, "definition": 2},
    "frise": {"hydratation": 4, "nutrition": 3, "definition": 2, "reparation": 1},
    "crepu": {"hydratation": 5, "nutrition": 4, "definition": 1, "reparation": 1},
}

EPAISSEUR_POINTS = {
    "fin": {"proteines": 1, "volume": 1},
    "moyen": {},
    "epais": {"nutrition": 1},
}

POROSITE_POINTS = {
    "faible": {"hydratation": 1},
    "moyenne": {},
    "forte": {"hydratation": 2, "nutrition": 2, "proteines": 2},
    "inconnue": {},
}

ELASTICITE_POINTS = {
    "equilibre": {},
    "manque_proteines": {"proteines": 4, "reparation": 1},
    "manque_hydratation": {"hydratation": 4, "nutrition": 1},
    "non_teste": {},
}

CUIR_POINTS = {
    "normal": {},
    "sec": {"cuir_chevelu": 2, "hydratation": 1},
    "gras": {"cuir_chevelu": 3},
    "sensible": {"cuir_chevelu": 4},
    "pellicules": {"cuir_chevelu": 4},
}

PREOCCUPATION_POINTS = {
    "secheresse": {"hydratation": 3, "nutrition": 2},
    "casse": {"proteines": 3, "reparation": 3},
    "frisottis": {"hydratation": 2, "nutrition": 2, "definition": 1},
    "chute": {"cuir_chevelu": 3},
    "pointes": {"reparation": 3, "nutrition": 1},
    "volume": {"volume": 5},
    "definition": {"definition": 5, "hydratation": 1},
    "pousse": {"cuir_chevelu": 2, "reparation": 1},
    "terne": {"nutrition": 3},
    "demelage": {"hydratation": 2, "nutrition": 2},
    "alourdis": {"volume": 2},
    "demangeaisons": {"cuir_chevelu": 5},
    "pellicules": {"cuir_chevelu": 5},
    "poux": {"cuir_chevelu": 3},
    "croutes_lait": {"cuir_chevelu": 3},
}

COIFFURE_POINTS = {
    "serrees": {"reparation": 1},
    "rajouts": {"reparation": 1, "cuir_chevelu": 1},
    "laches": {},
    "piscine": {"hydratation": 2, "proteines": 1},
    "casque": {"cuir_chevelu": 1},
}

AGES_JEUNES = {"bebe": "moins de 3 ans", "petit": "3 à 5 ans", "enfant": "6 à 11 ans",
               "ado_jeune": "12 à 14 ans", "ado": "15 à 17 ans"}

# Part du second type quand les cheveux mélangent deux types.
PART_SECONDAIRE = 0.35

# Poids des signes vus sur la photo : ils complètent les réponses sans les remplacer.
PHOTO_FACTEUR = {"leger": 0.3, "modere": 0.5, "marque": 0.8}

TRAITEMENT_POINTS = {
    "coloration": {"reparation": 1, "proteines": 1, "nutrition": 1},
    "decoloration": {"reparation": 4, "proteines": 3, "hydratation": 1},
    "lissage": {"reparation": 3, "proteines": 2},
    "permanente": {"reparation": 2, "proteines": 1, "hydratation": 1},
}

CHALEUR_POINTS = {
    "jamais": {},
    "parfois": {"protection": 4},
    "souvent": {"protection": 8, "reparation": 2},
}

OBJECTIF_POINTS = {
    "hydratation": {"hydratation": 3},
    "definition": {"definition": 4},
    "volume": {"volume": 4},
    "longueur": {"reparation": 2, "proteines": 2},
    "sante_cuir": {"cuir_chevelu": 4},
    "brillance": {"nutrition": 3},
    "demelage": {"hydratation": 3, "nutrition": 1},
    "autonomie": {},
}


def compute_needs(a: Answers, photo: AnalysePhoto | None = None,
                  saison: seasons.Saison | None = None) -> dict[str, int]:
    """Renvoie un score de 0 à 100 pour chaque besoin."""
    raw: dict[str, float] = dict.fromkeys(NEEDS, 0.0)

    def add(points: dict[str, int], factor: float = 1.0) -> None:
        for need, value in points.items():
            raw[need] += value * factor

    sec = HAIR_TYPES.get(a.type_secondaire)
    part = PART_SECONDAIRE if sec else 0.0
    add(TEXTURE_POINTS[a.texture], 1 - part)
    add(TYPE_POINTS[a.type_cheveux], 1 - part)
    if sec:
        add(TEXTURE_POINTS[sec.texture], part)
        add(TYPE_POINTS[sec.code], part)
    for sid in a.specifiques:
        add(SPECIFICITES[sid].points)
    for pts in sante.points(a):
        add(pts)
    for c in a.coiffures:
        add(COIFFURE_POINTS[c])
    for did in a.demangeaisons_details:
        add(DETAILS_DEMANGEAISONS[did].points)
    if saison:
        add(saison.points)
    for pts in profil.points(a, saison):
        add(pts)
    add(EPAISSEUR_POINTS[a.epaisseur])
    add(POROSITE_POINTS[a.porosite])
    add(ELASTICITE_POINTS[a.elasticite])
    add(CUIR_POINTS[a.cuir_chevelu])
    add(CHALEUR_POINTS[a.chaleur])
    add(OBJECTIF_POINTS[a.objectif])
    for p in a.preoccupations:
        add(PREOCCUPATION_POINTS[p], INTENSITE_FACTEUR[a.intensites.get(p, "beaucoup")])
    if photo and photo.exploitable:
        for s in photo.signes:
            add(PREOCCUPATION_POINTS[s.signe], PHOTO_FACTEUR[s.intensite])
    for t in a.traitements:
        add(TRAITEMENT_POINTS[t])

    if a.epaisseur == "fin" and a.densite == "faible":
        raw["volume"] += 2

    return {need: min(100, round(100 * value / MAX_RAW)) for need, value in raw.items()}


# --- Résultat ----------------------------------------------------------------


@dataclass
class Step:
    moment: str  # "lavage", "quotidien", "hebdomadaire", "nuit"
    titre: str
    conseil: str
    categorie: str | None = None
    produit: Product | None = None
    hors_preferences: list[str] = field(default_factory=list)
    # Produit précis à proposer s'il convient (ex. le bonnet en satin pour la nuit).
    produit_id: str | None = None
    # Recette maison qui peut remplacer le produit de cette étape.
    alternative: naturel.Recette | None = None


@dataclass
class Diagnostic:
    resume: str
    texture: str
    type_cheveux: HairType
    problemes_type: list[dict]
    besoins: dict[str, int]
    priorites: list[str]
    frequence_lavage: str
    poids_produits: str
    routine: list[Step]
    saison: seasons.Saison | None = None
    conseils_saison: list[str] = field(default_factory=list)
    conseils_vie: list[str] = field(default_factory=list)
    prochaine_saison: seasons.Saison | None = None
    anticipation: list[str] = field(default_factory=list)
    phase: str = "intensive"
    programme: list[dict] = field(default_factory=list)
    prochain_point: dt.date | None = None
    evolution: Evolution | None = None
    suivi: dict = field(default_factory=dict)
    cout_total: float = 0.0
    jours_lavage: list[str] = field(default_factory=list)
    prenom: str = ""
    liens_affilies: bool = False
    liens_amazon: bool = False
    preferences: list[str] = field(default_factory=list)
    budget: str = "indifferent"
    douleurs: list[PainReport] = field(default_factory=list)
    conseils: list[str] = field(default_factory=list)
    alertes: list[str] = field(default_factory=list)
    photo: AnalysePhoto | None = None
    notes_photo: list[str] = field(default_factory=list)
    signes_photo_en_plus: list[dict] = field(default_factory=list)
    type_secondaire: HairType | None = None
    specifiques: list[dict] = field(default_factory=list)
    # Fiabilité : score sur 100, niveau, ce qui l'améliorerait, réponses à vérifier.
    fiabilite: dict = field(default_factory=dict)
    # Santé : facteurs, professionnels à consulter, examens à demander.
    orientation: dict = field(default_factory=dict)
    pour: str = "adulte"
    # Coffret routine vendu par TrichoSens, s'il en existe un adapté au profil.
    coffret: Product | None = None
    # Alternatives naturelles : recettes maison, cures et gestes du quotidien.
    recettes: list[dict] = field(default_factory=list)
    cures: list[dict] = field(default_factory=list)
    cures_message: str = ""
    conseils_naturels: list[str] = field(default_factory=list)

    @property
    def type_code(self) -> str:
        """Code du type, avec le second type s'il y en a un (ex. « 3B/3C »)."""
        if self.type_secondaire:
            return f"{self.type_cheveux.code}/{self.type_secondaire.code}"
        return self.type_cheveux.code

    def to_dict(self) -> dict:
        return {
            "resume": self.resume,
            "texture": self.texture,
            "type_cheveux": self.type_cheveux.code,
            "type_secondaire": self.type_secondaire.code if self.type_secondaire else None,
            "specifiques": self.specifiques,
            "fiabilite": self.fiabilite,
            "orientation": self.orientation,
            "pour": self.pour,
            "coffret": self.coffret.to_dict() if self.coffret else None,
            "recettes": [
                {"id": r["recette"].id, "titre": r["recette"].titre,
                 "remplace": r["recette"].categorie,
                 "ingredients": [{"texte": t, "produit": p.to_dict() if p else None}
                                 for t, p in r["ingredients"]],
                 "etapes": list(r["recette"].etapes), "frequence": r["recette"].frequence,
                 "conservation": r["recette"].conservation,
                 "precaution": r["recette"].precaution}
                for r in self.recettes
            ],
            "cures": [{"titre": c["cure"].titre, "pourquoi": c["cure"].pourquoi,
                       "duree": c["cure"].duree,
                       "produits": [p.to_dict() for p in c["produits"]]} for c in self.cures],
            "cures_message": self.cures_message,
            "conseils_naturels": self.conseils_naturels,
            "problemes_type": self.problemes_type,
            "douleurs": [d.to_dict() for d in self.douleurs],
            "saison": self.saison.id if self.saison else None,
            "conseils_saison": self.conseils_saison,
            "conseils_vie": self.conseils_vie,
            "prochaine_saison": self.prochaine_saison.id if self.prochaine_saison else None,
            "anticipation": self.anticipation,
            "phase": self.phase,
            "programme": self.programme,
            "prochain_point": self.prochain_point.isoformat() if self.prochain_point else None,
            "evolution": {
                "depuis": self.evolution.depuis.isoformat(),
                "jours": self.evolution.jours,
                "changements": [c.__dict__ for c in self.evolution.changements],
                "besoins_deltas": self.evolution.besoins_deltas,
                "messages": self.evolution.messages,
            } if self.evolution else None,
            "suivi": self.suivi,
            "cout_total": self.cout_total,
            "jours_lavage": self.jours_lavage,
            "preferences": self.preferences,
            "budget": self.budget,
            "photo": self.photo.model_dump() if self.photo else None,
            "notes_photo": self.notes_photo,
            "signes_photo_en_plus": self.signes_photo_en_plus,
            "besoins": self.besoins,
            "priorites": self.priorites,
            "frequence_lavage": self.frequence_lavage,
            "poids_produits": self.poids_produits,
            "routine": [
                {
                    "moment": s.moment,
                    "titre": s.titre,
                    "conseil": s.conseil,
                    "categorie": s.categorie,
                    "produit": s.produit.to_dict() if s.produit else None,
                    "hors_preferences": s.hors_preferences,
                }
                for s in self.routine
            ],
            "conseils": self.conseils,
            "alertes": self.alertes,
        }


MOMENTS = {
    "lavage": "Le jour du lavage",
    "quotidien": "Au quotidien",
    "hebdomadaire": "Chaque semaine ou chaque mois",
    "nuit": "La nuit",
}


CUIR_LABELS = {"normal": "normal", "sec": "sec", "gras": "gras", "sensible": "sensible",
               "pellicules": "avec pellicules"}


def _resume(a: Answers) -> str:
    t = HAIR_TYPES[a.type_cheveux]
    epaisseur = {"fin": "cheveu fin", "moyen": "cheveu d'épaisseur moyenne",
                 "epais": "cheveu épais"}[a.epaisseur]
    type_txt = f"{FAMILLES[t.famille].label}, type {t.code} ({t.nom.lower()})"
    if a.type_secondaire:
        type_txt += f" avec une part de {a.type_secondaire}"
    parts = [type_txt, epaisseur, f"densité {a.densite}"]
    if a.porosite != "inconnue":
        parts.append(f"porosité {a.porosite}")
    parts.append(f"cuir chevelu {CUIR_LABELS[a.cuir_chevelu]}")
    if a.pour != "adulte":
        qui = "Enfant" if a.pour == "enfant" else "Ado"
        age = f" de {AGES_JEUNES[a.age_jeune]}" if a.age_jeune in AGES_JEUNES else ""
        parts[0] = f"{qui}{age} · {parts[0]}"
    if "demangeaisons" in a.preoccupations:
        parts[-1] += " qui démange"
    return ", ".join(parts) + "."


def _frequence_lavage(a: Answers) -> str:
    if a.pour == "enfant":
        if a.age_jeune == "bebe":
            return "1 à 2 fois par semaine, avec un shampoing pour bébé"
        return {
            "lisse": "1 à 2 fois par semaine, et après la piscine",
            "ondule": "1 à 2 fois par semaine",
            "boucle": "1 fois par semaine",
            "frise": "1 fois par semaine",
            "crepu": "1 fois par semaine à tous les 10 jours",
        }[a.texture]
    return _frequence_adulte(a)


def _frequence_adulte(a: Answers) -> str:
    base = {
        "lisse": "2 à 3 fois par semaine",
        "ondule": "2 fois par semaine",
        "boucle": "1 à 2 fois par semaine",
        "frise": "1 fois par semaine",
        "crepu": "1 fois par semaine à tous les 10 jours",
    }[a.texture]
    if a.cuir_chevelu == "gras":
        faster = {
            "lisse": "tous les 1 à 2 jours, avec un shampoing doux",
            "ondule": "2 à 3 fois par semaine",
            "boucle": "2 fois par semaine",
            "frise": "1 à 2 fois par semaine",
            "crepu": "1 fois par semaine",
        }[a.texture]
        return faster
    return base


def lavages_par_semaine(a: Answers) -> float:
    """Nombre de lavages par semaine conseillé (pour proposer des jours de rappel)."""
    if a.cuir_chevelu == "gras":
        return {"lisse": 4, "ondule": 2.5, "boucle": 2, "frise": 1.5, "crepu": 1}[a.texture]
    return {"lisse": 2.5, "ondule": 2, "boucle": 1.5, "frise": 1, "crepu": 1}[a.texture]


def _poids_produits(a: Answers, saison: seasons.Saison | None = None) -> str:
    """Texture des soins à privilégier : légère, moyenne ou riche."""
    echelle = {"lisse": -2, "ondule": -1, "boucle": 0, "frise": 1, "crepu": 2}
    score: float = echelle[a.texture]
    sec = HAIR_TYPES.get(a.type_secondaire)
    if sec:
        score += PART_SECONDAIRE * (echelle[sec.texture] - echelle[a.texture])
    score += {"fin": -2, "moyen": 0, "epais": 1}[a.epaisseur]
    score += {"faible": -1, "moyenne": 0, "forte": 1, "inconnue": 0}[a.porosite]
    if "alourdis" in a.preoccupations:
        score -= 1
    score += TYPE_POIDS.get(a.type_cheveux, 0)
    score += profil.ajustement_poids(a, saison)
    if score <= -2:
        return "leger"
    if score >= 2:
        return "riche"
    return "moyen"


def cuir_effectif(a: Answers) -> str:
    """Nature du cuir chevelu à traiter en priorité pour choisir les soins.

    Les détails des démangeaisons peuvent révéler des pellicules ou une sensibilité
    que la personne n'a pas cochées dans « cuir chevelu ».
    """
    cuirs = {DETAILS_DEMANGEAISONS[d].cuir for d in a.demangeaisons_details}
    if "pellicules" in a.preoccupations and a.cuir_chevelu in {"normal", "gras", "sec"}:
        return "pellicules"
    if "pellicules" in cuirs and a.cuir_chevelu in {"normal", "gras", "sec"}:
        if a.cuir_chevelu != "sec" or "pellicules_grasses" in a.demangeaisons_details:
            return "pellicules"
    if "sensible" in cuirs and a.cuir_chevelu in {"normal", "sec"}:
        return "sensible"
    return a.cuir_chevelu


def _routine_enfant(a: Answers, besoins: dict[str, int], poids: str) -> list[Step]:
    """Routine courte et douce pour un enfant : peu d'étapes, que des soins adaptés à l'âge."""
    texture_bouclee = a.texture in {"ondule", "boucle", "frise", "crepu"}
    steps: list[Step] = [Step(
        "lavage", "Shampoing doux",
        "Une noisette suffit : massez doucement le cuir chevelu, puis rincez longtemps en "
        "protégeant les yeux.", "shampoing")]
    if a.age_jeune == "bebe":
        if "croutes_lait" in a.preoccupations:
            steps.append(Step(
                "hebdomadaire", "Croûtes de lait",
                "Le soir, une huile végétale douce sur les croûtes ; le lendemain, décollez-les avec "
                "une brosse très douce avant le shampoing.", "huile"))
        return steps
    steps.append(Step(
        "lavage", "Démêlant",
        "Sur les longueurs : démêlez avec un peigne à dents larges, des pointes vers les "
        "racines, par petites mèches, sans tirer. C'est le secret d'un démêlage sans pleurs.",
        "apres_shampoing"))
    if texture_bouclee:
        steps.append(Step("lavage", "Soin sans rinçage",
                          "Sur cheveux encore humides, pour garder l'hydratation et faciliter le "
                          "coiffage.", "leave_in"))
    if a.texture in {"boucle", "frise", "crepu"} and (besoins["definition"] >= 30
                                                      or a.objectif == "definition"):
        steps.append(Step("lavage", "Crème coiffante",
                          "Une petite quantité par sections, pour des boucles définies sans les "
                          "durcir.", "coiffant"))
    if a.texture in {"frise", "crepu"}:
        steps.append(Step("lavage", "Sceller l'hydratation",
                          "Quelques gouttes d'huile ou un peu de beurre sur les longueurs.", "huile"))
    steps.append(Step("lavage", "Séchage",
                      "Essorez dans une serviette douce en tamponnant, sans frotter ; laissez "
                      "sécher à l'air libre, sans sèche-cheveux chaud."))
    if texture_bouclee:
        steps.append(Step("quotidien", "Réhydrater",
                          "Le matin, un peu d'eau ou de soin sans rinçage en spray, puis "
                          "coiffez avec les doigts.", "leave_in"))
    steps.append(Step("quotidien", "Coiffer sans tirer",
                      "Des coiffures souples, des élastiques sans métal, et une pause entre deux "
                      "coiffures serrées pour protéger les tempes."))
    if "poux" in a.preoccupations:
        steps.append(Step("hebdomadaire", "Vérifier les poux",
                          "Une fois par semaine, passez le peigne anti-poux sur cheveux mouillés "
                          "et démêlés, mèche par mèche.", "accessoire",
                          produit_id="divers-peigne-anti-poux"))
    if texture_bouclee or "frisottis" in a.preoccupations:
        steps.append(Step("nuit", "Protéger les cheveux",
                          "Une taie ou un bonnet en satin, et les cheveux rassemblés en tresse "
                          "lâche ou en ananas.", "accessoire", produit_id="bonnet-satin"))
    return steps


def _build_routine(a: Answers, besoins: dict[str, int], poids: str) -> list[Step]:
    if a.pour == "enfant":
        return _routine_enfant(a, besoins, poids)
    boucles = a.texture in {"boucle", "frise", "crepu"}
    texture_bouclee = a.texture in {"ondule", "boucle", "frise", "crepu"}
    steps: list[Step] = []

    # Jour de lavage
    if a.texture in {"frise", "crepu"} or besoins["nutrition"] >= 60:
        steps.append(Step(
            "lavage", "Pré-shampoing",
            "Appliquez une huile ou un soin sur les longueurs 30 minutes avant le lavage "
            "pour protéger la fibre.",
            "huile",
        ))
    cuir = cuir_effectif(a)
    if cuir == "pellicules" or "pellicules_grasses" in a.demangeaisons_details:
        conseil = ("Faites mousser sur le cuir chevelu et laissez poser 3 à 5 minutes avant de "
                   "rincer : c'est ce temps de pose qui agit sur les pellicules.")
    elif cuir in {"sensible", "pellicules", "sec"}:
        conseil = "Massez doucement le cuir chevelu avec la pulpe des doigts, sans frotter les longueurs."
    elif a.cuir_chevelu == "gras":
        conseil = "Concentrez le shampoing sur le cuir chevelu ; la mousse qui coule suffit pour les longueurs."
    else:
        conseil = "Lavez surtout le cuir chevelu ; la mousse qui coule suffit pour les longueurs."
    steps.append(Step("lavage", "Shampoing", conseil, "shampoing"))

    if besoins["proteines"] >= 50 or besoins["reparation"] >= 50 or besoins["hydratation"] >= 50:
        conseil = "Laissez poser 10 à 20 minutes sur les longueurs."
        if a.porosite == "faible":
            conseil += " Une source de chaleur douce (bonnet chauffant, serviette chaude) aide le soin à pénétrer."
        steps.append(Step("lavage", "Masque", conseil, "masque"))
    else:
        steps.append(Step(
            "lavage", "Après-shampoing",
            "Appliquez sur les longueurs et les pointes, laissez poser 2 à 3 minutes puis rincez.",
            "apres_shampoing",
        ))

    if boucles or "demelage" in a.preoccupations:
        steps.append(Step(
            "lavage", "Démêlage",
            "Démêlez sous l'après-shampoing ou le masque, avec les doigts ou un peigne à dents larges, "
            "en partant des pointes.",
        ))

    if texture_bouclee or besoins["hydratation"] >= 50:
        steps.append(Step(
            "lavage", "Soin sans rinçage",
            "Sur cheveux encore humides, pour garder l'hydratation." if boucles
            else "Une petite quantité sur les longueurs encore humides.",
            "leave_in",
        ))

    if texture_bouclee and (besoins["definition"] >= 30 or a.objectif == "definition"):
        steps.append(Step(
            "lavage", "Coiffant",
            "Appliquez par sections sur cheveux trempés, puis froissez vers le haut pour former les boucles.",
            "coiffant",
        ))
    elif besoins["volume"] >= 40:
        steps.append(Step(
            "lavage", "Coiffant volume",
            "Appliquez aux racines sur cheveux humides et séchez tête en bas.",
            "coiffant",
        ))

    if a.porosite == "forte" or a.texture in {"frise", "crepu"}:
        steps.append(Step(
            "lavage", "Sceller l'hydratation",
            "Terminez par quelques gouttes d'huile ou de beurre sur les longueurs pour garder l'hydratation.",
            "huile",
        ))

    if a.chaleur != "jamais":
        steps.append(Step(
            "lavage", "Protection thermique",
            "Toujours avant le sèche-cheveux, le lisseur ou le fer. Restez sous 180 °C.",
            "protecteur_thermique",
        ))

    if texture_bouclee:
        steps.append(Step(
            "lavage", "Séchage",
            "Essorez avec une serviette en microfibre ou un t-shirt en coton, puis séchez à l'air libre "
            "ou au diffuseur à température douce.",
        ))

    # Au quotidien
    if boucles:
        steps.append(Step(
            "quotidien", "Réhydrater",
            "Entre deux lavages, vaporisez un peu d'eau ou de soin sans rinçage dilué, "
            "puis froissez pour redonner forme.",
            "leave_in",
        ))
    if a.cuir_chevelu == "gras":
        steps.append(Step(
            "quotidien", "Cuir chevelu",
            "Évitez de toucher vos racines et n'appliquez pas d'huile près du cuir chevelu.",
        ))
    if {"demangeaisons", "pellicules"} & set(a.preoccupations):
        steps.append(Step(
            "quotidien", "Apaiser sans gratter",
            "Quand ça gratte, appuyez ou massez avec la pulpe des doigts au lieu de gratter avec "
            "les ongles. N'appliquez pas d'huile épaisse sur le cuir chevelu.",
        ))
    if "pointes" in a.preoccupations or "casse" in a.preoccupations:
        steps.append(Step(
            "quotidien", "Protéger les pointes",
            "Une goutte d'huile ou de sérum sur les pointes sèches limite la casse.",
            "huile",
        ))

    # Hebdomadaire / mensuel
    if ("sous_coiffure" in a.demangeaisons_details
            or "lavage_sous_tresses" in a.specifiques):
        steps.append(Step(
            "hebdomadaire", "Laver sous les tresses",
            "Toutes les 1 à 2 semaines, appliquez un shampoing dilué entre les tresses avec un "
            "flacon applicateur, massez, rincez longtemps et séchez bien.",
        ))
    if besoins["cuir_chevelu"] >= 40 or {"demangeaisons", "pellicules"} & set(a.preoccupations):
        steps.append(Step(
            "hebdomadaire", "Soin du cuir chevelu",
            "1 fois par semaine, appliquez un soin adapté et massez 3 à 5 minutes pour stimuler la circulation.",
            "soin_cuir",
        ))
    if (a.porosite == "faible" or a.cuir_chevelu == "gras" or texture_bouclee
            or "alourdis" in a.preoccupations or "entre_lavages" in a.demangeaisons_details):
        steps.append(Step(
            "hebdomadaire", "Shampoing clarifiant",
            "1 fois par mois, pour enlever les résidus de produits qui alourdissent les cheveux.",
            "shampoing_clarifiant",
        ))
    if besoins["reparation"] >= 50 or "pointes" in a.preoccupations:
        steps.append(Step(
            "hebdomadaire", "Coupe des pointes",
            "Faites couper les pointes abîmées tous les 3 mois environ.",
        ))

    # La nuit
    if texture_bouclee or "casse" in a.preoccupations or "frisottis" in a.preoccupations:
        conseil = "Dormez sur une taie en satin ou en soie, ou protégez vos cheveux avec un bonnet en satin."
        if boucles:
            conseil += " Rassemblez vos cheveux en ananas (queue haute et lâche) pour préserver les boucles."
        steps.append(Step("nuit", "Protéger les cheveux", conseil, "accessoire",
                          produit_id="bonnet-satin"))

    return steps


def _conseils(a: Answers, besoins: dict[str, int], poids: str) -> list[str]:
    conseils = []
    poids_txt = {
        "leger": "Privilégiez des soins légers (sprays, lotions, gels fluides) pour ne pas alourdir vos cheveux.",
        "moyen": "Des soins de texture moyenne (crèmes légères, laits) conviennent bien à vos cheveux.",
        "riche": "Vos cheveux aiment les soins riches (beurres, crèmes épaisses, huiles) qui nourrissent en profondeur.",
    }
    conseils.append(poids_txt[poids])

    if a.porosite == "inconnue":
        conseils.append(
            "Pour connaître votre porosité : déposez un cheveu propre dans un verre d'eau. "
            "S'il flotte longtemps, la porosité est faible ; s'il coule vite, elle est forte."
        )
    if a.porosite == "forte":
        conseils.append(
            "Avec une porosité forte, superposez les soins : d'abord l'eau ou le soin sans rinçage, "
            "puis une crème, puis une huile pour sceller."
        )
    if a.elasticite == "manque_proteines":
        conseils.append(
            "Votre test d'élasticité montre un cheveu trop souple, qui ne revient pas : il "
            "manque de protéines. Intégrez un soin protéiné (kératine, protéines de riz ou de "
            "soie) une semaine sur deux, puis refaites le test dans un mois."
        )
    elif a.elasticite == "manque_hydratation":
        conseils.append(
            "Votre test d'élasticité montre un cheveu qui casse sans s'étirer : il manque "
            "d'hydratation. Mettez de côté les soins protéinés quelques semaines et misez sur "
            "les masques hydratants, puis refaites le test dans un mois."
        )
    if besoins["proteines"] >= 50 and besoins["hydratation"] >= 50:
        conseils.append(
            "Alternez soins hydratants et soins protéinés : trop de protéines rend le cheveu rigide "
            "et cassant, pas assez le rend mou et élastique."
        )
    if a.chaleur == "souvent":
        conseils.append(
            "Réduire l'usage des outils chauffants est le geste le plus efficace pour limiter la casse."
        )
    if "lissage" in a.traitements or "decoloration" in a.traitements:
        conseils.append(
            "Vos cheveux traités sont plus fragiles : espacez les traitements chimiques "
            "et faites-les réaliser par un professionnel."
        )
    if "pousse" in a.preoccupations or a.objectif == "longueur":
        conseils.append(
            "Les cheveux poussent d'environ 1 cm par mois. Pour gagner en longueur, l'essentiel "
            "est de limiter la casse des pointes."
        )
    if a.type_secondaire:
        conseils.append(
            f"Vos cheveux mélangent les types {a.type_cheveux} et {a.type_secondaire}. Coiffez "
            "zone par zone : un peu plus de crème sur les zones les plus serrées (souvent la "
            "nuque), des textures plus légères sur les zones plus souples. Vos soins ont été "
            "choisis pour convenir aux deux."
        )
    conseils += _conseils_jeunes(a)
    if a.texture in {"frise", "crepu"} and a.pour != "enfant":
        conseils.append(
            "Les coiffures protectrices (tresses, vanilles, chignons) limitent les manipulations ; "
            "évitez qu'elles tirent sur les tempes."
        )
    return conseils


def _conseils_jeunes(a: Answers) -> list[str]:
    """Conseils propres aux parcours enfant et ado."""
    c: list[str] = []
    if a.pour == "enfant":
        c.append("Pour un démêlage sans larmes : toujours sur cheveux mouillés et couverts de "
                 "démêlant, en commençant par les pointes, et en laissant votre enfant tenir une "
                 "mèche ou le peigne : il se sent acteur.")
        c.append("Pas de lissage, de défrisage, de coloration ni d'outil chauffant chez l'enfant : "
                 "sa fibre et son cuir chevelu sont encore fragiles.")
        c.append("Gardez des soins simples et doux, pensés pour les enfants : les produits pour "
                 "adultes sont souvent trop parfumés ou trop actifs.")
        if a.age_jeune != "bebe":
            c.append("Les poux reviennent souvent avec l'école : un coup de peigne anti-poux une "
                     "fois par semaine permet de les repérer tôt.")
    if a.pour == "ado":
        c.append("À la puberté, le cuir chevelu regraisse plus vite : un shampoing doux plus "
                 "fréquent ne l'abîme pas. Évitez de frotter fort, ce qui relance le sébum.")
        if a.chaleur != "jamais":
            c.append("Lisseur ou fer à boucler : toujours un protecteur thermique, et pas plus de "
                     "180 °C. Gardez-les pour les grandes occasions.")
        c.append("Coloration, décoloration, défrisage : mieux vaut attendre au moins 16 ans, et "
                 "toujours faire un test d'allergie 48 heures avant.")
        c.append("Examens, manque de sommeil, régime : ce que vit le corps se voit sur les "
                 "cheveux 2 à 3 mois plus tard.")
        if a.objectif == "autonomie":
            c.append("Pour vous lancer : un shampoing doux, un après-shampoing sur les longueurs, "
                     "un soin sans rinçage si vos cheveux sont bouclés. Ajoutez le reste peu à peu.")
    if {"serrees", "rajouts"} & set(a.coiffures):
        c.append("Les coiffures serrées et les rajouts tirent sur les tempes : desserrez dès que "
                 "ça fait mal, gardez une coiffure 6 semaines au plus et faites des pauses.")
    if "piscine" in a.coiffures:
        c.append("Piscine : mouillez les cheveux à l'eau claire et mettez un peu de soin sans "
                 "rinçage avant, un bonnet si possible, et rincez bien après.")
    return c


def _alertes(a: Answers) -> list[str]:
    alertes = [DETAILS_DEMANGEAISONS[d].alerte for d in a.demangeaisons_details
               if DETAILS_DEMANGEAISONS[d].alerte]
    if a.pour == "enfant" and ("chute" in a.preoccupations
                               or {"chute_plaques", "chute_brutale"} & set(a.sante)):
        alertes.append(
            "Une chute de cheveux chez l'enfant n'est jamais banale : consultez le pédiatre ou un "
            "dermatologue. Elle peut venir d'une teigne (contagieuse), d'une pelade, ou de cheveux "
            "arrachés par habitude.")
    elif "chute" in a.preoccupations:
        alertes.append(
            "Une chute importante, soudaine ou qui dure plus de 3 mois mérite l'avis d'un médecin "
            "ou d'un dermatologue : elle peut avoir des causes hormonales, nutritionnelles ou médicales."
        )
    if "plaques" in a.demangeaisons_details:
        pass  # l'alerte « plaques » est déjà plus précise
    elif (a.cuir_chevelu in {"sensible", "pellicules"}
          or {"demangeaisons", "pellicules"} & set(a.preoccupations)):
        alertes.append(
            "Si les démangeaisons, rougeurs ou pellicules persistent malgré des soins doux, "
            "consultez un dermatologue."
        )
    return alertes


# --- Produits ----------------------------------------------------------------


def score_product(p: Product, a: Answers, besoins: dict[str, int], poids: str,
                  saison: str | None = None) -> float | None:
    """Score d'adéquation d'un produit au profil, ou None s'il ne convient pas."""
    if p.types and a.type_cheveux not in p.types:
        return None
    # Produits adaptés à l'âge : seulement des soins pour enfants ou de tout âge pour un enfant.
    if a.pour == "enfant" and p.public not in {"enfant", "tous"}:
        return None
    if a.pour != "enfant" and p.public == "enfant":
        return None
    cuir = cuir_effectif(a)
    if p.cuir_chevelu and cuir not in p.cuir_chevelu:
        return None
    # Cuir chevelu sensible : seulement des produits prévus pour lui.
    if (cuir == "sensible" and p.categorie in {"shampoing", "soin_cuir"}
            and "sensible" not in p.cuir_chevelu):
        return None

    vrais_besoins = [b for b in p.besoins if b in NEEDS]
    score = sum(besoins.get(b, 0) for b in vrais_besoins) / max(1, len(vrais_besoins))
    if "anti_chute" in p.besoins:
        if "chute" not in a.preoccupations or "grossesse" in a.periodes:
            return None  # pas de soin anti-chute sans chute
        score += 25
    if p.poids == poids:
        score += 20
    elif {p.poids, poids} == {"leger", "riche"}:
        score -= 30
    if saison and saison in p.saisons:
        score += 8
    if p.types and len(p.types) <= 6:
        score += 4  # produit pensé pour peu de types : plus ciblé
    if "pellicules" in a.preoccupations and "pellicules" in p.cuir_chevelu:
        score += 10  # soin antipelliculaire, y compris pour un cuir chevelu sensible
    if cuir != a.cuir_chevelu and a.cuir_chevelu in p.cuir_chevelu:
        score += 5  # convient aussi à la nature habituelle du cuir chevelu
    if a.type_secondaire and p.types:
        score += 3 if a.type_secondaire in p.types else -3
    if a.pour == "enfant" and p.sans_parfum is True:
        score += 5
    if ("demangeaisons" in a.preoccupations and p.sans_parfum is True
            and p.categorie in {"shampoing", "soin_cuir", "leave_in"}):
        score += 6
    return score


PREFERENCES = {
    "vegan": "vegan",
    "sans_parfum": "sans parfum",
    "sans_sulfates": "sans sulfates",
    "sans_silicones": "sans silicones",
}
BUDGET_MAX = {"petit": 12.0, "moyen": 25.0}


def preferences_non_respectees(p: Product, a: Answers) -> list[str]:
    """Préférences que le produit ne respecte pas (ou dont on n'est pas sûr)."""
    manque = [PREFERENCES[pref] for pref in a.preferences if getattr(p, pref) is not True]
    limite = BUDGET_MAX.get(a.budget)
    if limite and p.prix is not None and p.prix > limite:
        manque.append("budget")
    return manque


def recommend(category: str, a: Answers, besoins: dict[str, int], poids: str,
              catalog: list[Product], saison: str | None = None
              ) -> tuple[Product | None, list[str]]:
    """Meilleur produit de la catégorie.

    On choisit d'abord parmi les produits qui respectent le plus de préférences,
    puis selon l'adéquation au profil. Renvoie aussi les préférences non respectées.
    """
    best: tuple[tuple[int, float], Product, list[str]] | None = None
    for p in catalog:
        if p.categorie != category:
            continue
        s = score_product(p, a, besoins, poids, saison)
        if s is None:
            continue
        manque = preferences_non_respectees(p, a)
        key = (-len(manque), s)
        if best is None or key > best[0]:
            best = (key, p, manque)
    return (best[1], best[2]) if best else (None, [])


def cout_routine(routine: list[Step]) -> float:
    """Prix indicatif total des produits de la routine (chaque produit compté une fois)."""
    produits = {s.produit.id: s.produit for s in routine if s.produit}
    return round(sum(p.prix or 0 for p in produits.values()), 2)


# --- Point d'entrée ----------------------------------------------------------


INTENSITE_PHOTO = {"leger": "léger", "modere": "modéré", "marque": "marqué"}


def _apply_photo(a: Answers, photo: AnalysePhoto, douleurs: list[PainReport],
                 alertes: list[str]) -> tuple[list[str], list[dict]]:
    """Croise l'analyse photo avec les réponses. Les réponses restent la référence."""
    notes: list[str] = []
    if not photo.exploitable:
        if photo.conseil_photo:
            notes.append(f"La photo n'a pas pu être exploitée : {photo.conseil_photo}")
        return notes, []

    vu = HAIR_TYPES.get(photo.type_cheveux or "")
    if vu and vu.code != a.type_cheveux and photo.confiance_type != "faible":
        if vu.famille != a.famille:
            notes.append(
                f"Sur la photo, vos cheveux ressemblent plutôt au type {vu.code} "
                f"({FAMILLES[vu.famille].label.lower()}), alors que vous avez choisi le type "
                f"{a.type_cheveux}. Les cheveux coiffés ou mouillés trompent souvent : observez-les "
                "après un lavage, sans produit. Si vous hésitez, refaites le diagnostic avec "
                "l'autre type pour comparer."
            )
        else:
            notes.append(
                f"Sur la photo, vos cheveux ressemblent plutôt au type {vu.code} "
                f"({vu.nom.lower()}) qu'au type {a.type_cheveux}. Les deux sont proches : "
                "vos soins restent adaptés."
            )

    seen = {s.signe: s for s in photo.signes}
    for d in douleurs:
        if d.id in seen:
            d.vu_sur_photo = True
            d.note_photo = seen[d.id].explication

    chosen = {d.id for d in douleurs}
    en_plus = [
        {"id": s.signe, "label": PAIN_POINTS[s.signe].label,
         "intensite": INTENSITE_PHOTO[s.intensite], "explication": s.explication}
        for s in photo.signes
        if s.signe not in chosen and s.intensite != "leger"
    ]
    if photo.alerte_medicale:
        alertes.append(photo.alerte_medicale)
    return notes, en_plus


# --- Fiabilité du diagnostic ------------------------------------------------------

NIVEAUX_FIABILITE = (
    (85, "elevee", "Élevée"),
    (65, "bonne", "Bonne"),
    (0, "a_preciser", "À préciser"),
)


def fiabilite(a: Answers, photo: AnalysePhoto | None = None,
              photo_dispo: bool | None = None) -> dict:
    """Indice de fiabilité : il baisse quand une réponse manque ou semble contradictoire."""
    photo_dispo = photo_disponible() if photo_dispo is None else photo_dispo
    score = 100
    a_ameliorer: list[str] = []
    a_verifier: list[str] = []

    if a.porosite == "inconnue":
        score -= 15
        a_ameliorer.append("Faites le test du verre d'eau pour connaître votre porosité "
                           "(5 minutes) : elle change le choix des soins.")
    if a.elasticite == "non_teste" and a.pour != "enfant":
        score -= 10
        a_ameliorer.append("Faites le test d'élasticité (1 minute) : il dit si vos cheveux "
                           "manquent plutôt d'hydratation ou de protéines.")
    photo_ok = bool(photo and photo.exploitable)
    if photo_dispo and not photo_ok and a.pour == "adulte":
        score -= 5
        a_ameliorer.append("Ajoutez une photo de vos cheveux : l'IA vérifie votre type et les "
                           "signes visibles.")

    if a.famille == "1" and ("definition" in a.preoccupations or a.objectif == "definition"):
        score -= 10
        a_verifier.append("Vous avez choisi des cheveux raides mais parlez de boucles : vos "
                          "cheveux sont peut-être ondulés (type 2). L'aide « Je ne suis pas sûre "
                          "de mon type » peut vous aider.")
    if (a.porosite == "forte" and a.famille == "1" and not a.traitements
            and a.chaleur == "jamais"):
        score -= 10
        a_verifier.append("Une porosité forte est rare sur des cheveux raides jamais colorés ni "
                          "chauffés : vérifiez-la avec le test du verre d'eau.")
    if a.porosite == "faible" and a.elasticite == "manque_proteines" and not a.traitements:
        score -= 5
        a_verifier.append("Un cheveu de porosité faible manque rarement de protéines sans "
                          "traitement chimique : refaites le test d'élasticité sur un cheveu "
                          "bien mouillé.")
    if photo_ok and photo.type_cheveux and photo.confiance_type != "faible":
        vu = HAIR_TYPES.get(photo.type_cheveux)
        if vu and vu.famille != a.famille and vu.famille != HAIR_TYPES.get(
                a.type_secondaire, typ_vide).famille:
            score -= 15
            a_verifier.append(f"Votre photo ressemble plutôt au type {vu.code} : vérifiez votre "
                              "type sur des cheveux lavés, séchés sans produit.")

    score = max(30, min(100, score))
    niveau, label = next((n, l) for seuil, n, l in NIVEAUX_FIABILITE if score >= seuil)
    return {"score": score, "niveau": niveau, "label": label,
            "a_ameliorer": a_ameliorer, "a_verifier": a_verifier}


class _TypeVide:
    famille = ""


typ_vide = _TypeVide()


PHASES = {
    "intensive": "Phase intensive",
    "entretien": "Phase d'entretien",
    "ajustement": "Phase d'ajustement",
}


def _programme(phase: str, a: Answers, besoins: dict[str, int], priorites: list[str],
               today: dt.date) -> tuple[list[dict], dt.date]:
    """Programme en étapes : ce qui change d'une période à l'autre."""
    prio = [NEEDS[p].lower() for p in priorites[:2]]
    focus = " et ".join(prio) if prio else "l'équilibre de vos cheveux"
    point = today + dt.timedelta(weeks=4)
    entretien = {
        "titre": "Entretien",
        "periode": "Ensuite",
        "actions": [
            "Masque 1 lavage sur 2, après-shampoing les autres fois.",
            "Gardez les gestes protecteurs : nuit en satin, démêlage doux, séchage sans frotter.",
            "Refaites votre diagnostic tous les 2 à 3 mois, ou à chaque changement de saison.",
        ],
    }
    if a.pour == "enfant":
        entretien["actions"] = [
            "Gardez la même routine douce : elle suffit dans la durée.",
            "Démêlage sous démêlant, coiffures souples, satin la nuit.",
            "Refaites le diagnostic tous les 3 mois ou à chaque changement de saison : ses "
            "cheveux changent en grandissant.",
        ]
    if phase == "entretien":
        return [entretien], today + dt.timedelta(weeks=8)
    intensif = {
        "titre": "Phase intensive" if phase == "intensive" else "Ajustement",
        "periode": "Semaines 1 à 4",
        "actions": [
            f"Priorité : {focus}.",
            "Suivez la routine ci-dessous à chaque lavage." if a.pour == "enfant"
            else "Masque à chaque lavage, en suivant la routine ci-dessous.",
            "Notez ce que vous observez après chaque lavage (souplesse, frisottis, casse).",
        ],
    }
    if besoins.get("reparation", 0) >= 50 or "pointes" in a.preoccupations:
        intensif["actions"].append("Faites couper les pointes abîmées au début du programme.")
    if phase == "ajustement":
        intensif["actions"].insert(1, "Appliquez les ajustements indiqués dans « Votre évolution ».")
    return [intensif, {**entretien, "periode": "À partir de la semaine 5"}], point


def resume_suivi(d: Diagnostic, a: Answers, today: dt.date) -> dict:
    return ResumeSuivi(
        id=uuid.uuid4().hex, date=today, type_cheveux=a.type_cheveux,
        intensites=dict(a.intensites), besoins=d.besoins, phase=d.phase,
        prochain_point=d.prochain_point, preferences=list(a.preferences), budget=a.budget,
        age=a.age, saisons_sensibles=list(a.saisons_sensibles), prenom=a.prenom,
        type_secondaire=a.type_secondaire, pour=a.pour,
    ).model_dump(mode="json")


def run_diagnostic(a: Answers, catalog: list[Product] | None = None,
                   photo: AnalysePhoto | None = None, today: dt.date | None = None,
                   precedent: ResumeSuivi | None = None) -> Diagnostic:
    catalog = catalog if catalog is not None else load_catalog()
    today = today or dt.date.today()
    saison = seasons.saison_du(today)
    besoins = compute_needs(a, photo, saison)
    poids = _poids_produits(a, saison)
    # On ne compare qu'avec un diagnostic du même parcours (pas un parent et son enfant).
    if precedent and precedent.pour != a.pour:
        precedent = None
    evolution = compare(precedent, a, besoins, today) if precedent else None
    phase = evolution.phase if evolution else "intensive"
    routine = _build_routine(a, besoins, poids)
    par_id_cat = {p.id: p for p in catalog}
    for step in routine:
        prefere = par_id_cat.get(step.produit_id or "")
        if prefere and score_product(prefere, a, besoins, poids, saison.id) is not None:
            step.produit, step.hors_preferences = prefere, preferences_non_respectees(prefere, a)
        elif step.categorie:
            step.produit, step.hors_preferences = recommend(
                step.categorie, a, besoins, poids, catalog, saison.id)
        if step.categorie == "masque" and phase == "entretien":
            step.conseil = "Un lavage sur deux, en alternance avec un après-shampoing. " + step.conseil

    priorites = [n for n, s in sorted(besoins.items(), key=lambda kv: -kv[1]) if s > 0][:3]
    programme, prochain_point = _programme(phase, a, besoins, priorites, today)
    douleurs = explain(a)
    typ = HAIR_TYPES[a.type_cheveux]
    vus = {s.signe for s in photo.signes} if photo and photo.exploitable else set()
    problemes_type = [
        {"id": pid, "label": PAIN_POINTS[pid].label, "pourquoi": why,
         "signale": pid in a.preoccupations, "vu_photo": pid in vus, "type": typ.code}
        for pid, why in typ.problemes
    ]
    sec = HAIR_TYPES.get(a.type_secondaire)
    if sec:
        deja = {p["id"] for p in problemes_type}
        problemes_type += [
            {"id": pid, "label": PAIN_POINTS[pid].label, "pourquoi": why,
             "signale": pid in a.preoccupations, "vu_photo": pid in vus, "type": sec.code}
            for pid, why in sec.problemes if pid not in deja
        ]
    par_id = {p.id: p for p in catalog}
    recettes = naturel.recettes_pour(a, besoins, {s.categorie for s in routine if s.categorie})
    for r in recettes:
        step = next((s for s in routine if s.categorie == r.categorie and not s.alternative), None)
        if step:
            step.alternative = r
    cures, cures_message = naturel.cures_pour(a, saison.id)
    specifiques = [{"id": sid, "label": SPECIFICITES[sid].label,
                    "conseil": SPECIFICITES[sid].conseil} for sid in a.specifiques]
    alertes = _alertes(a)
    notes_photo, en_plus = _apply_photo(a, photo, douleurs, alertes) if photo else ([], [])

    d = Diagnostic(
        resume=_resume(a),
        texture=a.texture,
        type_cheveux=typ,
        problemes_type=problemes_type,
        besoins=besoins,
        priorites=priorites,
        frequence_lavage=_frequence_lavage(a),
        poids_produits=poids,
        routine=routine,
        douleurs=douleurs,
        conseils=_conseils(a, besoins, poids),
        alertes=alertes,
        photo=photo,
        notes_photo=notes_photo,
        signes_photo_en_plus=en_plus,
        saison=saison,
        conseils_saison=profil.conseils_saison_perso(a, saison)
        + ([] if a.pour == "enfant" else seasons.conseils(saison, a)),
        conseils_vie=profil.conseils_vie(a),
        prochaine_saison=seasons.prochaine(saison),
        # Ce qui changera à la saison suivante : la réaction propre à la personne si elle
        # l'a indiquée, sinon le principal conseil de la saison.
        anticipation=(profil.anticipation(a, seasons.prochaine(saison))
                      or ([] if a.pour == "enfant"
                          else seasons.conseils(seasons.prochaine(saison), a)[:1])),
        phase=phase,
        programme=programme,
        prochain_point=prochain_point,
        evolution=evolution,
        cout_total=cout_routine(routine),
        jours_lavage=jours_suggeres(lavages_par_semaine(a)),
        prenom=a.prenom,
        liens_affilies=any(o.affilie for s in routine if s.produit for o in s.produit.offres),
        liens_amazon=any(o.amazon for s in routine if s.produit for o in s.produit.offres),
        preferences=[PREFERENCES[p] for p in a.preferences],
        budget=a.budget,
        type_secondaire=sec,
        specifiques=specifiques,
        recettes=[{"recette": r, "ingredients": naturel.produits_recette(r, catalog)}
                  for r in recettes],
        cures=[{"cure": c, "produits": [par_id[i] for i in c.produits if i in par_id]}
               for c in cures],
        cures_message=cures_message,
        conseils_naturels=naturel.conseils_naturels(a),
        fiabilite=fiabilite(a, photo),
        orientation=sante.orientation(a),
        pour=a.pour,
        coffret=recommend("coffret", a, besoins, poids, catalog, saison.id)[0],
    )
    d.suivi = resume_suivi(d, a, today)
    return d
