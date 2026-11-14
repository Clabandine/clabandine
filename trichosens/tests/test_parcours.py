import re

from fastapi.testclient import TestClient

from app.main import app
from app.questionnaire import PHASES_PARCOURS, QUESTIONS, STEPS

client = TestClient(app)


def panneaux(html):
    return re.findall(r'<section class="step-panel" data-step="([a-z]+)"', html)


def test_accueil_puis_description_puis_diagnostic():
    ids = [s.id for s in STEPS]
    assert ids[:3] == ["bienvenue", "description", "douleurs"]
    assert {q.id: q.step for q in QUESTIONS}["age"] == "bienvenue"


def test_chaque_etape_a_une_partie_et_une_duree():
    for s in STEPS:
        assert s.phase in PHASES_PARCOURS and s.duree > 0
    # Les parties se suivent dans l'ordre (pas de retour en arrière).
    ordre = [list(PHASES_PARCOURS).index(s.phase) for s in STEPS]
    assert ordre == sorted(ordre)


def test_pages_du_questionnaire():
    html = client.get("/diagnostic").text
    etapes = panneaux(html)
    assert etapes[:3] == ["bienvenue", "description", "douleurs"]
    bienvenue = html.split('data-step="bienvenue"')[1].split('data-step="description"')[0]
    assert 'id="prenom"' in bienvenue and 'name="age"' in bienvenue
    description = html.split('data-step="description"')[1].split('data-step="douleurs"')[0]
    assert 'id="description"' in description
    assert "Passer cette étape" in description
    assert "Commencer →" in bienvenue and "Retour" not in bienvenue
    assert html.count("← Retour") == len(etapes) - 1
    assert "Voir mon diagnostic ✨" in html
    for label in PHASES_PARCOURS.values():
        assert label in html


def test_le_formulaire_complet_fonctionne_toujours():
    form = {"prenom": "Awa", "age": "30_44", "type_cheveux": "4A", "epaisseur": "fin",
            "densite": "forte", "porosite": "forte", "cuir_chevelu": "sec",
            "preoccupations": ["secheresse"], "gene_secheresse": "beaucoup",
            "chaleur": "jamais", "objectif": "hydratation"}
    r = client.post("/diagnostic", data=form)
    assert r.status_code == 200 and "Awa, voici votre profil capillaire" in r.text
