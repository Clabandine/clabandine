"""Informations légales de l'éditrice du site (mentions légales, confidentialité, CGU).

À compléter ici quand la société est immatriculée. Un champ vide n'est pas affiché sur
le site ; le tableau de bord admin rappelle ce qui manque.
"""

import os

EDITEUR = {
    "nom": "TrichoSens",
    # Forme juridique et capital, par exemple « SAS au capital de 1 000 € ».
    "forme": os.environ.get("LEGAL_FORME", "SAS"),
    "capital": os.environ.get("LEGAL_CAPITAL", ""),
    "siren": os.environ.get("LEGAL_SIREN", ""),  # ou « RCS Versailles 123 456 789 »
    "ville": "Poissy, France",
    "email": "trichosens@gmail.com",
    # Personne responsable de ce qui est publié (en général la présidente de la SAS).
    "directeur_publication": os.environ.get("LEGAL_DIRECTEUR", ""),
}

HEBERGEUR = {
    "nom": "Render Services, Inc.",
    "adresse": "525 Brannan Street, Suite 300, San Francisco, CA 94107, États-Unis",
    "site": "https://render.com",
    "region": "serveurs situés à Francfort (Allemagne)",
}

MISE_A_JOUR = "19 novembre 2026"

LIBELLES_MANQUANTS = {
    "capital": "capital social",
    "siren": "numéro SIREN ou RCS",
    "directeur_publication": "directeur ou directrice de la publication",
}


def manquants() -> list[str]:
    """Mentions légales à compléter (affiché dans le tableau de bord admin)."""
    return [label for cle, label in LIBELLES_MANQUANTS.items() if not EDITEUR.get(cle)]
