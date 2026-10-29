import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FORM = {
    "texture": "frise",
    "epaisseur": "fin",
    "densite": "forte",
    "porosite": "forte",
    "cuir_chevelu": "sec",
    "preoccupations": ["secheresse", "casse"],
    "chaleur": "parfois",
    "objectif": "longueur",
}


def test_home_page():
    r = client.get("/")
    assert r.status_code == 200
    assert "Commencer mon diagnostic" in r.text


def test_questionnaire_page_lists_all_questions():
    r = client.get("/diagnostic")
    assert r.status_code == 200
    assert "texture naturelle" in r.text
    assert "objectif principal" in r.text


def test_submit_form_shows_result():
    r = client.post("/diagnostic", data=FORM)
    assert r.status_code == 200
    assert "Votre routine sur mesure" in r.text
    assert "Protection thermique" in r.text


def test_incomplete_form_shows_errors_and_keeps_answers():
    r = client.post("/diagnostic", data={"texture": "boucle"})
    assert r.status_code == 422
    assert "Cette question est obligatoire." in r.text
    assert re.search(r'value="boucle"\s+checked', r.text)


def test_api_questions():
    r = client.get("/api/questions")
    assert r.status_code == 200
    assert [q["id"] for q in r.json()][0] == "texture"


def test_api_diagnostic():
    r = client.post("/api/diagnostic", json=FORM)
    assert r.status_code == 200
    body = r.json()
    assert body["routine"]
    assert set(body["besoins"]) >= {"hydratation", "proteines"}


def test_api_diagnostic_rejects_invalid():
    r = client.post("/api/diagnostic", json={"texture": "inconnue"})
    assert r.status_code == 422
