"""Points de douleur : ce qui gêne la personne dans ses cheveux.

Pour chaque problème, on explique pourquoi il apparaît chez elle (selon son
profil), ce qu'on va faire, ce qu'il faut éviter et quand espérer des résultats.
"""

from collections.abc import Callable
from dataclasses import dataclass, field
from typing import TYPE_CHECKING

from .hair_types import HAIR_TYPES

if TYPE_CHECKING:
    from .questionnaire import Answers

Condition = Callable[["Answers"], bool]

INTENSITES = {
    "un_peu": "Un peu",
    "beaucoup": "Beaucoup",
    "enormement": "Énormément",
}
INTENSITE_FACTEUR = {"un_peu": 0.7, "beaucoup": 1.0, "enormement": 1.4}


def _bouclés(a: "Answers") -> bool:
    return a.texture in {"boucle", "frise", "crepu"}


def _traites(a: "Answers") -> bool:
    return bool(set(a.traitements) & {"decoloration", "lissage", "permanente"})


@dataclass(frozen=True)
class PainPoint:
    id: str
    label: str
    description: str
    causes: tuple[str, ...]
    causes_profil: tuple[tuple[Condition, str], ...]
    actions: tuple[str, ...]
    a_eviter: tuple[str, ...]
    delai: str


PAIN_POINTS: dict[str, PainPoint] = {}


def _add(p: PainPoint) -> None:
    PAIN_POINTS[p.id] = p


_add(PainPoint(
    id="secheresse",
    label="Sécheresse",
    description="Cheveux rêches, qui manquent de souplesse et cassent au toucher.",
    causes=("Le cheveu perd son eau plus vite qu'il ne la reçoit.",),
    causes_profil=(
        (_bouclés, "Sur les cheveux bouclés à crépus, le sébum du cuir chevelu descend mal le long "
                   "des boucles : les longueurs sont naturellement moins protégées."),
        (lambda a: a.porosite == "forte", "Votre porosité forte laisse l'hydratation s'échapper "
                                          "rapidement : il faut la sceller."),
        (lambda a: a.porosite == "faible", "Votre porosité faible empêche les soins de pénétrer : "
                                           "ils restent en surface sans hydrater."),
        (lambda a: a.chaleur == "souvent", "La chaleur fréquente évapore l'eau contenue dans la fibre."),
        (_traites, "Les traitements chimiques ont ouvert les écailles du cheveu, qui retient moins bien l'eau."),
    ),
    actions=(
        "Hydrater d'abord (eau, soin sans rinçage à base d'aloe vera ou de glycérine), nourrir ensuite.",
        "Faire un masque hydratant à chaque lavage pendant 4 semaines.",
        "Sceller avec une huile ou un beurre sur cheveux encore humides.",
    ),
    a_eviter=(
        "Les shampoings aux sulfates forts (sodium lauryl sulfate).",
        "Les huiles appliquées sur cheveux secs : elles scellent la sécheresse au lieu de l'hydratation.",
    ),
    delai="Des cheveux plus souples dès 2 à 3 lavages, un vrai changement en 4 à 6 semaines.",
))

_add(PainPoint(
    id="casse",
    label="Casse",
    description="Des petits morceaux de cheveux dans la brosse, sur les vêtements ou le lavabo.",
    causes=("Le cheveu casse quand il manque de résistance (protéines) ou d'élasticité (hydratation).",),
    causes_profil=(
        (lambda a: "decoloration" in a.traitements, "La décoloration détruit une partie de la kératine : "
                                                    "le cheveu devient fragile et cassant."),
        (lambda a: "lissage" in a.traitements, "Le lissage ou le défrisage modifie la structure interne "
                                               "du cheveu et l'affaiblit durablement."),
        (lambda a: a.chaleur != "jamais", "Les outils chauffants fragilisent la fibre à chaque passage."),
        (lambda a: a.texture in {"frise", "crepu"}, "Chaque angle d'une boucle serrée est un point "
                                                    "de faiblesse : ces cheveux cassent plus facilement "
                                                    "au démêlage."),
        (lambda a: a.epaisseur == "fin", "Un cheveu fin contient moins de matière et résiste moins."),
    ),
    actions=(
        "Alterner masque protéiné et masque hydratant d'une semaine à l'autre.",
        "Démêler uniquement sur cheveux mouillés et enduits de soin, en partant des pointes.",
        "Protéger les cheveux la nuit (satin) et limiter les coiffures qui tirent.",
    ),
    a_eviter=(
        "Brosser les cheveux secs, surtout s'ils sont bouclés.",
        "Les élastiques avec partie métallique.",
        "Enchaîner les traitements chimiques sans pause.",
    ),
    delai="Moins de casse visible en 3 à 4 semaines si les gestes sont réguliers.",
))

