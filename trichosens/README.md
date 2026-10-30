# TrichoSens

> **Comprendre ses cheveux. Trouver les bons soins. Révéler leur potentiel.**

TrichoSens est une plateforme dédiée à la santé et à la beauté des cheveux. Elle aide
chacun à comprendre ses cheveux et à choisir des soins adaptés, quelle que soit la
texture : lisse, ondulée, bouclée, frisée ou crépue.

**Ambition :** devenir une plateforme internationale de référence du conseil capillaire
personnalisé, qui réunit diagnostic, accompagnement, e-commerce et, à terme, un
écosystème de marques et de professionnels.

## Ce que fait la version actuelle (v0.2)

1. **Ce qui vous gêne d'abord** : le diagnostic commence par les points de douleur
   (sécheresse, casse, frisottis, chute, démêlage…) et leur intensité.
2. **Analyse photo par IA (facultative)** : la personne prend ses cheveux en photo ;
   l'IA (Claude, d'Anthropic) observe la texture, l'épaisseur, la densité et les signes
   visibles (sécheresse, frisottis, pointes abîmées…). Elle pré-remplit les réponses,
   confirme ou complète les points de douleur. La photo n'est jamais enregistrée.
3. **Questionnaire illustré** en 5 étapes : texture, épaisseur, densité et porosité sont
   illustrées, puis cuir chevelu, habitudes et objectif.
4. **Résultat centré sur les problèmes** : pour chaque point de douleur, pourquoi il
   apparaît chez cette personne, ce qu'on va faire, ce qu'il faut éviter et le délai
   pour voir des résultats.
5. **Besoins, routine et produits** : scores sur 100, routine du jour de lavage au soin
   de nuit, et produit recommandé pour chaque étape.

Le catalogue (`app/data/produits.json`) contient des **produits génériques d'exemple**,
à remplacer par les produits des marques partenaires.

## Lancer le projet

Il faut Python 3.10 ou plus récent.

```bash
cd trichosens
python -m venv .venv
source .venv/bin/activate        # sous Windows : .venv\Scripts\activate
pip install -r requirements-dev.txt

uvicorn app.main:app --reload
```

Ouvrez ensuite http://127.0.0.1:8000 dans votre navigateur.
La documentation de l'API est sur http://127.0.0.1:8000/docs.

Lancer les tests :

```bash
pytest
```

## Mettre en ligne (Render, gratuit)

Le fichier `render.yaml` à la racine du dépôt décrit tout l'hébergement.

1. Créez un compte sur https://render.com en vous connectant avec GitHub.
2. Cliquez sur **New +**, puis **Blueprint**, et choisissez le dépôt `Clabandine/clabandine`.
3. Choisissez la branche à publier (`main` une fois le code fusionné), puis validez.
4. Après 2 à 3 minutes, le site est en ligne à une adresse du type
   `https://trichosens.onrender.com`.

Chaque nouvel envoi sur cette branche met le site à jour automatiquement.
Avec l'offre gratuite, le site se met en veille après 15 minutes sans visite :
la première page met alors une trentaine de secondes à s'afficher.

### Activer l'analyse photo

1. Créez une clé sur https://console.anthropic.com (rubrique **API Keys**) et ajoutez
   un moyen de paiement. Une analyse coûte quelques centimes.
2. Dans Render, ouvrez le service **trichosens**, puis **Environment**, et donnez sa
   valeur à `ANTHROPIC_API_KEY`.
3. `PHOTO_MAX_PAR_HEURE` (par personne) et `PHOTO_MAX_PAR_JOUR` (pour tout le site)
   limitent le nombre d'analyses, et donc la dépense.

En local : `export ANTHROPIC_API_KEY=...` avant `uvicorn`.

## Images

Les réponses illustrées utilisent des dessins vectoriels générés par
`scripts/generate_illustrations.py` (dans `app/static/img/illustrations/`).

**Pour les remplacer par des photos HD**, déposez un fichier JPG, PNG ou WebP carré
(1000 × 1000 pixels conseillés) dans `app/static/img/photos/`, avec le même nom que
l'illustration : `texture-lisse.jpg`, `texture-ondule.jpg`, `texture-boucle.jpg`,
`texture-frise.jpg`, `texture-crepu.jpg`, `epaisseur-fin.jpg`, `densite-forte.jpg`,
`porosite-faible.jpg`… La photo remplace automatiquement l'illustration.
Utilisez uniquement des photos dont vous avez les droits (vos propres photos avec
l'accord des personnes, ou des banques d'images libres comme Unsplash ou Pexels).

## Organisation du code

```
trichosens/
├── app/
│   ├── main.py            # Application web (pages + API JSON)
│   ├── questionnaire.py   # Étapes, questions du diagnostic et validation des réponses
│   ├── pain_points.py     # Points de douleur : causes, actions, à éviter, délais
│   ├── photo.py           # Analyse photo par l'IA (Claude)
│   ├── engine.py          # Moteur : besoins, routine, produits, conseils
│   ├── catalog.py         # Chargement du catalogue de produits
│   ├── data/produits.json # Catalogue d'exemple
│   ├── templates/         # Pages HTML (accueil, questionnaire, résultat)
│   └── static/            # Mise en page, script du questionnaire, images
├── scripts/               # Génération des illustrations
└── tests/                 # Tests automatiques (pytest)
```

**Ajouter un produit :** ajoutez une entrée dans `app/data/produits.json`. Les champs
`textures` et `cuir_chevelu` vides veulent dire « convient à tous ».

**Ajuster le diagnostic :** les points attribués à chaque réponse sont dans les tableaux
en haut de `app/engine.py` (`TEXTURE_POINTS`, `PREOCCUPATION_POINTS`, etc.).

## API

| Méthode | Adresse            | Rôle                                        |
|---------|--------------------|---------------------------------------------|
| GET     | `/api/questions`   | Étapes, questions et réponses possibles |
| POST    | `/api/analyse-photo` | Envoie une photo (`photo`, `consentement=oui`), renvoie l'analyse |
| POST    | `/api/diagnostic`  | Envoie les réponses (JSON), renvoie le diagnostic |

Exemple :

```bash
curl -X POST http://127.0.0.1:8000/api/diagnostic -H "Content-Type: application/json" -d '{
  "texture": "boucle", "epaisseur": "fin", "densite": "moyenne", "porosite": "forte",
  "cuir_chevelu": "normal", "preoccupations": ["secheresse", "frisottis"],
  "intensites": {"secheresse": "enormement", "frisottis": "un_peu"},
  "traitements": [], "chaleur": "parfois", "objectif": "definition"
}'
```

## Feuille de route

- **v0.1 – Mise en ligne** : publier le diagnostic et recueillir les avis des premiers
  testeurs.
- **v0.2 – Diagnostic affiné** : points de douleur, analyse photo par IA, questionnaire
  illustré. À ajuster ensuite avec les avis des testeurs.
- **v0.3 – Catalogue réel** : base de données de produits (ingrédients, prix, liens),
  filtres (vegan, sans parfum, budget).
- **v0.4 – Comptes utilisateurs** : sauvegarder son diagnostic et suivre l'évolution
  de ses cheveux (journal, photos, rappels de routine).
- **v0.5 – E-commerce** : panier, paiement, partenariats avec les marques.
- **v0.6 – Professionnels** : annuaire de coiffeurs et trichologues, prise de rendez-vous.
- **Plus tard** : analyse photo des cheveux, application mobile, plusieurs langues.

## Avertissement

TrichoSens donne des conseils de soin et ne remplace pas l'avis d'un médecin ou d'un
dermatologue.
