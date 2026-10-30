# TrichoSens

> **Comprendre ses cheveux. Trouver les bons soins. Révéler leur potentiel.**

TrichoSens est une plateforme dédiée à la santé et à la beauté des cheveux. Elle aide
chacun à comprendre ses cheveux et à choisir des soins adaptés, quelle que soit la
texture : lisse, ondulée, bouclée, frisée ou crépue.

**Ambition :** devenir une plateforme internationale de référence du conseil capillaire
personnalisé, qui réunit diagnostic, accompagnement, e-commerce et, à terme, un
écosystème de marques et de professionnels.

## Ce que fait cette première version (v0.1)

1. **Diagnostic capillaire** : 9 questions (texture, épaisseur, densité, porosité,
   cuir chevelu, préoccupations, traitements chimiques, chaleur, objectif).
2. **Profil des besoins** : un score sur 100 pour l'hydratation, la nutrition, les
   protéines, la réparation, le cuir chevelu, la protection thermique, la définition et
   le volume. Les 3 besoins les plus forts sont les priorités.
3. **Routine sur mesure** : les étapes du jour de lavage, du quotidien, de la semaine ou
   du mois et de la nuit, avec la fréquence de lavage conseillée.
4. **Produits recommandés** : pour chaque étape, le produit du catalogue qui correspond
   le mieux au profil (texture, poids du soin, type de cuir chevelu, besoins).
5. **Conseils et alertes** : conseils pratiques, et une invitation à consulter un médecin
   en cas de chute ou de problème de cuir chevelu persistant.

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

## Organisation du code

```
trichosens/
├── app/
│   ├── main.py            # Application web (pages + API JSON)
│   ├── questionnaire.py   # Questions du diagnostic et validation des réponses
│   ├── engine.py          # Moteur : besoins, routine, produits, conseils
│   ├── catalog.py         # Chargement du catalogue de produits
│   ├── data/produits.json # Catalogue d'exemple
│   ├── templates/         # Pages HTML (accueil, questionnaire, résultat)
│   └── static/style.css   # Mise en page
└── tests/                 # Tests automatiques (pytest)
```

**Ajouter un produit :** ajoutez une entrée dans `app/data/produits.json`. Les champs
`textures` et `cuir_chevelu` vides veulent dire « convient à tous ».

**Ajuster le diagnostic :** les points attribués à chaque réponse sont dans les tableaux
en haut de `app/engine.py` (`TEXTURE_POINTS`, `PREOCCUPATION_POINTS`, etc.).

## API

| Méthode | Adresse            | Rôle                                        |
|---------|--------------------|---------------------------------------------|
| GET     | `/api/questions`   | Liste des questions et des réponses possibles |
| POST    | `/api/diagnostic`  | Envoie les réponses (JSON), renvoie le diagnostic |

Exemple :

```bash
curl -X POST http://127.0.0.1:8000/api/diagnostic -H "Content-Type: application/json" -d '{
  "texture": "boucle", "epaisseur": "fin", "densite": "moyenne", "porosite": "forte",
  "cuir_chevelu": "normal", "preoccupations": ["secheresse", "frisottis"],
  "traitements": [], "chaleur": "parfois", "objectif": "definition"
}'
```

## Feuille de route

- **v0.1 – Mise en ligne** : publier le diagnostic et recueillir les avis des premiers
  testeurs.
- **v0.2 – Diagnostic affiné** : ajuster les questions et les règles à partir de ces avis.
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
