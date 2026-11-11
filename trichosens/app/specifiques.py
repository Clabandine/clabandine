"""Questions ciblées : problèmes propres à chaque famille de cheveux et démangeaisons.

Chaque réponse ajoute des points aux besoins et un conseil sur mesure. Les
familles concernées sont notées dans `familles` (ex. "34" : types 3 et 4).
"""

from dataclasses import dataclass, field


@dataclass(frozen=True)
class Specificite:
    id: str
    label: str
    familles: str
    points: dict[str, int]
    conseil: str
    hint: str = ""


SPECIFICITES: dict[str, Specificite] = {s.id: s for s in (
    # --- Type 1 : cheveux raides ----------------------------------------------
    Specificite(
        "racines_grasses", "Racines grasses dès le lendemain du lavage", "12",
        {"cuir_chevelu": 2, "volume": 1},
        "Sur un cheveu raide, le sébum glisse vite jusqu'aux longueurs. Lavez avec un shampoing "
        "doux et léger aussi souvent que nécessaire : un lavage fréquent n'abîme pas un cheveu "
        "raide s'il est doux. Entre deux, un shampoing sec seulement aux racines, et pas plus "
        "de deux jours de suite.",
    ),
    Specificite(
        "plats_racine", "Aucun volume à la racine, cheveux collés au crâne", "12",
        {"volume": 3},
        "Séchez d'abord les racines, tête en bas ou en les soulevant avec les doigts, puis les "
        "longueurs. Changez la raie de côté de temps en temps : elle retombe moins à plat.",
    ),
    Specificite(
        "coiffage_ne_tient_pas", "Les boucles ou le brushing ne tiennent pas", "1",
        {"volume": 2, "proteines": 1},
        "Un cheveu raide et lisse retient mal la forme. Appliquez une mousse ou un spray "
        "texturisant sur cheveux humides, laissez refroidir chaque mèche enroulée avant de la "
        "relâcher, et évitez les soins trop riches le jour du coiffage.",
    ),
    Specificite(
        "electricite", "Électricité statique, surtout en hiver", "12",
        {"hydratation": 1, "nutrition": 1},
        "L'électricité vient d'un cheveu sec qui frotte. Une goutte d'huile légère sur les "
        "longueurs, une brosse en poils naturels ou en bois, et un bonnet doublé de satin en "
        "hiver règlent souvent le problème.",
    ),
    # --- Type 2 : cheveux ondulés ---------------------------------------------
    Specificite(
        "ondulations_disparaissent", "Les ondulations disparaissent en cours de journée", "2",
        {"definition": 3},
        "Appliquez une mousse ou un gel léger sur cheveux trempés, puis froissez vers le haut. "
        "Laissez sécher sans toucher : une fois secs, froissez pour casser l'effet cartonné. "
        "Le lendemain, quelques pulvérisations d'eau suffisent à réveiller les vagues.",
    ),
    Specificite(
        "dessus_lisse", "Ondulés dessous, plus lisses sur le dessus", "23",
        {"definition": 2, "volume": 1},
        "C'est très courant : le dessus est plus exposé aux frottements et au soleil. Coiffez "
        "le dessus en premier, avec un peu plus de produit, et séchez-le tête en bas ou au "
        "diffuseur pour l'aider à onduler.",
    ),
    Specificite(
        "ecrases_produits", "Les produits pour boucles écrasent mes ondulations", "2",
        {"volume": 2},
        "Les soins pensés pour les boucles serrées sont trop riches pour des ondulations. "
        "Choisissez des textures légères (mousse, gel fluide, spray) et gardez les crèmes pour "
        "les pointes.",
    ),
    # --- Types 2 et 3 -----------------------------------------------------------
    Specificite(
        "boucles_lendemain", "Boucles écrasées ou défaites le lendemain", "23",
        {"definition": 2, "hydratation": 1},
        "La nuit, rassemblez vos cheveux en ananas (queue haute et lâche) sur une taie en "
        "satin. Le matin, vaporisez un mélange d'eau et de soin sans rinçage, puis froissez. "
        "Sur les mèches les plus défaites, enroulez-les autour de votre doigt.",
    ),
    Specificite(
        "halo_frisottis", "Un halo de frisottis sur le dessus de la tête", "23",
        {"hydratation": 1, "definition": 1},
        "Le dessus de la tête est la zone qui sèche le plus vite. Appliquez vos soins sur "
        "cheveux trempés, en finissant par le dessus, et lissez la surface avec un peu de gel "
        "du bout des doigts sans défaire les boucles.",
    ),
    Specificite(
        "gel_cartonne", "Le gel laisse les boucles cartonnées ou collantes", "234",
        {"definition": 1},
        "Le côté cartonné est normal : c'est le gel qui protège la boucle pendant le séchage. "
        "Une fois les cheveux bien secs, froissez-les avec une goutte d'huile sur les mains. "
        "S'ils restent collants, mettez moins de gel ou appliquez-le sur des cheveux plus "
        "mouillés.",
    ),
    # --- Types 3 et 4 -----------------------------------------------------------
    Specificite(
        "retractation", "Forte rétractation : mes cheveux paraissent bien plus courts", "34",
        {"hydratation": 1},
        "La rétractation est le signe de boucles en bonne santé, pas un défaut. Pour montrer "
        "la longueur sans chaleur : vanilles, tresses ou bantu knots défaits une fois secs, ou "
        "étirement en ananas. Mesurez une mèche étirée pour suivre la vraie pousse.",
    ),
    Specificite(
        "noeuds_fees", "Petits nœuds sur les pointes (nœuds de fée)", "34",
        {"reparation": 2, "hydratation": 1},
        "Les nœuds de fée se forment quand une boucle s'enroule sur elle-même. Coupez les "
        "nœuds existants (ils ne se défont pas), gardez les pointes bien hydratées et scellées, "
        "et dormez cheveux rassemblés sur du satin.",
    ),
    Specificite(
        "zones_textures", "Des boucles différentes selon les zones (nuque, tempes, dessus)", "234",
        {"definition": 1},
        "Avoir plusieurs textures sur la tête est très fréquent, notamment chez les cheveux "
        "métissés. Traitez chaque zone selon sa forme : plus de crème sur les zones les plus "
        "serrées (souvent la nuque), plus de gel léger sur les zones plus souples.",
    ),
    # --- Type 4 : cheveux crépus et frisés ---------------------------------------
    Specificite(
        "secs_lendemain", "Cheveux secs dès le lendemain de l'hydratation", "34",
        {"hydratation": 2, "nutrition": 2},
        "Votre hydratation s'évapore trop vite : scellez-la. Méthode LOC (Liquide, huile, "
        "crème) ou LCO (Liquide, crème, huile) sur cheveux mouillés, puis réhydratez les "
        "longueurs tous les 2 à 3 jours avec un spray d'eau et de soin.",
    ),
    Specificite(
        "casse_nuque", "Casse à la nuque ou au sommet du crâne", "34",
        {"reparation": 2, "proteines": 1},
        "Ces zones frottent sur le col, l'oreiller ou le dossier du siège. Protégez-les : "
        "bonnet ou foulard en satin la nuit, coiffures qui rassemblent la nuque, et une goutte "
        "d'huile sur les pointes de la nuque chaque jour.",
    ),
    Specificite(
        "tempes_clairsemees", "Tempes ou contour clairsemés", "34",
        {"cuir_chevelu": 2, "reparation": 1},
        "Des tempes qui s'éclaircissent sont souvent liées à des coiffures qui tirent (tresses "
        "serrées, tissages, perruques, chignons tendus). Faites des pauses entre deux coiffures, "
        "demandez des tresses sans tension sur le contour, et massez doucement les tempes. Si "
        "la zone ne repousse pas après quelques mois, consultez un dermatologue.",
    ),
    Specificite(
        "lavage_sous_tresses", "Cuir chevelu difficile à laver sous les coiffures protectrices",
        "34", {"cuir_chevelu": 2},
        "Sous les tresses, nettoyez le cuir chevelu toutes les 1 à 2 semaines : shampoing dilué "
        "dans un flacon applicateur, appliqué directement entre les tresses, massé puis bien "
        "rincé. Séchez soigneusement pour éviter les odeurs et les démangeaisons. Gardez une "
        "coiffure protectrice 6 à 8 semaines au plus.",
    ),
)}