_add(PainPoint(
    id="frisottis",
    label="Frisottis",
    description="Des cheveux qui gonflent et se dressent, surtout avec l'humidité.",
    causes=("Un cheveu qui a soif prend l'humidité de l'air : il gonfle et ses écailles se soulèvent.",),
    causes_profil=(
        (lambda a: a.texture != "lisse", "Les cheveux ondulés à crépus ont des écailles naturellement "
                                         "plus soulevées : ils frisottent plus facilement."),
        (lambda a: a.porosite == "forte", "Votre porosité forte absorbe l'humidité de l'air très vite."),
    ),
    actions=(
        "Appliquer les soins sur cheveux trempés, pas seulement humides.",
        "Finir par un gel ou une crème coiffante pour figer la forme.",
        "Sécher sans frotter : serviette microfibre, t-shirt en coton ou diffuseur.",
    ),
    a_eviter=(
        "Les serviettes éponge classiques.",
        "Toucher ses cheveux pendant qu'ils sèchent.",
    ),
    delai="Visible dès le prochain lavage, de mieux en mieux en 3 à 4 semaines.",
))

_add(PainPoint(
    id="chute",
    label="Chute de cheveux",
    description="Plus de cheveux que d'habitude sur l'oreiller, sous la douche ou dans la brosse.",
    causes=(
        "Perdre 50 à 100 cheveux par jour est normal. Au-delà, la chute peut venir du stress, d'un "
        "changement hormonal, d'une carence (fer, vitamine D), de la saison ou d'une maladie.",
    ),
    causes_profil=(
        (lambda a: a.cuir_chevelu in {"sensible", "pellicules"}, "Un cuir chevelu irrité peut entretenir "
                                                                 "une chute : il faut d'abord l'apaiser."),
        (lambda a: a.texture in {"frise", "crepu"}, "Les coiffures très serrées (tresses, tissages) "
                                                    "peuvent arracher les cheveux des tempes."),
    ),
    actions=(
        "Masser le cuir chevelu 3 à 5 minutes, plusieurs fois par semaine.",
        "Utiliser un soin du cuir chevelu adapté.",
        "Faire un bilan avec un médecin si la chute dure plus de 3 mois ou est soudaine.",
    ),
    a_eviter=(
        "Les coiffures qui tirent sur les racines.",
        "Les régimes très restrictifs.",
    ),
    delai="Un cycle de pousse dure environ 3 mois : comptez 3 mois avant de juger un soin anti-chute.",
))

_add(PainPoint(
    id="pointes",
    label="Pointes abîmées",
    description="Pointes sèches, fourchues, plus fines ou plus claires que le reste.",
    causes=("Les pointes sont la partie la plus ancienne du cheveu : elles ont subi tous les frottements.",),
    causes_profil=(
        (lambda a: a.chaleur != "jamais", "La chaleur abîme en premier les pointes."),
        (_traites, "Les traitements chimiques fragilisent surtout les longueurs et les pointes."),
    ),
    actions=(
        "Couper les pointes fourchues : aucun soin ne les recolle durablement.",
        "Nourrir les pointes chaque jour avec une goutte d'huile ou de sérum.",
        "Protéger les pointes la nuit et dans les coiffures (chignon, tresse lâche).",
    ),
    a_eviter=(
        "Laisser les pointes frotter sur les vêtements en laine ou les écharpes.",
        "Attendre trop longtemps pour couper : la fourche remonte le long du cheveu.",
    ),
    delai="Effet immédiat après la coupe ; à entretenir tous les 3 mois.",
))

