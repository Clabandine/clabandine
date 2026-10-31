# TrichoSens

> **Comprendre ses cheveux. Trouver les bons soins. Révéler leur potentiel.**

TrichoSens est une plateforme dédiée à la santé et à la beauté des cheveux. Elle aide
chacun à comprendre ses cheveux et à choisir des soins adaptés, quelle que soit la
texture : lisse, ondulée, bouclée, frisée ou crépue.

**Ambition :** devenir une plateforme internationale de référence du conseil capillaire
personnalisé, qui réunit diagnostic, accompagnement, e-commerce et, à terme, un
écosystème de marques et de professionnels.

## Ce que fait la version actuelle (v0.5)

1. **Ce qui vous gêne d'abord** : le diagnostic commence par les points de douleur
   (sécheresse, casse, frisottis, chute, démêlage…) et leur intensité.
2. **Analyse photo par IA (facultative)** : l'IA (Claude, d'Anthropic) reconnaît le type
   de cheveux et les signes visibles, et pré-remplit les réponses. La photo n'est jamais
   enregistrée.
3. **Les 12 types de cheveux (1A à 4C)**, chacun avec ses problèmes fréquents
   (`app/hair_types.py`).
4. **Résultat centré sur les problèmes** : causes propres au profil, actions, à éviter, délai.
5. **Programme de soins** : phase intensive (4 semaines), puis entretien, avec la date du
   prochain point.
6. **Saisons** : besoins, conseils et choix des produits adaptés à la saison en cours.
7. **Évolution des cheveux** : chaque diagnostic est gardé sur l'appareil de la personne.
   Le suivant est comparé au précédent (mieux, stable, en hausse, réglé, nouveau) et le
   programme s'adapte : entretien si ça progresse, ajustement ciblé sinon. La page
   **Mon suivi** montre l'historique, l'évolution des besoins et un journal de pousse
   (mèche témoin).
8. **Catalogue de produits réels** : 51 produits de marques disponibles en France.
9. **Préférences** : vegan, sans parfum, sans sulfates, sans silicones, et budget par
   produit (petit : 12 € environ, moyen : 25 € environ). Les produits qui respectent le
   plus de préférences passent en premier ; sinon, le résultat le signale. Le budget de
   départ de la routine est affiché, et les préférences sont reprises au diagnostic suivant.
10. **Rappels dans l'agenda** : la personne choisit ses jours de lavage et une heure, puis
    télécharge un fichier agenda (.ics) avec ses rappels : jours de lavage, shampoing
    clarifiant et mesure de la mèche témoin (une fois par mois), coupe des pointes (tous
    les 3 mois) et prochain diagnostic. Aucun compte ni serveur de notifications.

### Le catalogue

Le catalogue est le tableau `app/data/produits.csv` (séparateur « ; »), qui s'ouvre dans
Google Sheets ou Excel. **Les prix sont indicatifs et toutes les fiches sont à vérifier**
(colonne `a_verifier`) : formules et prix changent souvent.

| Colonne | Contenu |
|---|---|
| `categorie` | shampoing, apres_shampoing, masque, leave_in, coiffant, huile, protecteur_thermique, soin_cuir, shampoing_clarifiant, accessoire |
| `besoins` | hydratation, nutrition, proteines, reparation, cuir_chevelu, protection, definition, volume (+ `anti_chute`, réservé aux personnes qui ont de la chute) |
| `poids` | leger, moyen ou riche |
| `types` | types de cheveux, avec des plages : `3A-4C`, `1A\|2B`. Vide = tous |
| `cuir_chevelu` | normal, sec, gras, sensible, pellicules. Vide = tous |
| `saisons` | hiver, printemps, été, automne : le produit est favorisé à cette saison |
| `sans_parfum`, `sans_sulfates`, `sans_silicones`, `vegan` | oui, non, ou vide si inconnu |
| `prix_indicatif`, `contenance` | prix moyen constaté et format |
| `a_verifier`, `date_verification` | `non` + date une fois la fiche vérifiée (voir plus bas) |

Dans les colonnes à plusieurs valeurs, séparez les valeurs par `|`. Après modification,
lancez `pytest` : les tests signalent toute ligne mal remplie.

### Liens d'achat et affiliation

Les liens d'achat sont dans un second tableau, `app/data/liens.csv` : une ligne par
revendeur et par produit. Un produit peut avoir plusieurs revendeurs ; les 3 moins chers
s'affichent sous forme de boutons « Acheter chez… ».

| Colonne | Contenu |
|---|---|
| `produit_id` | l'`id` du produit dans `produits.csv` |
| `marchand` | nom affiché : Amazon, Sephora, Notino… |
| `url` | votre lien (affilié ou non), qui doit commencer par `https://` |
| `prix` | prix chez ce revendeur (facultatif) |
| `affilie` | `oui` si c'est un lien d'affiliation : la mention « Lien affilié » s'affiche |
| `actif` | `non` pour masquer le lien sans le supprimer |
| `awin_mid` | pour un revendeur Awin : son **ID annonceur** (voir ci-dessous) |

Dès qu'un lien affilié s'affiche, le résultat explique que TrichoSens peut toucher une
commission (obligation légale en France). Le choix des produits ne dépend jamais des
commissions.

**Amazon Partenaires (identifiant `trichosens-21`) :** chaque produit a un lien de recherche
Amazon avec cet identifiant, créé par `python scripts/liens_amazon.py` (le script n'ajoute un
lien qu'aux produits qui n'en ont pas). Pour vendre davantage, remplacez peu à peu ces liens par
le lien direct de la fiche, créé avec la barre SiteStripe d'Amazon. Ne renseignez jamais de prix
pour Amazon : son règlement l'interdit hors de son interface officielle. La phrase obligatoire
« En tant que Partenaire Amazon… » s'affiche automatiquement.