@dataclass(frozen=True)
class DetailDemangeaison:
    id: str
    label: str
    hint: str
    points: dict[str, int]
    cause: str
    conseil: str
    alerte: str = ""
    # Type de cuir chevelu à traiter en priorité (pour choisir le shampoing).
    cuir: str = ""


DETAILS_DEMANGEAISONS: dict[str, DetailDemangeaison] = {d.id: d for d in (
    DetailDemangeaison(
        "pellicules_seches", "Petites pellicules blanches et sèches",
        "Elles tombent sur les épaules.",
        {"cuir_chevelu": 1, "hydratation": 1},
        "De petites pellicules sèches viennent souvent d'un cuir chevelu qui manque d'eau ou "
        "d'un lavage trop décapant.",
        "Passez à un shampoing doux, rincez à l'eau tiède plutôt que chaude, et appliquez un "
        "soin apaisant sur le cuir chevelu. Si elles persistent après 4 semaines, essayez un "
        "shampoing antipelliculaire doux une fois par semaine.",
        cuir="pellicules",
    ),
    DetailDemangeaison(
        "pellicules_grasses", "Pellicules jaunâtres, grasses ou collées",
        "Avec parfois des petites plaques.",
        {"cuir_chevelu": 2},
        "Des pellicules grasses sont le plus souvent liées à une levure naturelle de la peau "
        "(Malassezia) qui se développe trop : c'est la dermite séborrhéique, fréquente et "
        "bénigne.",
        "Utilisez un shampoing antipelliculaire 2 fois par semaine pendant 4 semaines, en le "
        "laissant poser 3 à 5 minutes avant de rincer, puis une fois par semaine en entretien.",
        cuir="pellicules",
    ),
    DetailDemangeaison(
        "rougeurs", "Rougeurs, brûlures ou picotements",
        "Le cuir chevelu réagit facilement.",
        {"cuir_chevelu": 2},
        "Des rougeurs et des picotements indiquent un cuir chevelu sensible ou irrité, "
        "souvent par le parfum, les sulfates ou l'eau trop chaude.",
        "Choisissez des soins sans parfum, au lavant doux, rincez à l'eau tiède, et testez "
        "chaque nouveau produit sur une petite zone avant de l'adopter.",
        cuir="sensible",
    ),
    DetailDemangeaison(
        "apres_produit", "Depuis un nouveau produit ou une coloration",
        "Shampoing, soin, teinture, défrisage…",
        {"cuir_chevelu": 1},
        "Des démangeaisons apparues après un nouveau produit évoquent une irritation ou une "
        "allergie à l'un de ses ingrédients.",
        "Arrêtez le produit suspect et revenez à des soins simples et sans parfum. Avant toute "
        "coloration, faites une touche d'essai 48 heures avant.",
        alerte="Si le cuir chevelu, le visage ou les paupières gonflent après une coloration, "
               "c'est une urgence : consultez un médecin sans attendre.",
        cuir="sensible",
    ),
    DetailDemangeaison(
        "sous_coiffure", "Sous des tresses, un tissage ou une perruque",
        "Le cuir chevelu respire moins et se lave mal.",
        {"cuir_chevelu": 2},
        "Sous une coiffure protectrice, le sébum, la sueur et les résidus s'accumulent, et les "
        "tresses trop serrées irritent la racine.",
        "Nettoyez le cuir chevelu entre les tresses toutes les 1 à 2 semaines avec un shampoing "
        "dilué, séchez bien, et appliquez une lotion apaisante légère (pas d'huile épaisse qui "
        "bouche). Une coiffure trop serrée qui démange doit être desserrée.",
    ),
    DetailDemangeaison(
        "entre_lavages", "Surtout quand j'espace les lavages",
        "Ça gratte de plus en plus jusqu'au lavage suivant.",
        {"cuir_chevelu": 2},
        "Quand on espace les lavages, le sébum, la sueur et les produits coiffants "
        "s'accumulent sur le cuir chevelu et finissent par l'irriter.",
        "Lavez un peu plus souvent le cuir chevelu, quitte à ne laver que lui : vos longueurs "
        "n'ont pas besoin d'un lavage à chaque fois. Faites un shampoing clarifiant une fois "
        "par mois pour retirer les résidus.",
    ),
    DetailDemangeaison(
        "plaques", "Plaques épaisses, croûtes, zones sans cheveux ou saignements",
        "", {"cuir_chevelu": 3},
        "Des plaques épaisses, des croûtes ou des zones sans cheveux peuvent révéler une "
        "maladie de peau (psoriasis, eczéma, teigne…) qui demande un vrai diagnostic.",
        "En attendant votre rendez-vous, utilisez des soins très doux et sans parfum, et "
        "évitez de gratter ou d'arracher les croûtes.",
        alerte="Plaques, croûtes, zones sans cheveux ou saignements du cuir chevelu : prenez "
               "rendez-vous avec un médecin ou un dermatologue. Ces signes demandent un "
               "examen, que TrichoSens ne peut pas remplacer.",
    ),
)}


