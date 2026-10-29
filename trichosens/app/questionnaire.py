"""Questions du diagnostic capillaire TrichoSens.

Les questions sont décrites sous forme de données : le formulaire web,
l'API et la validation s'appuient tous sur cette liste.
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    hint: str = ""


@dataclass(frozen=True)
class Question:
    id: str
    label: str
    options: tuple[Option, ...]
    multiple: bool = False
    help: str = ""
    required: bool = True
    max_choices: int | None = None

    def values(self) -> set[str]:
        return {o.value for o in self.options}


QUESTIONS: tuple[Question, ...] = (
    Question(
        id="texture",
        label="Quelle est la texture naturelle de vos cheveux ?",
        help="Observez vos cheveux au naturel, après un lavage, sans coiffage.",
        options=(
            Option("lisse", "Lisses", "Tombent droit, sans forme."),
            Option("ondule", "Ondulés", "Forment des vagues en S."),
            Option("boucle", "Bouclés", "Forment des boucles bien définies."),
            Option("frise", "Frisés", "Petites boucles serrées, en ressort."),
            Option("crepu", "Crépus", "Motif en zigzag très serré, fort rétrécissement."),
        ),
    ),
    Question(
        id="epaisseur",
        label="Quelle est l'épaisseur d'un cheveu ?",
        help="Faites rouler un cheveu entre vos doigts : le sentez-vous à peine, ou nettement ?",
        options=(
            Option("fin", "Fin", "On le sent à peine."),
            Option("moyen", "Moyen"),
            Option("epais", "Épais", "On le sent nettement, comme un fil."),
        ),
    ),
    Question(
        id="densite",
        label="Quelle est la densité de votre chevelure ?",
        help="Voit-on facilement votre cuir chevelu quand les cheveux sont secs ?",
        options=(
            Option("faible", "Faible", "Le cuir chevelu se voit facilement."),
            Option("moyenne", "Moyenne"),
            Option("forte", "Forte", "Le cuir chevelu se voit à peine."),
        ),
    ),
    Question(
        id="porosite",
        label="Comment vos cheveux réagissent-ils à l'eau ?",
        help="La porosité indique la facilité avec laquelle le cheveu absorbe et garde l'hydratation.",
        options=(
            Option("faible", "Ils mettent du temps à se mouiller et à sécher", "Porosité faible : les soins restent en surface."),
            Option("moyenne", "Ils se mouillent et sèchent normalement", "Porosité moyenne."),
            Option("forte", "Ils absorbent l'eau vite mais sèchent très vite", "Porosité forte : l'hydratation s'échappe vite."),
            Option("inconnue", "Je ne sais pas"),
        ),
    ),
    Question(
        id="cuir_chevelu",
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
        id="preoccupations",
        label="Quelles sont vos principales préoccupations ?",
        help="Choisissez jusqu'à 3 réponses.",
        multiple=True,
        max_choices=3,
        options=(
            Option("secheresse", "Sécheresse"),
            Option("casse", "Casse"),
            Option("frisottis", "Frisottis"),
            Option("chute", "Chute de cheveux"),
            Option("pointes", "Pointes abîmées ou fourchues"),
            Option("volume", "Manque de volume"),
            Option("definition", "Boucles peu définies"),
            Option("pousse", "Pousse lente"),
            Option("terne", "Cheveux ternes"),
        ),
    ),
    Question(
        id="traitements",
        label="Vos cheveux ont-ils subi des traitements chimiques ?",
        help="Plusieurs réponses possibles.",
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

    texture: str
    epaisseur: str
    densite: str
    porosite: str
    cuir_chevelu: str
    chaleur: str
    objectif: str
    preoccupations: list[str] = field(default_factory=list)
    traitements: list[str] = field(default_factory=list)


class InvalidAnswers(ValueError):
    def __init__(self, errors: dict[str, str]):
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))
        self.errors = errors


def validate(raw: dict[str, str | list[str] | None]) -> Answers:
    """Vérifie les réponses brutes et renvoie des `Answers` propres.

    Lève `InvalidAnswers` avec un message par question en erreur.
    """
    errors: dict[str, str] = {}
    clean: dict[str, str | list[str]] = {}

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

    if errors:
        raise InvalidAnswers(errors)
    return Answers(**clean)  # type: ignore[arg-type]
