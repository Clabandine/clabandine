"""Adaptation de la routine à la saison (hémisphère nord)."""

from dataclasses import dataclass
from datetime import date
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .questionnaire import Answers


@dataclass(frozen=True)
class Saison:
    id: str
    nom: str
    article: str  # « cet hiver », « ce printemps »…
    points: dict[str, int]


SAISONS = {
    "hiver": Saison("hiver", "Hiver", "cet hiver", {"hydratation": 1, "nutrition": 2}),
    "printemps": Saison("printemps", "Printemps", "ce printemps", {}),
    "ete": Saison("ete", "Été", "cet été", {"protection": 3, "hydratation": 1}),
    "automne": Saison("automne", "Automne", "cet automne", {"cuir_chevelu": 1, "reparation": 1}),
}


def saison_du(jour: date) -> Saison:
    m = jour.month
    if m in (12, 1, 2):
        return SAISONS["hiver"]
    if m in (3, 4, 5):
        return SAISONS["printemps"]
    if m in (6, 7, 8):
        return SAISONS["ete"]
    return SAISONS["automne"]


def conseils(s: Saison, a: "Answers") -> list[str]:
    boucles = a.famille in {"3", "4"}
    ondule_ou_plus = a.famille in {"2", "3", "4"}
    out: list[str] = []
    if s.id == "hiver":
        out.append("Le froid et le chauffage dessèchent les cheveux : choisissez un masque plus "
                   "nourrissant et scellez l'hydratation avec une huile ou un beurre.")
        out.append("Sous un bonnet en laine, glissez un bonnet ou un foulard en satin pour éviter "
                   "les frottements et la casse.")
        out.append("Ne sortez pas les cheveux mouillés : le froid les fragilise.")
        if boucles:
            out.append("Un humidificateur d'air la nuit aide les boucles à garder leur hydratation.")
    elif s.id == "printemps":
        out.append("C'est le bon moment pour couper les pointes abîmées par l'hiver.")
        out.append("Allégez peu à peu les soins très riches de l'hiver.")
        if ondule_ou_plus:
            out.append("L'humidité revient : un gel ou une crème coiffante limitera les frisottis.")
    elif s.id == "ete":
        out.append("Le soleil abîme la fibre : portez un chapeau ou un foulard, ou utilisez un "
                   "spray protecteur UV pour cheveux.")
        out.append("Avant la baignade, mouillez vos cheveux à l'eau douce et appliquez un soin sans "
                   "rinçage : ils absorberont moins de sel ou de chlore.")
        out.append("Après la mer ou la piscine, rincez toujours vos cheveux à l'eau douce.")
        out.append("Avec la chaleur, préférez des textures plus légères.")
    elif s.id == "automne":
        out.append("Une chute plus importante est normale en automne : c'est la chute saisonnière, "
                   "elle dure en général 4 à 8 semaines.")
        out.append("Réparez les dégâts de l'été : un masque réparateur une fois par semaine pendant "
                   "un mois.")
        out.append("Massez votre cuir chevelu quelques minutes à chaque lavage pour l'entretenir.")
    return out