# --- Mini-questionnaire pour trouver son type --------------------------------

@dataclass(frozen=True)
class Choix:
    value: str
    label: str
    hint: str = ""


FORMES: tuple[Choix, ...] = (
    Choix("1", "Ils restent droits", "Aucune vague, même après un lavage."),
    Choix("2", "Ils forment des vagues en S", "Des ondulations, pas de vraies boucles."),
    Choix("3", "Ils forment des boucles ou des spirales", "Des boucles qui tournent sur elles-mêmes."),
    Choix("4", "De toutes petites spirales ou des zigzags", "Un motif très serré, souvent dense."),
)

TAILLES: dict[str, tuple[Choix, ...]] = {
    "1": (
        Choix("A", "Très fins et plats", "Ils ne gardent aucune forme."),
        Choix("B", "Raides avec un peu de corps", "Un léger mouvement aux pointes."),
        Choix("C", "Raides mais épais", "Ils gonflent un peu, une petite ondulation par endroits."),
    ),
    "2": (
        Choix("A", "Vagues légères", "Surtout sur les longueurs, la racine reste plate."),
        Choix("B", "S bien dessinés", "À partir de la mi-longueur."),
        Choix("C", "S marqués dès la racine", "Avec quelques vraies boucles."),
    ),
    "3": (
        Choix("A", "Boucles larges", "Elles s'enrouleraient autour d'un gros feutre."),
        Choix("B", "Boucles en ressort", "Elles s'enrouleraient autour d'un crayon."),
        Choix("C", "Boucles serrées", "Elles s'enrouleraient autour d'une paille."),
    ),
    "4": (
        Choix("A", "Petites spirales bien définies",
              "Elles s'enrouleraient autour d'une aiguille à tricoter."),
        Choix("B", "Motif en Z", "Des angles plutôt que des spirales."),
        Choix("C", "Frisure très serrée", "Presque aucun motif visible, très dense."),
    ),
}

