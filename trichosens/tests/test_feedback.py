from urllib.parse import parse_qs, urlsplit

from fastapi.testclient import TestClient

from app import main
from app.engine import run_diagnostic
from app.feedback import lien_avis
from app.questionnaire import validate

ANSWERS = {
    "type_cheveux": "4C", "epaisseur": "fin", "densite": "forte", "porosite": "forte",
    "cuir_chevelu": "sec", "chaleur": "jamais", "objectif": "longueur",
    "preoccupations": ["casse"], "intensites": {"casse": "enormement"},
    "age": "30_44", "periodes": ["grossesse"],
}
FORM_URL = ("https://docs.google.com/forms/d/e/ABC/viewform?usp=pp_url"
            "&entry.111=TS_RESUME&entry.222=TS_TYPE&entry.333=Texte+fixe")


def test_placeholders_are_replaced():
    d = run_diagnostic(validate(ANSWERS))
    q = parse_qs(urlsplit(lien_avis(FORM_URL, d)).query)
    assert q["entry.222"] == ["4C"]
    assert q["entry.333"] == ["Texte fixe"]
    resume = q["entry.111"][0]
    assert "Type 4C" in resume and "Casse (énormément)" in resume
    # Aucune donnée personnelle : ni âge ni période de vie.
    assert "30" not in resume and "grossesse" not in resume.lower()


def test_plain_link_is_unchanged():
    d = run_diagnostic(validate(ANSWERS))
    url = "https://docs.google.com/forms/d/e/ABC/viewform"
    assert lien_avis(url, d) == url


def test_result_page_uses_prefilled_link(monkeypatch):
    monkeypatch.setitem(main.templates.env.globals, "AVIS_URL", FORM_URL)
    form = {k: v for k, v in ANSWERS.items() if k != "intensites"}
    form["gene_casse"] = "enormement"
    r = TestClient(main.app).post("/diagnostic", data=form)
    assert "entry.222=4C" in r.text
