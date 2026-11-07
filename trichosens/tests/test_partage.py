from fastapi.testclient import TestClient

from app.engine import run_diagnostic
from app.feedback import valeurs
from app.main import app
from app.partage import texte_partage
from app.questionnaire import nettoyer_prenom, validate

client = TestClient(app)
ANSWERS = {
    "type_cheveux": "3B", "epaisseur": "moyen", "densite": "moyenne", "porosite": "forte",
    "cuir_chevelu": "normal", "chaleur": "jamais", "objectif": "definition",
    "preoccupations": ["secheresse"], "intensites": {"secheresse": "beaucoup"},
}


def test_first_name_is_cleaned():
    assert nettoyer_prenom("  clarisse ") == "Clarisse"
    assert nettoyer_prenom("Marie-Anne") == "Marie-Anne"
    assert nettoyer_prenom("N'Dèye") == "N'Dèye"
    assert nettoyer_prenom("<script>") == ""
    assert nettoyer_prenom("Jean2") == ""
    assert nettoyer_prenom(None) == ""
    assert len(nettoyer_prenom("A" * 50)) == 30


def test_first_name_is_optional_and_kept_in_history():
    assert validate(ANSWERS).prenom == ""
    d = run_diagnostic(validate({**ANSWERS, "prenom": "awa"}))
    assert d.prenom == "Awa" and d.suivi["prenom"] == "Awa"


def test_first_name_is_never_sent_with_feedback():
    d = run_diagnostic(validate({**ANSWERS, "prenom": "Awa"}))
    assert all("Awa" not in v for v in valeurs(d).values())


def test_share_text():
    d = run_diagnostic(validate({**ANSWERS, "prenom": "Awa"}))
    text = texte_partage(d, "https://trichosens.example/")
    assert text.startswith("Ma routine TrichoSens – Awa")
    assert "Type de cheveux : 3B" in text and "Le jour du lavage :" in text
    assert text.rstrip().endswith("https://trichosens.example/")


def test_result_page_greets_and_offers_sharing():
    form = {k: v for k, v in ANSWERS.items() if k != "intensites"}
    form.update(gene_secheresse="beaucoup", prenom="Awa")
    r = client.post("/diagnostic", data=form)
    assert r.status_code == 200
    assert "Awa, voici votre profil capillaire" in r.text
    assert "Ma fiche PDF" in r.text and "data-share" in r.text
    assert 'class="fiche"' in r.text and "Awa, votre routine capillaire" in r.text


def test_questionnaire_has_first_name_field():
    assert 'name="prenom"' in client.get("/diagnostic").text