RETRACTATIONS: tuple[Choix, ...] = (
    Choix("aucune", "Pas de différence", "Mouillés ou secs, même longueur."),
    Choix("peu", "Un peu plus longs mouillés", "Jusqu'à 20 % environ."),
    Choix("beaucoup", "Nettement plus longs mouillés", "De 20 à 50 % environ."),
    Choix("enorme", "Beaucoup plus longs mouillés", "Plus de 50 % : ils doublent presque."),
)

TEXTURES: tuple[Choix, ...] = (
    Choix("une", "Non, la même partout"),
    Choix("plus_serrees", "Oui, certaines zones sont plus serrées",
          "Souvent la nuque ou l'arrière de la tête."),
    Choix("plus_souples", "Oui, certaines zones sont plus souples",
          "Souvent le dessus ou le devant."),
)

CODES = [f"{f}{s}" for f in "1234" for s in "ABC"]
RETRACTATION_ATTENDUE = {"1": 0, "2": 1, "3": 2, "4": 3}
RETRACTATION_NIVEAU = {c.value: i for i, c in enumerate(RETRACTATIONS)}


class ReponseInvalide(ValueError):
    pass


def trouver_type(forme: str, taille: str, retractation: str = "",
                 textures: str = "une") -> dict:
    """Propose le type le plus proche et, si besoin, un second type.

    Le second type couvre les cheveux « entre deux types » et ceux qui ont plusieurs
    textures (fréquent chez les cheveux métissés).
    """
    if forme not in TAILLES or taille not in {"A", "B", "C"}:
        raise ReponseInvalide("Choisissez la forme et la taille de vos boucles.")
    if retractation and retractation not in RETRACTATION_NIVEAU:
        raise ReponseInvalide("Réponse inconnue pour la rétractation.")
    if textures not in {c.value for c in TEXTURES}:
        raise ReponseInvalide("Réponse inconnue pour les textures.")

    principal = f"{forme}{taille}"
    i = CODES.index(principal)
    sens = 0
    raisons = []
    if retractation:
        ecart = RETRACTATION_NIVEAU[retractation] - RETRACTATION_ATTENDUE[forme]
        if ecart >= 1:
            sens = 1
            raisons.append("vos cheveux se rétractent plus que la moyenne de ce type")
        elif ecart <= -1:
            sens = -1
            raisons.append("vos cheveux se rétractent moins que la moyenne de ce type")
    if textures == "plus_serrees":
        sens = 1
        raisons.insert(0, "certaines zones de votre tête sont plus serrées")
    elif textures == "plus_souples":
        sens = -1
        raisons.insert(0, "certaines zones de votre tête sont plus souples")

    j = i + sens
    secondaire = CODES[j] if sens and 0 <= j < len(CODES) else None
    if secondaire:
        explication = (f"Votre type le plus proche est le {principal}, avec une part de "
                       f"{secondaire} : {raisons[0]}. Avoir deux types est très courant, "
                       "notamment pour les cheveux métissés : votre routine tiendra compte "
                       "des deux.")
    else:
        explication = (f"Votre type le plus proche est le {principal}. Vos réponses sont "
                       "cohérentes avec ce type.")
    return {"type": principal, "secondaire": secondaire, "explication": explication}
