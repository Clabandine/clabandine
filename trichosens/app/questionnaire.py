"""Questions du diagnostic capillaire TrichoSens.

Les questions sont décrites sous forme de données : le formulaire web,
l'API et la validation s'appuient tous sur cette liste.
"""

from dataclasses import dataclass, field

from .hair_types import HAIR_TYPES
from .pain_points import INTENSITES, PAIN_POINTS


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    hint: str = ""
    visuel: str = ""  # nom d'image (sans extension), voir main.visuel()
    groupe: str = ""  # famille de cheveux (1 à 4) pour la question du type


@dataclass(frozen=True)
class Question:
    id: str
    step: str
    label: str
    options: tuple[Option, ...]
    multiple: bool = False
    help: str = ""
    required: bool = True
    max_choices: int | None = None

    def values(self) -> set[str]:
        return {o.value for o in self.options}

    @property
    def has_visuals(self) -> bool:
        return any(o.visuel for o in self.options)


@dataclass(frozen=True)
class Step:
    id: str
    titre: str
    intro: str


STEPS: tuple[Step, ...] = (
    Step("douleurs", "Ce qui vous gêne",
         "Commençons par l'essentiel : qu'est-ce qui vous dérange dans vos cheveux aujourd'hui ?"),
    Step("photo", "Votre photo",
         "Facultatif : notre IA observe vos cheveux pour affiner le diagnostic."),
    Step("cheveux", "Vos cheveux", "Apprenons à connaître la nature de vos cheveux."),
    Step("habitudes", "Cuir chevelu et habitudes", "Ce que vivent vos cheveux au quotidien."),
    Step("objectif", "Votre objectif", "Dernière question !"),
)

QUESTIONS: tuple[Question, ...] = (
    Question(
        id="preoccupations",
        step="douleurs",
        label="Qu'est-ce qui vous gêne le plus dans vos cheveux ?",
        help="Choisissez jusqu'à 3 réponses, puis dites-nous à quel point cela vous gêne.",
        multiple=True,
        max_choices=3,
        options=tuple(Option(p.id, p.label, p.description) for p in PAIN_POINTS.values()),
    ),
    Question(
        id="type_cheveux",
        step="cheveux",
        label="Quel est votre type de cheveux ?",
        help="Observez vos cheveux au naturel, après un lavage, sans coiffage. "
             "Choisissez d'abord la famille, puis le type le plus proche.",
        options=tuple(
            Option(t.code, f"{t.code} · {t.nom}", t.description, t.visuel, t.famille)
            for t in HAIR_TYPES.values()
        ),
    ),
    Question(
        id="epaisseur",
        step="cheveux",
        label="Quelle est l'épaisseur d'un cheveu ?",
        help="Faites rouler un cheveu entre vos doigts : le sentez-vous à peine, ou nettement ?",
        options=(
            Option("fin", "Fin", "On le sent à peine.", "epaisseur-fin"),
            Option("moyen", "Moyen", "On le sent sous les doigts.", "epaisseur-moyen"),
            Option("epais", "Épais", "On le sent nettement, comme un fil.", "epaisseur-epais"),
        ),
    ),
    Question(
        id="densite",
        step="cheveux",
        label="Quelle est la densité de votre chevelure ?",
        help="Voit-on facilement votre cuir chevelu quand les cheveux sont secs ?",
        options=(
            Option("faible", "Faible", "Le cuir chevelu se voit facilement.", "densite-faible"),
            Option("moyenne", "Moyenne", "Le cuir chevelu se voit un peu.", "densite-moyenne"),
            Option("forte", "Forte", "Le cuir chevelu se voit à peine.", "densite-forte"),
        ),
    ),
    Question(
        id="porosite",
        step="cheveux",
        label="Comment vos cheveux réagissent-ils à l'eau ?",
        help="La porosité indique la facilité avec laquelle le cheveu absorbe et garde l'hydratation.",
        options=(
            Option("faible", "Ils mettent du temps à se mouiller et à sécher",
                   "Porosité faible : les écailles sont fermées, les soins restent en surface.",
                   "porosite-faible"),
            Option("moyenne", "Ils se mouillent et sèchent normalement",
                   "Porosité moyenne : l'équilibre idéal.", "porosite-moyenne"),
            Option("forte", "Ils absorbent l'eau vite mais sèchent très vite",
                   "Porosité forte : les écailles sont ouvertes, l'hydratation s'échappe.",
                   "porosite-forte"),
            Option("inconnue", "Je ne sais pas", "Nous vous expliquerons comment la tester."),
        ),
    ),
    Question(
        id="cuir_chevelu",
        step="habitudes",
        label="Comment décririez-vous votre cuir chevelu ?",
        options=(
            Option("normal", "Normal"),
            Option("sec", "Sec, tiraille"),
            Option("gras", "Gras, regraisse vite"),
            Option("sensible", "Sensible, démange ou rougit"),
            Option("pellicules", "Avec des pellicules"),
        ),
    ),
    Question(
        id="traitements",
        step="habitudes",
        label="Vos cheveux ont-ils subi des traitements chimiques ?",
        help="Plusieurs réponses possibles. Ne cochez rien si ce n'est pas le cas.",
        multiple=True,
        required=False,
        options=(
            Option("coloration", "Coloration"),
            Option("decoloration", "Décoloration ou mèches"),
            Option("lissage", "Lissage ou défrisage"),
            Option("permanente", "Permanente"),
        ),
    ),
    Question(
        id="chaleur",
        step="habitudes",
        label="À quelle fréquence utilisez-vous des outils chauffants ?",
        help="Lisseur, fer à boucler, sèche-cheveux à température élevée.",
        options=(
            Option("jamais", "Jamais ou presque"),
            Option("parfois", "Quelques fois par mois"),
            Option("souvent", "Plusieurs fois par semaine"),
        ),
    ),
    Question(
        id="objectif",
        step="objectif",
        label="Quel est votre objectif principal ?",
        options=(
            Option("hydratation", "Des cheveux mieux hydratés"),
            Option("definition", "Des boucles plus définies"),
            Option("volume", "Plus de volume"),
            Option("longueur", "Garder la longueur, limiter la casse"),
            Option("sante_cuir", "Un cuir chevelu sain"),
            Option("brillance", "Plus de brillance"),
        ),
    ),
)

