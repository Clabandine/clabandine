import re

from fastapi.testclient import TestClient

from app.main import app

client = TestClient(app)

FORM = {
    "type_cheveux": "3C",
    "epaisseur": "fin",
    "densite": "forte",
    "porosite": "forte",
    "cuir_chevelu": "sec",
    "preoccupations": ["secheresse", "casse"],
    "gene_secheresse": "beaucoup",
    "gene_casse": "enormement",
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
    assert "type de cheveux" in r.text
    assert "4C · Frisure très serrée" in r.text
    assert "objectif principal" in r.text


def test_submit_form_shows_result():
    r = client.post("/diagnostic", data=FORM)
    assert r.status_code == 200
    assert "Votre routine sur mesure" in r.text
    assert "Protection thermique" in r.text
    assert "Ce qui vous gêne, et comment y remédier" in r.text
    assert "Votre type : 3C" in r.text
    pains = r.text[r.text.index("Ce qui vous gêne, et comment y remédier"):]
    assert pains.index("Casse") < pains.index("Sécheresse")  # la plus gênante d'abord


def test_incomplete_form_shows_errors_and_keeps_answers():
    r = client.post("/diagnostic", data={"type_cheveux": "3B"})
    assert r.status_code == 422
    assert "Cette question est obligatoire." in r.text
    assert re.search(r'value="3B"\s+checked', r.text)


def test_api_questions():
    r = client.get("/api/questions")
    assert r.status_code == 200
    assert r.json()["questions"][0]["id"] == "preoccupations"


API_PAYLOAD = {k: v for k, v in FORM.items() if not k.startswith("gene_")}
API_PAYLOAD["intensites"] = {"secheresse": "beaucoup", "casse": "enormement"}


def test_api_diagnostic():
    r = client.post("/api/diagnostic", json=API_PAYLOAD)
    assert r.status_code == 200
    body = r.json()
    assert body["routine"]
    assert set(body["besoins"]) >= {"hydratation", "proteines"}


def test_api_diagnostic_rejects_invalid():
    r = client.post("/api/diagnostic", json={"texture": "inconnue"})
    assert r.status_code == 422


def test_health_check():
    assert client.get("/sante").json() == {"statut": "ok"}
