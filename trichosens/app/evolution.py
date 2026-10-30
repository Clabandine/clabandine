"""Évolution des cheveux : comparaison avec le diagnostic précédent.

L'historique est gardé dans le navigateur de la personne. À chaque nouveau
diagnostic, le navigateur renvoie le résumé du précédent ; on compare, puis on
adapte le programme de soins (intensif, entretien ou ajustement).
"""

from dataclasses import dataclass, field
import datetime as dt
from typing import TYPE_CHECKING

from pydantic import BaseModel, Field

from .hair_types import HAIR_TYPES
from .pain_points import INTENSITES, PAIN_POINTS

if TYPE_CHECKING:
    from .questionnaire import Answers

# Délai avant de juger l'effet d'une routine.
JOURS_MINIMUM = 14
JOURS_CYCLE = 28

NIVEAU = {"absent": 0, "un_peu": 1, "beaucoup": 2, "enormement": 3}


class ResumeSuivi(BaseModel):
    """Résumé d'un diagnostic, gardé dans l'historique du navigateur."""

    version: int = 1
    id: str = Field(max_length=64)
    date: dt.date
    type_cheveux: str
    intensites: dict[str, str] = {}
    besoins: dict[str, int] = {}
    phase: str = "intensive"
    prochain_point: dt.date | None = None


@dataclass
class Changement:
    id: str
    label: str
    avant: str
    apres: str
    tendance: str  # mieux, moins_bien, stable, nouveau, resolu


@dataclass
class Evolution:
    depuis: dt.date
    jours: int
    changements: list[Changement]
    besoins_deltas: dict[str, int]
    messages: list[str] = field(default_factory=list)
    phase: str = "intensive"


TENDANCE_LABEL = {
    "mieux": "En amélioration",
    "moins_bien": "En hausse",
    "stable": "Stable",
    "nouveau": "Nouveau",
    "resolu": "Réglé",
}

CONSEIL_SI_PIRE = {
    "secheresse": "La sécheresse augmente : passez à un masque plus riche, hydratez entre deux "
                  "lavages et scellez avec une huile ou un beurre.",
    "casse": "La casse augmente : regardez vos cheveux mouillés. S'ils sont rigides et cassants, "
             "réduisez les soins protéinés ; s'ils sont mous et trop élastiques, ajoutez-en.",
    "frisottis": "Les frisottis augmentent : appliquez vos soins sur cheveux trempés et passez à "
                 "un coiffant à tenue plus forte.",
    "chute": "La chute augmente : si elle dure depuis plus de 3 mois, consultez un médecin ou un "
             "dermatologue.",
    "pointes": "Les pointes s'abîment : une coupe s'impose, puis nourrissez-les chaque jour.",
    "volume": "Le volume diminue : allégez vos soins et faites un shampoing clarifiant.",
    "definition": "Les boucles se définissent moins : vérifiez que vos soins ne s'accumulent pas "
                  "(shampoing clarifiant) et figez-les avec un gel.",
    "pousse": "La longueur stagne toujours : concentrez-vous sur la protection des pointes et les "
              "coiffures protectrices.",
    "terne": "Vos cheveux ternissent : clarifiez, puis finissez par un rinçage à l'eau fraîche.",
    "demelage": "Le démêlage devient plus difficile : démêlez toujours sous un soin glissant et "
                "protégez vos cheveux la nuit.",
    "alourdis": "Vos cheveux s'alourdissent davantage : réduisez les quantités et passez à des "
                "textures plus légères.",
}


def _fmt_jours(jours: int) -> str:
    if jours < 14:
        return f"{jours} jour{'s' if jours > 1 else ''}"
    semaines = round(jours / 7)
    if semaines < 9:
        return f"{semaines} semaines"
    return f"{round(jours / 30)} mois"


def compare(prec: ResumeSuivi, a: "Answers", besoins: dict[str, int], today: dt.date) -> Evolution:
    jours = max(0, (today - prec.date).days)
    avant = {k: v for k, v in prec.intensites.items() if k in PAIN_POINTS and v in INTENSITES}
    apres = dict(a.intensites)

    changements: list[Changement] = []
    for pid in list(dict.fromkeys([*apres, *avant])):
        n_avant = NIVEAU[avant.get(pid, "absent")]
        n_apres = NIVEAU[apres.get(pid, "absent")]
        if n_avant == 0:
            tendance = "nouveau"
        elif n_apres == 0:
            tendance = "resolu"
        elif n_apres < n_avant:
            tendance = "mieux"
        elif n_apres > n_avant:
            tendance = "moins_bien"
        else:
            tendance = "stable"
        changements.append(Changement(
            id=pid, label=PAIN_POINTS[pid].label,
            avant=INTENSITES.get(avant.get(pid, ""), "Absent"),
            apres=INTENSITES.get(apres.get(pid, ""), "Absent"),
            tendance=tendance,
        ))

    deltas = {k: besoins[k] - prec.besoins[k] for k in besoins if k in prec.besoins
              and besoins[k] != prec.besoins[k]}

    evo = Evolution(depuis=prec.date, jours=jours, changements=changements, besoins_deltas=deltas)
    tendances = {c.tendance for c in changements}
    progres = tendances & {"mieux", "resolu"}
    recul = tendances & {"moins_bien", "nouveau"}
    duree = _fmt_jours(jours)

    if prec.type_cheveux != a.type_cheveux and prec.type_cheveux in HAIR_TYPES:
        evo.messages.append(
            f"Vous avez choisi le type {a.type_cheveux}, contre {prec.type_cheveux} la dernière fois. "
            "C'est fréquent quand les cheveux retrouvent leur forme naturelle (après un lissage ou "
            "pendant une transition) ou grâce à des soins mieux adaptés."
        )

    if jours < JOURS_MINIMUM:
        evo.phase = prec.phase
        evo.messages.append(
            f"Votre dernier diagnostic date de {duree} : c'est encore tôt pour juger. Les soins "
            "mettent environ 4 semaines à montrer leurs effets, gardez la même routine."
        )
        return evo

    if progres and not recul:
        evo.phase = "entretien"
        evo.messages.append(
            f"Bravo : en {duree}, vos cheveux ont progressé. Votre routine passe en phase "
            "d'entretien : moins de soins intensifs, les mêmes bons gestes."
        )
    elif recul:
        evo.phase = "ajustement"
        if progres:
            evo.messages.append(f"En {duree}, certains points s'améliorent, d'autres non. "
                                "Nous ajustons votre routine sur ce qui résiste.")
        else:
            evo.messages.append(f"En {duree}, vos cheveux n'ont pas progressé comme prévu. "
                                "Nous ajustons votre routine.")
        for c in changements:
            if c.tendance in {"moins_bien", "nouveau"} and c.id in CONSEIL_SI_PIRE:
                evo.messages.append(CONSEIL_SI_PIRE[c.id])
    else:
        evo.phase = "ajustement" if jours >= JOURS_CYCLE else prec.phase
        evo.messages.append(
            f"Pas de changement notable en {duree}. "
            + ("Essayons d'ajuster votre routine : suivez les conseils ci-dessous et refaites le "
               "point dans 4 semaines." if jours >= JOURS_CYCLE else
               "Continuez encore quelques semaines avant de juger.")
        )
    return evo