_add(PainPoint(
    id="volume",
    label="Manque de volume",
    description="Cheveux plats, collés au crâne, qui manquent de corps.",
    causes=("Le volume dépend de l'épaisseur du cheveu, de la densité et du poids des produits.",),
    causes_profil=(
        (lambda a: a.epaisseur == "fin", "Vos cheveux fins s'alourdissent très vite."),
        (lambda a: a.densite == "faible", "Avec une densité faible, chaque cheveu compte : il faut éviter "
                                          "tout ce qui les colle entre eux."),
        (lambda a: a.cuir_chevelu == "gras", "Un cuir chevelu gras fait retomber les racines."),
    ),
    actions=(
        "Choisir des soins légers et les appliquer loin des racines.",
        "Faire un shampoing clarifiant une fois par mois.",
        "Sécher tête en bas ou en soulevant les racines.",
    ),
    a_eviter=(
        "Les beurres, huiles riches et silicones lourds.",
        "Les après-shampoings appliqués sur le cuir chevelu.",
    ),
    delai="Visible dès le prochain lavage.",
))

_add(PainPoint(
    id="definition",
    label="Boucles peu définies",
    description="Boucles qui se défont, se regroupent mal ou ressemblent à un nuage flou.",
    causes=("Une boucle se forme quand le cheveu est bien hydraté et qu'on l'aide à garder sa forme.",),
    causes_profil=(
        (lambda a: a.chaleur != "jamais", "La chaleur casse peu à peu la forme naturelle de la boucle."),
        (lambda a: "lissage" in a.traitements, "Les parties lissées ou défrisées ne retrouveront pas "
                                               "leur boucle : seule la repousse sera naturelle."),
        (lambda a: a.porosite == "faible", "Avec une porosité faible, les résidus de produits "
                                           "alourdissent les boucles."),
    ),
    actions=(
        "Appliquer les soins par sections sur cheveux trempés.",
        "Utiliser un gel pour figer la boucle, puis froisser une fois sec.",
        "Ne pas toucher les cheveux pendant le séchage.",
    ),
    a_eviter=(
        "Brosser les boucles une fois sèches.",
        "Les serviettes éponge.",
    ),
    delai="Visible dès le prochain lavage, la méthode s'affine en 3 à 4 lavages.",
))

_add(PainPoint(
    id="pousse",
    label="Longueur qui stagne",
    description="L'impression que les cheveux ne poussent plus.",
    causes=(
        "Les cheveux poussent en moyenne de 1 cm par mois. Si la longueur stagne, c'est presque "
        "toujours parce que les pointes cassent aussi vite qu'elles poussent.",
    ),
    causes_profil=(
        (lambda a: a.texture in {"frise", "crepu"}, "Les cheveux frisés et crépus se rétractent "
                                                    "beaucoup : ils sont souvent plus longs qu'ils "
                                                    "n'en ont l'air."),
        (_traites, "Les cheveux traités cassent plus vite aux pointes."),
    ),
    actions=(
        "Mesurer une mèche témoin chaque mois pour suivre la vraie pousse.",
        "Protéger les pointes : coiffures protectrices, satin, huile.",
        "Masser le cuir chevelu pour l'entretenir.",
    ),
    a_eviter=(
        "Les manipulations quotidiennes inutiles.",
        "Les coupes trop rares si les pointes fourchent.",
    ),
    delai="Comptez 3 mois pour constater un gain de longueur.",
))

