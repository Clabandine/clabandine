"""Santé et cheveux : problèmes de santé, carences et signes qui touchent les cheveux.

Ces réponses sont facultatives et restent sur l'appareil de la personne. Elles servent
à expliquer ce qui peut jouer sur ses cheveux, à l'orienter vers le bon professionnel
de santé et à adapter (ou éviter) les compléments alimentaires. TrichoSens ne pose
aucun diagnostic médical.
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .questionnaire import Answers

GENERALISTE = "Médecin généraliste"
DERMATO = "Dermatologue"
GYNECO = "Gynécologue"
ENDOCRINO = "Endocrinologue"


@dataclass(frozen=True)
class Facteur:
    id: str
    label: str
    hint: str
    groupe: str  # "connu" (problème connu) ou "signe" (ce que l'on remarque)
    explication: str
    specialistes: tuple[tuple[str, str], ...] = ()  # (professionnel, pourquoi)
    bilan: tuple[str, ...] = ()  # examens à demander à son médecin
    points: dict[str, int] = field(default_factory=dict)
    # Pas de cure de compléments sans avis médical.
    sans_cure: bool = False
    note_cure: str = ""


FACTEURS: dict[str, Facteur] = {f.id: f for f in (
    # --- Problèmes connus --------------------------------------------------------
    Facteur(
        "carence_fer", "Manque de fer ou anémie", "Ferritine basse, anémie.", "connu",
        "Le fer est indispensable à la fabrication du cheveu : un manque, même sans anémie "
        "(ferritine basse), est l'une des premières causes de chute chez les femmes.",
        ((GENERALISTE, "contrôler la ferritine et adapter la supplémentation en fer"),),
        ("ferritine", "numération formule sanguine"),
        {"cuir_chevelu": 2},
        note_cure="Le fer se prend seulement si une prise de sang a confirmé le manque, à la "
                  "dose indiquée par votre médecin : trop de fer est toxique.",
    ),
    Facteur(
        "carence_vitd", "Manque de vitamine D", "Fréquent en hiver.", "connu",
        "Un manque de vitamine D est souvent associé à une chute plus importante.",
        ((GENERALISTE, "doser la vitamine D et choisir la bonne dose"),),
        ("vitamine D",),
        {"cuir_chevelu": 1},
        note_cure="La vitamine D se dose avant d'être complétée : votre médecin vous dira "
                  "quelle dose prendre et combien de temps.",
    ),
    Facteur(
        "carence_autre", "Autre carence (B12, zinc, protéines…)", "Souvent liée à "
        "l'alimentation (végétarienne, végane).", "connu",
        "Les cheveux ont besoin de protéines, de zinc et de vitamines B : une carence les "
        "rend plus fins, cassants et fait tomber.",
        ((GENERALISTE, "vérifier la vitamine B12, le zinc et l'équilibre alimentaire"),),
        ("vitamine B12", "zinc"),
        {"reparation": 1, "proteines": 1},
    ),
    Facteur(
        "thyroide", "Problème de thyroïde", "Hypothyroïdie, Hashimoto, hyperthyroïdie.",
        "connu",
        "La thyroïde règle le rythme de pousse : quand elle fonctionne trop ou pas assez, les "
        "cheveux deviennent plus fins, secs et tombent davantage.",
        ((ENDOCRINO, "suivre votre thyroïde : une chute peut signaler un traitement à ajuster"),),
        ("TSH",),
        {"hydratation": 1, "cuir_chevelu": 1},
        note_cure="Si vous prenez de la biotine (vitamine B8), arrêtez-la 2 à 3 jours avant "
                  "une prise de sang : elle fausse le dosage de la thyroïde.",
    ),
    Facteur(
        "sopk", "Syndrome des ovaires polykystiques (SOPK)", "", "connu",
        "Le SOPK augmente l'effet des hormones androgènes : les cheveux s'affinent sur le "
        "dessus de la tête, alors que des poils peuvent apparaître sur le visage.",
        ((GYNECO, "traiter le déséquilibre hormonal à l'origine de la chute"),
         (DERMATO, "proposer un traitement local de la chute si besoin")),
        ("bilan hormonal",),
        {"cuir_chevelu": 2},
        note_cure="Une cure de compléments peut accompagner, mais ne remplace pas le "
                  "traitement du SOPK.",
    ),
    Facteur(
        "pelade", "Pelade (chute par plaques)", "Maladie auto-immune du cheveu.", "connu",
        "La pelade est une maladie auto-immune : le corps attaque ses propres racines, "
        "ce qui crée des plaques sans cheveux. Elle se soigne chez le dermatologue.",
        ((DERMATO, "suivre la pelade et proposer un traitement"),),
        (),
        {"cuir_chevelu": 3},
        note_cure="Aucun complément ne soigne la pelade : suivez le traitement de votre "
                  "dermatologue.",
    ),
    Facteur(
        "auto_immune", "Autre maladie auto-immune", "Lupus, maladie cœliaque…", "connu",
        "Plusieurs maladies auto-immunes (lupus, maladie cœliaque) peuvent fragiliser les "
        "cheveux ou faire tomber, directement ou par leurs traitements.",
        ((GENERALISTE, "en parler à votre médecin qui suit la maladie"),),
        (),
        {"cuir_chevelu": 2},
        sans_cure=True,
    ),
    Facteur(
        "dermato", "Psoriasis, eczéma ou dermite du cuir chevelu", "", "connu",
        "Ces maladies de peau irritent le cuir chevelu, font des plaques et des squames, et "
        "peuvent entretenir une chute.",
        ((DERMATO, "traiter le cuir chevelu avec des soins médicaux adaptés"),),
        (),
        {"cuir_chevelu": 3},
    ),
    Facteur(
        "regime", "Régime strict, perte de poids rapide ou trouble alimentaire", "",
        "connu",
        "Une perte de poids rapide ou une alimentation trop restreinte prive les cheveux de "
        "protéines et de fer : ils tombent souvent 2 à 3 mois plus tard.",
        ((GENERALISTE, "vérifier les carences et vous accompagner"),),
        ("ferritine", "vitamine B12", "zinc"),
        {"reparation": 1, "proteines": 2},
    ),
    Facteur(
        "maladie_recente", "Forte fièvre, infection, COVID ou opération récente",
        "Ces 3 derniers mois.", "connu",
        "Une forte fièvre, une infection ou une opération peuvent déclencher une chute "
        "importante 2 à 3 mois plus tard (effluvium télogène). Elle s'arrête d'elle-même en "
        "quelques mois.",
        (),
        (),
        {"cuir_chevelu": 1},
    ),
    Facteur(
        "chimio", "Chimiothérapie ou radiothérapie", "", "connu",
        "Les traitements du cancer peuvent faire tomber les cheveux ; ils repoussent en "
        "général après la fin du traitement, parfois avec une texture différente.",
        ((GENERALISTE, "demander à votre équipe médicale les soins autorisés pendant le "
                       "traitement"),),
        (),
        {"cuir_chevelu": 2, "hydratation": 1},
        sans_cure=True,
        note_cure="Pendant un traitement du cancer, ne prenez aucun complément sans l'accord "
                  "de votre équipe médicale.",
    ),
    # --- Signes que l'on remarque ---------------------------------------------------
    Facteur(
        "fatigue", "Fatigue inhabituelle, essoufflement ou pâleur", "", "signe",
        "Une fatigue inhabituelle avec une chute de cheveux peut signaler un manque de fer "
        "ou un problème de thyroïde.",
        ((GENERALISTE, "faire un bilan sanguin"),),
        ("ferritine", "numération formule sanguine", "TSH", "vitamine D"),
    ),
    Facteur(
        "regles_abondantes", "Règles très abondantes", "", "signe",
        "Des règles abondantes font perdre beaucoup de fer chaque mois : c'est une cause "
        "fréquente de manque de fer et de chute.",
        ((GENERALISTE, "doser la ferritine"), (GYNECO, "chercher la cause des règles "
                                                        "abondantes")),
        ("ferritine",),
    ),
    Facteur(
        "chute_plaques", "Chute par plaques rondes", "", "signe",
        "Des plaques rondes sans cheveux évoquent une pelade ou un problème du cuir chevelu "
        "qui doit être examiné.",
        ((DERMATO, "examiner les plaques"),),
        (),
    ),
    Facteur(
        "chute_brutale", "Chute brutale, par poignées", "", "signe",
        "Une chute brutale et abondante a presque toujours une cause (fièvre, accouchement, "
        "choc émotionnel, carence, médicament) qu'il vaut mieux identifier.",
        ((GENERALISTE, "trouver la cause et faire un bilan sanguin"),),
        ("ferritine", "TSH", "vitamine D"),
    ),
    Facteur(
        "signes_hormonaux", "Acné, poils au visage ou règles irrégulières", "", "signe",
        "Ces signes associés à des cheveux qui s'affinent sur le dessus évoquent un excès "
        "d'hormones androgènes (comme dans le SOPK).",
        ((GYNECO, "faire un bilan hormonal"),),
        ("bilan hormonal",),
    ),
    Facteur(
        "signes_thyroide", "Frilosité, prise de poids, ongles cassants (ou palpitations)",
        "", "signe",
        "Ces signes avec une chute de cheveux peuvent venir de la thyroïde.",
        ((GENERALISTE, "doser la TSH"),),
        ("TSH",),
    ),
    Facteur("aucun", "Rien de tout cela", "", "connu", ""),
)}


def _ajouter(specialistes: dict[str, list[str]], nom: str, raison: str) -> None:
    raisons = specialistes.setdefault(nom, [])
    if raison not in raisons:
        raisons.append(raison)


def orientation(a: "Answers") -> dict:
    """Facteurs de santé, professionnels à consulter et examens à demander."""
    facteurs = [FACTEURS[f] for f in a.sante if f != "aucun"]
    specialistes: dict[str, list[str]] = {}
    bilan: list[str] = []
    for f in facteurs:
        for nom, raison in f.specialistes:
            _ajouter(specialistes, nom, raison)
        bilan += [b for b in f.bilan if b not in bilan]

    # Même sans problème de santé coché, certaines réponses méritent un avis médical.
    chute = a.intensites.get("chute")
    if chute == "enormement":
        _ajouter(specialistes, GENERALISTE, "chercher la cause d'une chute importante")
        bilan += [b for b in ("ferritine", "TSH", "vitamine D") if b not in bilan]
    if "chute" in a.preoccupations and {"post_partum", "menopause"} & set(a.periodes) \
            and chute in {"beaucoup", "enormement"}:
        _ajouter(specialistes, GENERALISTE, "vérifier qu'aucune carence n'entretient la chute")
        bilan += [b for b in ("ferritine", "TSH") if b not in bilan]
    if "tempes_clairsemees" in a.specifiques:
        _ajouter(specialistes, DERMATO, "examiner les tempes si elles ne repoussent pas")
    if "plaques" in a.demangeaisons_details:
        _ajouter(specialistes, DERMATO, "examiner les plaques du cuir chevelu")

    ordre = [GENERALISTE, DERMATO, GYNECO, ENDOCRINO]
    return {
        "facteurs": [{"id": f.id, "label": f.label, "explication": f.explication}
                     for f in facteurs],
        "specialistes": [{"nom": n, "raisons": specialistes[n]}
                         for n in ordre if n in specialistes],
        "bilan": bilan,
    }


def points(a: "Answers") -> list[dict[str, int]]:
    return [FACTEURS[f].points for f in a.sante if FACTEURS[f].points]
