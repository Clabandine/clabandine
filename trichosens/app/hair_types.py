"""Les 12 types de cheveux (classification 1A à 4C) et leurs problèmes fréquents."""

from dataclasses import dataclass


@dataclass(frozen=True)
class Famille:
    id: str
    titre: str
    label: str
    visuel: str


FAMILLES: dict[str, Famille] = {
    "1": Famille("1", "Type 1", "Cheveux raides (lisses)", "type-1b"),
    "2": Famille("2", "Type 2", "Cheveux ondulés", "type-2b"),
    "3": Famille("3", "Type 3", "Cheveux bouclés", "type-3b"),
    "4": Famille("4", "Type 4", "Cheveux crépus et frisés", "type-4c"),
}


@dataclass(frozen=True)
class HairType:
    code: str
    famille: str
    nom: str
    description: str
    # Texture utilisée par le moteur de diagnostic (lisse, ondule, boucle, frise, crepu).
    texture: str
    # Problèmes fréquents : (identifiant du point de douleur, pourquoi chez ce type).
    problemes: tuple[tuple[str, str], ...]
    conseil_cle: str

    @property
    def visuel(self) -> str:
        return f"type-{self.code.lower()}"


HAIR_TYPES: dict[str, HairType] = {t.code: t for t in (
    HairType(
        "1A", "1", "Raides et fins",
        "Fins, plats et très brillants, difficiles à boucler.",
        "lisse",
        (
            ("alourdis", "Le sébum glisse très vite le long d'un cheveu fin et raide : "
                         "les racines graissent et les longueurs s'alourdissent."),
            ("volume", "Fins et plats, ils retombent au moindre produit un peu riche."),
        ),
        "Misez sur la légèreté : sprays, lotions, et rien de gras près des racines.",
    ),
    HairType(
        "1B", "1", "Raides avec du corps",
        "Moyennement épais, avec un peu plus de corps et de volume.",
        "lisse",
        (
            ("pointes", "Les longueurs raides frottent sur les vêtements : les pointes "
                        "s'abîment et fourchent."),
            ("terne", "La moindre trace de produit ou de calcaire se voit sur un cheveu lisse."),
        ),
        "Protégez les pointes et clarifiez une fois par mois pour garder la brillance.",
    ),
    HairType(
        "1C", "1", "Raides et épais",
        "Épais et raides, parfois un peu plus difficiles à discipliner.",
        "lisse",
        (
            ("frisottis", "Un cheveu épais gonfle avec l'humidité et se discipline moins bien."),
            ("secheresse", "Plus épais, il a besoin de plus de nutrition que les autres cheveux raides."),
        ),
        "Nourrissez les longueurs et finissez par une huile légère pour discipliner.",
    ),
    HairType(
        "2A", "2", "Ondulations souples",
        "Ondulations souples et lâches en forme de « S », très faciles à coiffer.",
        "ondule",
        (
            ("volume", "Le poids des produits riches aplatit facilement les ondulations légères."),
            ("alourdis", "Les ondulations 2A disparaissent dès que le cheveu est surchargé."),
        ),
        "Des soins légers et un séchage sans frotter suffisent à révéler l'ondulation.",
    ),
    HairType(
        "2B", "2", "Ondulations marquées",
        "Ondulations plus marquées et plus épaisses, qui commencent à friser avec l'humidité.",
        "ondule",
        (
            ("frisottis", "Les ondulations 2B frisent dès que l'air est humide."),
            ("definition", "Les vagues se défont si elles ne sont pas figées au séchage."),
        ),
        "Appliquez une mousse ou un gel léger sur cheveux trempés pour figer les vagues.",
    ),
    HairType(
        "2C", "2", "Ondulations prononcées",
        "Ondulations bien prononcées, proches de petites boucles, sujettes aux frisottis.",
        "ondule",
        (
            ("frisottis", "Proches de la boucle, les ondulations 2C sont très sujettes aux frisottis."),
            ("secheresse", "Le sébum descend moins bien le long d'une ondulation prononcée."),
            ("definition", "Sans soin adapté, les ondulations deviennent un volume flou."),
        ),
        "Traitez-les déjà comme des boucles : hydratation, gel, et séchage au diffuseur.",
    ),
    HairType(
        "3A", "3", "Boucles larges",
        "Boucles larges, souples et bien définies.",
        "boucle",
        (
            ("definition", "Les grandes boucles 3A se détendent et perdent leur forme au fil de la journée."),
            ("frisottis", "Toucher ses boucles ou les sécher en frottant crée vite des frisottis."),
        ),
        "Ne touchez plus vos boucles une fois coiffées, et réactivez-les avec un peu d'eau.",
    ),
    HairType(
        "3B", "3", "Boucles en ressort",
        "Boucles plus serrées, en forme de ressorts ou de tire-bouchons.",
        "boucle",
        (
            ("secheresse", "Plus la boucle est serrée, moins le sébum protège les longueurs."),
            ("frisottis", "Les boucles 3B gonflent dès qu'elles manquent d'hydratation."),
            ("demelage", "Les ressorts s'enroulent les uns autour des autres et forment des nœuds."),
        ),
        "Hydratez à chaque lavage et démêlez uniquement sous un soin bien glissant.",
    ),
    HairType(
        "3C", "3", "Boucles très serrées",
        "Boucles très serrées, denses et volumineuses (curly serré ou frisé).",
        "frise",
        (
            ("secheresse", "Très serrées et denses, ces boucles sèchent vite."),
            ("demelage", "La densité et la forme des boucles favorisent les nœuds."),
            ("casse", "Chaque courbe serrée est un point fragile, surtout au démêlage."),
        ),
        "Superposez les soins (eau, crème, huile) et démêlez par petites sections.",
    ),
    HairType(
        "4A", "4", "Petites boucles rebondies",
        "Petites boucles très serrées mais encore bien définies et rebondies.",
        "frise",
        (
            ("secheresse", "Les boucles 4A ont besoin d'une hydratation riche et régulière."),
            ("definition", "Sans hydratation, les petites boucles perdent leur définition."),
            ("casse", "Le cheveu est fin à chaque courbe : il casse si on le manipule à sec."),
        ),
        "Hydratez, scellez avec une crème ou un beurre, et définissez avec des vanilles.",
    ),
    HairType(
        "4B", "4", "Motif en Z",
        "Motifs en forme de « Z » ou de vagues très anguleuses, nécessitant beaucoup "
        "d'hydratation (risque de rétractation).",
        "crepu",
        (
            ("secheresse", "Les angles du motif en Z empêchent le sébum de descendre : "
                           "le cheveu sèche très vite."),
            ("casse", "Chaque angle est un point de fragilité où le cheveu peut casser."),
            ("pousse", "La rétractation peut atteindre 70 % : les cheveux paraissent bien "
                       "plus courts qu'ils ne le sont."),
            ("demelage", "Les angles s'accrochent entre eux et forment des nœuds."),
        ),
        "Hydratez beaucoup, scellez, et limitez les manipulations avec des coiffures protectrices.",
    ),
    HairType(
        "4C", "4", "Frisure très serrée",
        "Cheveux très denses au motif de frisure extrêmement serré, sans boucle vraiment "
        "définie, très fragiles et secs.",
        "crepu",
        (
            ("secheresse", "Les cheveux 4C sont les plus secs : le sébum ne descend presque pas "
                           "le long de la fibre."),
            ("casse", "Très fragiles, ils cassent au moindre démêlage à sec ou au frottement."),
            ("pousse", "La rétractation est extrême : la longueur réelle est souvent cachée."),
            ("demelage", "Le motif très serré forme facilement des nœuds."),
        ),
        "Méthode LOC ou LCO, coiffures protectrices, démêlage uniquement sur cheveux enduits de soin.",
    ),
)}

# Ajustement des besoins selon le type (en plus de la texture).
TYPE_POINTS: dict[str, dict[str, int]] = {
    "1A": {"volume": 2},
    "1B": {},
    "1C": {"nutrition": 1},
    "2A": {"volume": 1},
    "2B": {"hydratation": 1, "definition": 1},
    "2C": {"hydratation": 1, "definition": 2},
    "3A": {"definition": 1},
    "3B": {"hydratation": 1, "definition": 1},
    "3C": {"hydratation": 1, "nutrition": 1},
    "4A": {"definition": 1, "hydratation": 1},
    "4B": {"hydratation": 2, "reparation": 1},
    "4C": {"hydratation": 2, "nutrition": 1, "reparation": 2},
}

# Ajustement du poids des soins conseillés (négatif = plus léger).
TYPE_POIDS: dict[str, int] = {"1A": -1, "1C": 1, "2A": -1, "4C": 1}


def type_label(code: str) -> str:
    t = HAIR_TYPES[code]
    return f"{t.code} – {t.nom.lower()}"