QUESTIONS_BY_ID: dict[str, Question] = {q.id: q for q in QUESTIONS}


@dataclass
class Answers:
    """Réponses validées au questionnaire."""

    type_cheveux: str
    epaisseur: str
    densite: str
    porosite: str
    cuir_chevelu: str
    chaleur: str
    objectif: str
    preoccupations: list[str] = field(default_factory=list)
    traitements: list[str] = field(default_factory=list)
    # Intensité de la gêne pour chaque préoccupation : un_peu, beaucoup ou enormement.
    intensites: dict[str, str] = field(default_factory=dict)

    @property
    def texture(self) -> str:
        """Grande texture déduite du type : lisse, ondule, boucle, frise ou crepu."""
        return HAIR_TYPES[self.type_cheveux].texture

    @property
    def famille(self) -> str:
        return HAIR_TYPES[self.type_cheveux].famille


class InvalidAnswers(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


def validate(raw: dict) -> Answers:
    """Vérifie les réponses brutes et renvoie des `Answers` propres.

    `raw["intensites"]` est un dictionnaire {préoccupation: intensité}.
    Lève `InvalidAnswers` avec un message par question en erreur.
    """
    errors: dict[str, str] = {}
    clean: dict = {}

    for q in QUESTIONS:
        value = raw.get(q.id)
        if q.multiple:
            if value is None:
                items: list[str] = []
            elif isinstance(value, str):
                items = [value]
            else:
                items = list(value)
            items = list(dict.fromkeys(v for v in items if v))  # sans doublons
            unknown = [v for v in items if v not in q.values()]
            if unknown:
                errors[q.id] = f"Réponse inconnue : {', '.join(unknown)}"
            elif q.required and not items:
                errors[q.id] = "Choisissez au moins une réponse."
            elif q.max_choices and len(items) > q.max_choices:
                errors[q.id] = f"Choisissez au maximum {q.max_choices} réponses."
            clean[q.id] = items
        else:
            if isinstance(value, list):
                value = value[0] if value else None
            if not value:
                errors[q.id] = "Cette question est obligatoire."
            elif value not in q.values():
                errors[q.id] = f"Réponse inconnue : {value}"
            else:
                clean[q.id] = value

    raw_intensites = raw.get("intensites") or {}
    if not isinstance(raw_intensites, dict):
        raw_intensites = {}
    intensites = {}
    for pid in clean.get("preoccupations", []):
        value = raw_intensites.get(pid)
        if not value:
            errors[f"gene_{pid}"] = "Dites-nous à quel point cela vous gêne."
        elif value not in INTENSITES:
            errors[f"gene_{pid}"] = f"Réponse inconnue : {value}"
        else:
            intensites[pid] = value
    clean["intensites"] = intensites

    if errors:
        raise InvalidAnswers(errors)
    return Answers(**clean)