_add(PainPoint(
    id="terne",
    label="Cheveux ternes",
    description="Des cheveux sans éclat, qui ne reflètent pas la lumière.",
    causes=("Un cheveu brille quand ses écailles sont bien à plat et qu'il est nourri.",),
    causes_profil=(
        (lambda a: a.porosite == "faible", "Des résidus de produits ou de calcaire peuvent ternir "
                                           "vos cheveux."),
        (lambda a: a.porosite == "forte", "Des écailles ouvertes renvoient mal la lumière."),
        (_bouclés, "Les boucles renvoient naturellement moins la lumière que les cheveux lisses : "
                   "il faut nourrir davantage."),
    ),
    actions=(
        "Finir le rinçage à l'eau fraîche.",
        "Appliquer une huile légère sur les longueurs.",
        "Faire un shampoing clarifiant une fois par mois.",
    ),
    a_eviter=("Les eaux très calcaires sans clarifiant régulier.",),
    delai="Visible dès 1 à 2 lavages.",
))

_add(PainPoint(
    id="demelage",
    label="Démêlage difficile",
    description="Des nœuds, et des démêlages longs ou douloureux.",
    causes=("Les nœuds se forment quand les écailles accrochent entre elles et que le cheveu est sec.",),
    causes_profil=(
        (_bouclés, "Les boucles s'enroulent les unes autour des autres : les nœuds sont plus fréquents."),
        (lambda a: a.porosite == "forte", "Des écailles ouvertes accrochent davantage."),
    ),
    actions=(
        "Démêler uniquement sous un après-shampoing ou un masque bien glissant.",
        "Travailler par sections, des pointes vers les racines.",
        "Rassembler les cheveux la nuit (ananas, tresses lâches).",
    ),
    a_eviter=("Démêler à sec ou avec une brosse à poils serrés.",),
    delai="Démêlage plus facile dès le prochain lavage.",
))

_add(PainPoint(
    id="alourdis",
    label="Cheveux vite alourdis",
    description="Les cheveux deviennent plats, collants ou gras peu après le lavage.",
    causes=("Les produits trop riches ou mal rincés s'accumulent sur la fibre.",),
    causes_profil=(
        (lambda a: a.epaisseur == "fin", "Vos cheveux fins supportent mal les produits riches."),
        (lambda a: a.porosite == "faible", "Avec une porosité faible, les soins ne pénètrent pas et "
                                           "restent en surface."),
        (lambda a: a.cuir_chevelu == "gras", "Votre cuir chevelu produit beaucoup de sébum."),
    ),
    actions=(
        "Passer à des textures légères (sprays, lotions, gels).",
        "Faire un shampoing clarifiant pour repartir de zéro.",
        "Appliquer les soins seulement à partir de la mi-longueur.",
    ),
    a_eviter=("Les beurres et huiles épaisses près des racines.",),
    delai="Visible dès le prochain lavage.",
))


@dataclass
class PainReport:
    id: str
    label: str
    description: str
    intensite: str
    intensite_label: str
    causes: list[str]
    actions: list[str]
    a_eviter: list[str]
    delai: str
    vu_sur_photo: bool = False
    note_photo: str = ""
    extra: dict = field(default_factory=dict)

    def to_dict(self) -> dict:
        return {k: v for k, v in self.__dict__.items() if k != "extra"}


INTENSITE_ORDRE = {"enormement": 0, "beaucoup": 1, "un_peu": 2}


def explain(a: "Answers") -> list[PainReport]:
    """Explique chaque point de douleur choisi, du plus gênant au moins gênant."""
    reports = []
    for pid in a.preoccupations:
        p = PAIN_POINTS[pid]
        intensite = a.intensites.get(pid, "beaucoup")
        causes = list(p.causes)
        typ = HAIR_TYPES[a.type_cheveux]
        causes += [f"Fréquent chez le type {typ.code} : {why[0].lower()}{why[1:]}"
                   for prob, why in typ.problemes if prob == pid]
        causes += [text for cond, text in p.causes_profil if cond(a)]
        reports.append(PainReport(
            id=p.id, label=p.label, description=p.description,
            intensite=intensite, intensite_label=INTENSITES[intensite],
            causes=causes, actions=list(p.actions), a_eviter=list(p.a_eviter), delai=p.delai,
        ))
    reports.sort(key=lambda r: INTENSITE_ORDRE[r.intensite])
    return reports
