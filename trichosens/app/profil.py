"""Profil de vie : âge, périodes particulières et réaction des cheveux aux saisons.

Ces informations ajustent les besoins, le poids des soins et les conseils. Ce ne
sont jamais des avis médicaux : pour toute inquiétude, on oriente vers un médecin.
"""

from dataclasses import dataclass
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from .questionnaire import Answers
    from .seasons import Saison

AGES = {
    "moins_18": "Moins de 18 ans",
    "18_29": "18 à 29 ans",
    "30_44": "30 à 44 ans",
    "45_59": "45 à 59 ans",
    "60_plus": "60 ans et plus",
    "nc": "Je préfère ne pas répondre",
}

AGE_POINTS = {
    "45_59": {"nutrition": 1, "cuir_chevelu": 1},
    "60_plus": {"nutrition": 2, "hydratation": 1, "protection": 1},
}

AGE_CONSEILS = {
    "moins_18": "À votre âge, le cuir chevelu peut regraisser plus vite à cause des changements "
                "hormonaux : préférez un shampoing doux, et évitez les traitements chimiques "
                "(décoloration, lissage), qui fragilisent durablement la fibre.",
    "45_59": "Avec les années, le cheveu devient souvent plus fin et plus sec : nourrissez les "
             "longueurs et massez régulièrement le cuir chevelu.",
    "60_plus": "Les cheveux blancs sont souvent plus rêches, plus secs, et jaunissent au soleil : "
               "nourrissez-les, protégez-les des UV, et un shampoing violet de temps en temps "
               "ravive leur éclat.",
}

PERIODES = {
    "cycle": ("Mes cheveux changent selon mon cycle menstruel",
              "Racines plus grasses ou cheveux plus ternes à certains moments du mois."),
    "grossesse": ("Je suis enceinte", ""),
    "post_partum": ("J'ai accouché il y a moins d'un an", ""),
    "menopause": ("Ménopause ou périménopause", ""),
    "stress": ("Période de stress ou de grande fatigue", ""),
    "traitement": ("Nouveau traitement médical ou changement de contraception",
                   "Depuis moins de 6 mois."),
    "aucune": ("Rien de particulier", ""),
}

PERIODE_POINTS = {
    "post_partum": {"cuir_chevelu": 2},
    "menopause": {"nutrition": 1, "cuir_chevelu": 1, "volume": 1},
    "stress": {"cuir_chevelu": 1},
    "traitement": {"cuir_chevelu": 1},
}

PERIODE_CONSEILS = {
    "cycle": "Juste avant les règles, le cuir chevelu peut regraisser plus vite : un lavage de plus "
             "cette semaine-là, avec un shampoing doux, ne pose aucun problème.",
    "grossesse": "Pendant la grossesse, les cheveux sont souvent plus denses et plus brillants. "
                 "Demandez conseil à votre médecin ou à votre pharmacien avant d'utiliser des huiles "
                 "essentielles, une coloration ou un soin anti-chute.",
    "post_partum": "Une chute importante 2 à 4 mois après l'accouchement est fréquente et temporaire : "
                   "les cheveux gardés pendant la grossesse tombent d'un coup. Elle se calme en général "
                   "en 6 à 12 mois. D'ici là, coiffures lâches et démêlage tout en douceur.",
    "menopause": "Pendant la ménopause, les cheveux peuvent devenir plus fins, plus secs et moins "
                 "denses : nourrissez les longueurs avec des soins qui n'alourdissent pas les racines, "
                 "et parlez à votre médecin d'une chute marquée.",
    "stress": "Un stress ou une grande fatigue peuvent provoquer une chute 2 à 3 mois plus tard. "
              "Elle est le plus souvent temporaire ; un sommeil régulier et une alimentation variée aident.",
    "traitement": "Certains traitements, ou un changement de contraception, peuvent modifier la chute "
                  "ou le sébum pendant quelques mois. Parlez-en à votre médecin si cela vous inquiète.",
}


@dataclass(frozen=True)
class Sensibilite:
    label: str
    saisons: frozenset[str]
    points: dict
    poids: int  # +1 = soins plus riches, -1 = plus légers
    conseil: str


SENSIBILITES: dict[str, Sensibilite] = {
    "sec_hiver": Sensibilite(
        "Plus secs en hiver", frozenset({"hiver"}),
        {"hydratation": 2, "nutrition": 2}, 1,
        "vos cheveux deviennent plus secs : passez à un masque plus nourrissant dès les premiers "
        "froids, et scellez l'hydratation avec une huile ou un beurre.",
    ),
    "frisottis_humidite": Sensibilite(
        "Plus de frisottis quand l'air est humide", frozenset({"printemps", "ete", "automne"}),
        {"definition": 2, "hydratation": 1}, 0,
        "l'humidité fait gonfler vos cheveux : appliquez vos soins sur cheveux trempés et finissez "
        "par un gel à bonne tenue.",
    ),
    "gras_ete": Sensibilite(
        "Plus gras quand il fait chaud", frozenset({"ete"}),
        {"cuir_chevelu": 2}, -1,
        "votre cuir chevelu regraisse plus vite : allégez les soins près des racines et ajoutez un "
        "lavage doux si besoin.",
    ),
    "chute_automne": Sensibilite(
        "Plus de chute en automne", frozenset({"automne"}),
        {"cuir_chevelu": 2}, 0,
        "la chute saisonnière revient : massez le cuir chevelu à chaque lavage ; elle dure en "
        "général 4 à 8 semaines.",
    ),
    "abimes_ete": Sensibilite(
        "Abîmés ou plus ternes après l'été", frozenset({"ete", "automne"}),
        {"reparation": 2, "protection": 1}, 0,
        "le soleil, le sel et le chlore abîment vos longueurs : protégez-les en été, puis faites un "
        "masque réparateur chaque semaine à la rentrée.",
    ),
    "aucune": Sensibilite("Pas de différence", frozenset(), {}, 0, ""),
}


def _actives(a: "Answers", saison: "Saison | None") -> list[Sensibilite]:
    if not saison:
        return []
    return [SENSIBILITES[s] for s in a.saisons_sensibles if saison.id in SENSIBILITES[s].saisons]


def points(a: "Answers", saison: "Saison | None") -> list[dict]:
    """Points de besoins à ajouter (âge, périodes, réaction à la saison en cours)."""
    out = [AGE_POINTS.get(a.age, {})]
    out += [PERIODE_POINTS.get(p, {}) for p in a.periodes]
    out += [s.points for s in _actives(a, saison)]
    return out


def ajustement_poids(a: "Answers", saison: "Saison | None") -> int:
    return sum(s.poids for s in _actives(a, saison))


def conseils_saison_perso(a: "Answers", saison: "Saison") -> list[str]:
    return [f"Vous nous avez dit qu'{saison.article.replace('cet ', 'en ').replace('ce ', 'au ')}, "
            f"{s.conseil}" for s in _actives(a, saison)]


def conseils_vie(a: "Answers") -> list[str]:
    out = []
    if a.age in AGE_CONSEILS:
        out.append(AGE_CONSEILS[a.age])
    out += [PERIODE_CONSEILS[p] for p in a.periodes if p in PERIODE_CONSEILS]
    return out


def anticipation(a: "Answers", prochaine: "Saison") -> list[str]:
    """Ce qui changera dans la routine à la saison suivante, selon la réaction des cheveux."""
    return [f"{s.conseil[0].upper()}{s.conseil[1:]}" for s in _actives(a, prochaine)]
