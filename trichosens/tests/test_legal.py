from fastapi.testclient import TestClient

from app import legal
from app.main import app

client = TestClient(app)


def test_pages_legales():
    for url, titre in (("/mentions-legales", "Mentions légales"),
                       ("/confidentialite", "Politique de confidentialité"),
                       ("/conditions", "Conditions d'utilisation")):
        r = client.get(url)
        assert r.status_code == 200 and titre in r.text
        assert "trichosens@gmail.com" in r.text


def test_mentions_obligatoires():
    r = client.get("/mentions-legales").text
    assert "Render Services" in r and "Poissy" in r
    assert "Partenaire Amazon" in r and "pas un diagnostic" in r


def test_confidentialite_sante_et_ia():
    r = client.get("/confidentialite").text
    assert "jamais enregistrées" in r and "Anthropic" in r and "CNIL" in r


def test_liens_dans_le_pied_de_page():
    r = client.get("/").text
    for url in ("/mentions-legales", "/confidentialite", "/conditions"):
        assert f'href="{url}"' in r


def test_champs_vides_masques_et_rappeles(monkeypatch):
    monkeypatch.setitem(legal.EDITEUR, "siren", "")
    assert "Immatriculation" not in client.get("/mentions-legales").text
    assert "numéro SIREN ou RCS" in legal.manquants()
    monkeypatch.setitem(legal.EDITEUR, "siren", "RCS Versailles 123 456 789")
    assert "RCS Versailles 123 456 789" in client.get("/mentions-legales").text