**Awin (identifiant éditeur `2944635`) :** pour un revendeur auquel vous êtes acceptée sur
Awin, collez dans `url` l'adresse normale de la page produit, et dans `awin_mid` l'ID annonceur
du revendeur (tableau de bord Awin, rubrique des annonceurs : le numéro à côté du nom). Le
site fabrique alors le lien affilié avec votre identifiant, et le marque comme affilié.

**Clics :** les boutons passent par `/acheter/...`, qui compte le clic puis redirige vers le
revendeur. Les statistiques sont sur `/admin/clics?cle=VOTRE_CLE`. La clé `ADMIN_CLE` est
générée par Render (service trichosens, puis **Environment**). Les compteurs repartent à
zéro à chaque redémarrage du site : pour les ventes et les commissions, fiez-vous aux
tableaux de bord des programmes d'affiliation.

### Garder le catalogue à jour

- **Date de vérification :** après avoir vérifié une fiche (composition, prix, labels, types de
  cheveux), mettez `a_verifier` à `non` et la date du jour dans `date_verification`
  (`2026-11-30` ou `30/11/2026`). Une fiche est à revoir si elle n'a jamais été vérifiée, si
  elle est marquée « à vérifier », si sa vérification date de plus de 6 mois, ou si elle n'a
  aucun lien d'achat. La liste est sur `/admin/catalogue?cle=VOTRE_CLE`.
- **Contrôle des liens chaque lundi :** GitHub lance `scripts/verifier_catalogue.py`. En cas de
  lien mort (page introuvable), le contrôle échoue et GitHub vous prévient par e-mail ; le
  rapport s'affiche dans l'onglet **Actions** du dépôt. Les liens de recherche Amazon ne sont
  pas contrôlés (une recherche existe toujours) et certains sites bloquent les robots : ils
  apparaissent comme « non vérifiables ». Lancement à la main : onglet **Actions**,
  « Contrôle du catalogue TrichoSens », **Run workflow**.

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
l'illustration : `type-1a.webp` à `type-4c.webp`, `epaisseur-fin.jpg`,
`densite-forte.jpg`, `porosite-faible.jpg`… La photo remplace automatiquement
l'illustration.
Utilisez uniquement des photos dont vous avez les droits (vos propres photos avec
l'accord des personnes, ou des banques d'images libres comme Unsplash ou Pexels).

## Organisation du code

```
trichosens/
├── app/
│   ├── main.py            # Application web (pages + API JSON)
│   ├── questionnaire.py   # Étapes, questions du diagnostic et validation des réponses
│   ├── hair_types.py      # Les 12 types de cheveux et leurs problèmes fréquents
│   ├── pain_points.py     # Points de douleur : causes, actions, à éviter, délais
│   ├── photo.py           # Analyse photo par l'IA (Claude)
│   ├── seasons.py         # Adaptation à la saison
│   ├── evolution.py       # Comparaison avec le diagnostic précédent
│   ├── reminders.py       # Rappels : fichier agenda (.ics)
│   ├── engine.py          # Moteur : besoins, programme, routine, produits, conseils
│   ├── catalog.py         # Lecture et vérification du catalogue
│   ├── data/produits.csv  # Catalogue de produits (tableau)
│   ├── data/liens.csv     # Liens d'achat par revendeur (affiliation)
│   ├── clicks.py          # Comptage des clics sur les liens d'achat
│   ├── templates/         # Pages HTML (accueil, questionnaire, résultat, suivi)
│   └── static/            # Mise en page, scripts (questionnaire, suivi), images
├── scripts/               # Illustrations, liens Amazon, contrôle du catalogue
└── tests/                 # Tests automatiques (pytest)
```

**Ajouter un produit :** ajoutez une ligne dans `app/data/produits.csv` (voir plus haut).

**Ajuster le diagnostic :** les points attribués à chaque réponse sont dans les tableaux
en haut de `app/engine.py` (`TEXTURE_POINTS`, `PREOCCUPATION_POINTS`, etc.).

## API

| Méthode | Adresse            | Rôle                                        |
|---------|--------------------|---------------------------------------------|
| GET     | `/api/questions`   | Étapes, questions et réponses possibles |
| POST    | `/api/analyse-photo` | Envoie une photo (`photo`, `consentement=oui`), renvoie l'analyse |
| POST    | `/api/diagnostic`  | Envoie les réponses (JSON), renvoie le diagnostic |
| GET     | `/rappels.ics`     | Fichier agenda des rappels (`jours`, `heure`, `rappels`, `prochain`…) |

Exemple :

```bash
curl -X POST http://127.0.0.1:8000/api/diagnostic -H "Content-Type: application/json" -d '{
  "type_cheveux": "3A", "epaisseur": "fin", "densite": "moyenne", "porosite": "forte",
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
- **v0.3 – Les 12 types de cheveux** (1A à 4C) et leurs problèmes fréquents.
- **v0.4 – Catalogue réel, programme, saisons et suivi** : produits réels, phases de soins,
  conseils de saison, historique et comparaison des diagnostics sur l'appareil.
- **Ensuite** : photos dans le suivi, puis comptes utilisateurs pour retrouver son suivi sur tous ses appareils.
- **v0.5 – E-commerce** : panier, paiement, partenariats avec les marques.
- **v0.6 – Professionnels** : annuaire de coiffeurs et trichologues, prise de rendez-vous.
- **Plus tard** : analyse photo des cheveux, application mobile, plusieurs langues.

## Avertissement

TrichoSens donne des conseils de soin et ne remplace pas l'avis d'un médecin ou d'un
dermatologue.
