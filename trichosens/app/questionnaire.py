"""Questions du diagnostic capillaire TrichoSens.

Les questions sont décrites sous forme de données : le formulaire web,
l'API et la validation s'appuient tous sur cette liste.
"""

import re
from dataclasses import dataclass, field

from .hair_types import HAIR_TYPES
from .pain_points import INTENSITES, PAIN_POINTS
from .profil import AGES, PERIODES, SENSIBILITES
from .sante import FACTEURS
from .specifiques import DETAILS_DEMANGEAISONS, SPECIFICITES


@dataclass(frozen=True)
class Option:
    value: str
    label: str
    hint: str = ""
    visuel: str = ""  # nom d'image (sans extension), voir main.visuel()
    groupe: str = ""  # famille de cheveux (1 à 4) pour la question du type


@dataclass(frozen=True)
class TestMaison:
    """Petit test à faire chez soi pour répondre plus justement."""

    titre: str
    duree: str
    etapes: tuple[str, ...]
    # (résultat observé, valeur de la réponse correspondante)
    resultats: tuple[tuple[str, str], ...]
    astuce: str = ""


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
    test: TestMaison | None = None

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
    Step("vous", "Vos cheveux au fil du temps",
         "Âge, période de vie, saisons : vos cheveux changent avec vous. Ces questions sont facultatives."),
    Step("habitudes", "Cuir chevelu et habitudes", "Ce que vivent vos cheveux au quotidien."),
    Step("objectif", "Objectif et préférences", "Dernières questions !"),
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
        id="demangeaisons_details",
        step="douleurs",
        label="Votre cuir chevelu : qu'observez-vous ?",
        help="Facultatif, plusieurs réponses possibles. Cela nous aide à trouver la cause de "
             "vos démangeaisons ou de vos pellicules.",
        multiple=True,
        required=False,
        options=tuple(Option(d.id, d.label, d.hint) for d in DETAILS_DEMANGEAISONS.values()),
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
        id="type_secondaire",
        step="cheveux",
        label="Vos cheveux mélangent-ils deux types ?",
        help="Facultatif. Fréquent quand on est entre deux types, avec des textures différentes "
             "selon les zones, ou pour les cheveux métissés.",
        required=False,
        options=tuple(Option(t.code, t.code, t.nom, "", t.famille) for t in HAIR_TYPES.values()),
    ),
    Question(
        id="specifiques",
        step="cheveux",
        label="Avec vos cheveux, qu'est-ce qui vous arrive souvent ?",
        help="Facultatif, plusieurs réponses possibles. Nous vous proposons les situations "
             "propres à votre type.",
        multiple=True,
        required=False,
        options=tuple(Option(x.id, x.label, x.hint, "", x.familles) for x in SPECIFICITES.values()),
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
        test=TestMaison(
            "Le test du fil", "1 minute",
            ("Prenez un cheveu tombé, propre et sec, et un fil à coudre.",
             "Posez-les côte à côte sur une feuille blanche et comparez."),
            (("Plus fin que le fil", "fin"), ("À peu près pareil", "moyen"),
             ("Plus épais que le fil", "epais")),
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
        test=TestMaison(
            "Le test de la queue de cheval", "1 minute",
            ("Rassemblez vos cheveux secs en queue de cheval, sans les tirer.",
             "Mesurez le tour de la queue avec un mètre ruban (ou une ficelle, puis une règle)."),
            (("Moins de 5 cm", "faible"), ("De 5 à 10 cm", "moyenne"), ("Plus de 10 cm", "forte")),
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
            Option("inconnue", "Je ne sais pas", "Faites le test ci-dessous : 5 minutes suffisent."),
        ),
        test=TestMaison(
            "Le test du verre d'eau", "5 minutes",
            ("Prenez 2 ou 3 cheveux tombés après un shampoing, sans soin ni produit (ils "
             "fausseraient le test).",
             "Déposez-les dans un verre d'eau à température ambiante.",
             "Attendez 3 à 4 minutes, puis regardez où ils sont."),
            (("Ils flottent en surface", "faible"), ("Ils restent au milieu", "moyenne"),
             ("Ils ont coulé au fond", "forte")),
            astuce="Autre test : vaporisez de l'eau sur une mèche sèche. Si les gouttes perlent, "
                   "la porosité est faible ; si elles sont absorbées tout de suite, elle est forte.",
        ),
    ),
    Question(
        id="elasticite",
        step="cheveux",
        label="Votre cheveu est-il élastique ?",
        help="Ce test dit si vos cheveux manquent plutôt d'hydratation ou de protéines.",
        required=False,
        options=(
            Option("equilibre", "Il s'étire un peu puis reprend sa forme",
                   "Bon équilibre entre hydratation et protéines."),
            Option("manque_proteines", "Il s'étire beaucoup, comme un chewing-gum, sans revenir",
                   "Il manque plutôt de protéines."),
            Option("manque_hydratation", "Il casse presque tout de suite, sans s'étirer",
                   "Il manque plutôt d'hydratation."),
            Option("non_teste", "Je n'ai pas fait le test"),
        ),
        test=TestMaison(
            "Le test d'élasticité", "1 minute",
            ("Prenez un cheveu tombé et mouillez-le.",
             "Tenez-le entre le pouce et l'index de chaque côté, et étirez-le doucement."),
            (("Il s'étire un peu puis revient", "equilibre"),
             ("Il s'étire beaucoup et ne revient pas", "manque_proteines"),
             ("Il casse presque tout de suite", "manque_hydratation")),
        ),
    ),
    Question(
        id="age",
        step="vous",
        label="Quel âge avez-vous ?",
        help="Les besoins des cheveux évoluent avec l'âge.",
        required=False,
        options=tuple(Option(k, v) for k, v in AGES.items()),
    ),
    Question(
        id="periodes",
        step="vous",
        label="Traversez-vous une période particulière ?",
        help="Plusieurs réponses possibles. Ces informations restent sur votre appareil.",
        multiple=True,
        required=False,
        options=tuple(Option(k, label, hint) for k, (label, hint) in PERIODES.items()),
    ),
    Question(
        id="sante",
        step="vous",
        label="Votre santé : l'un de ces points vous concerne-t-il ?",
        help="Facultatif, plusieurs réponses possibles. Certains problèmes de santé et "
             "carences jouent beaucoup sur les cheveux. Ces informations restent sur votre "
             "appareil et ne sont jamais enregistrées.",
        multiple=True,
        required=False,
        options=tuple(Option(f.id, f.label, f.hint, "", f.groupe) for f in FACTEURS.values()),
    ),
    Question(
        id="saisons_sensibles",
        step="vous",
        label="Vos cheveux changent-ils selon les saisons ?",
        help="Plusieurs réponses possibles : votre routine s'adaptera à chaque saison.",
        multiple=True,
        required=False,
        options=tuple(Option(k, s.label) for k, s in SENSIBILITES.items()),
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
    Question(
        id="preferences",
        step="objectif",
        label="Avez-vous des préférences pour vos produits ?",
        help="Facultatif. Plusieurs réponses possibles.",
        multiple=True,
        required=False,
        options=(
            Option("vegan", "Vegan", "Sans ingrédient d'origine animale."),
            Option("sans_parfum", "Sans parfum", "Pour les peaux et cuirs chevelus réactifs."),
            Option("sans_sulfates", "Sans sulfates", "Lavants plus doux."),
            Option("sans_silicones", "Sans silicones", "Pas de film sur la fibre."),
        ),
    ),
    Question(
        id="budget",
        step="objectif",
        label="Quel budget par produit ?",
        required=False,
        options=(
            Option("petit", "Petit budget", "Jusqu'à 12 € environ."),
            Option("moyen", "Budget moyen", "Jusqu'à 25 € environ."),
            Option("indifferent", "Peu importe", "Seule l'efficacité compte."),
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
    preferences: list[str] = field(default_factory=list)
    budget: str = "indifferent"
    age: str = "nc"
    elasticite: str = "non_teste"
    sante: list[str] = field(default_factory=list)
    periodes: list[str] = field(default_factory=list)
    saisons_sensibles: list[str] = field(default_factory=list)
    prenom: str = ""
    # Second type (cheveux entre deux types, plusieurs textures, cheveux métissés).
    type_secondaire: str = ""
    specifiques: list[str] = field(default_factory=list)
    demangeaisons_details: list[str] = field(default_factory=list)
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


PRENOM_RE = re.compile(r"^[^\W\d_]+(?:[ '’-][^\W\d_]+)*$")


def nettoyer_prenom(valeur) -> str:
    """Prénom facultatif : lettres, espaces, tirets et apostrophes, 30 caractères au plus.

    Une valeur qui ne ressemble pas à un prénom est simplement ignorée.
    """
    if not isinstance(valeur, str):
        return ""
    v = " ".join(valeur.split())[:30].strip()
    if not v or not PRENOM_RE.match(v):
        return ""
    return v[0].upper() + v[1:]


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
            if not value and not q.required:
                continue  # valeur par défaut de Answers
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

    # « Rien de particulier » / « Pas de différence » n'ont de sens que seuls.
    for qid, rien in (("periodes", "aucune"), ("saisons_sensibles", "aucune"), ("sante", "aucun")):
        if len(clean.get(qid, [])) > 1 and rien in clean[qid]:
            clean[qid] = [v for v in clean[qid] if v != rien]

    clean["prenom"] = nettoyer_prenom(raw.get("prenom"))

    # Questions qui dépendent d'une autre réponse : on ignore ce qui ne s'applique plus.
    principal = HAIR_TYPES.get(clean.get("type_cheveux", ""))
    if clean.get("type_secondaire") and (not principal
                                         or clean["type_secondaire"] == principal.code):
        clean.pop("type_secondaire")
    if principal:
        familles = {principal.famille}
        if clean.get("type_secondaire"):
            familles.add(HAIR_TYPES[clean["type_secondaire"]].famille)
        clean["specifiques"] = [v for v in clean.get("specifiques", [])
                                if familles & set(SPECIFICITES[v].familles)]
    if not {"demangeaisons", "pellicules"} & set(clean.get("preoccupations", [])):
        clean["demangeaisons_details"] = []

    if errors:
        raise InvalidAnswers(errors)
    return Answers(**clean)
