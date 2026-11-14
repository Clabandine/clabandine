from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient

from app import texte
from app.main import app
from app.questionnaire import validate
from app.texte import ExtractionIA, TexteErreur, analyser, extraire_regles

client = TestClient(app)


def regles(t):
    return extraire_regles(t)["reponses"], extraire_regles(t)["intensites"]


# --- Règles -----------------------------------------------------------------------


def test_genes_type_et_details():
    r, i = regles("J'ai des cheveux bouclés 3C, très secs, qui cassent énormément. Mon cuir "
                  "chevelu gratte depuis que je porte des tresses et j'ai des pellicules grasses.")
    assert r["type_cheveux"] == "3C"
    assert r["preoccupations"][0] == "casse"  # la plus gênante d'abord
    assert set(r["preoccupations"]) == {"casse", "secheresse", "demangeaisons"}
    assert i == {"casse": "enormement", "secheresse": "beaucoup", "demangeaisons": "beaucoup"}
    assert set(r["demangeaisons_details"]) == {"pellicules_grasses", "sous_coiffure"}


def test_negations_ignorees():
    r, _ = regles("Je n'ai pas de pellicules et aucune chute. Par contre mes cheveux sont ternes.")
    assert r["preoccupations"] == ["terne"]


def test_mais_coupe_la_negation():
    r, _ = regles("Je n'ai pas de pellicules mais mon cuir chevelu est sensible.")
    assert r["cuir_chevelu"] == "sensible"
    assert "preoccupations" not in r


def test_pousse_avec_ne_pas():
    r, _ = regles("Mes cheveux ne poussent pas.")
    assert r["preoccupations"] == ["pousse"]


def test_cuir_chevelu_sec_n_est_pas_une_secheresse():
    r, _ = regles("Mon cuir chevelu est sec et j'ai des pellicules sèches.")
    assert r["cuir_chevelu"] == "sec"
    assert r["preoccupations"] == ["pellicules"]


def test_intensite_un_peu():
    _, i = regles("J'ai un peu de frisottis.")
    assert i == {"frisottis": "un_peu"}


def test_maximum_trois_genes():
    r, _ = regles("Secs, cassants, frisottis, chute, pellicules, ternes, noeuds.")
    assert len(r["preoccupations"]) == 3


def test_famille_par_les_mots_et_habitudes():
    r, _ = regles("Cheveux raides et fins, racines grasses dès le lendemain, aucun volume. "
                  "Brushing tous les jours. 34 ans, coloration et mèches.")
    assert r["famille"] == "1" and r["epaisseur"] == "fin" and r["cuir_chevelu"] == "gras"
    assert r["chaleur"] == "souvent" and r["age"] == "30_44"
    assert set(r["traitements"]) == {"coloration", "decoloration"}
    assert r["specifiques"] == ["racines_grasses"]


def test_jamais_de_chaleur_et_grossesse():
    r, _ = regles("Jamais de lisseur. Je suis enceinte.")
    assert r["chaleur"] == "jamais" and r["periodes"] == ["grossesse"]


def test_objectif_seulement_dans_un_souhait():
    assert "objectif" not in regles("Mes cheveux ont du volume.")[0]
    assert regles("J'aimerais plus de volume.")[0]["objectif"] == "volume"


def test_metisse_et_deux_types():
    res = extraire_regles("Je suis métisse : 3C sur le dessus, 4A à la nuque.")
    assert res["metisse"] is True
    assert res["reponses"]["type_cheveux"] == "3C"
    assert res["reponses"]["type_secondaire"] == "4A"


def test_toutes_les_reponses_sont_valides():
    res = extraire_regles(
        "Cheveux bouclés 3B, très secs, frisottis, cuir chevelu gras, pellicules grasses, "
        "rétractation, nœuds de fée. Coloration. Lisseur parfois. J'aimerais des boucles "
        "définies. 27 ans, stress.")
    r = res["reponses"]
    data = {"epaisseur": "moyen", "densite": "moyenne", "porosite": "moyenne",
            "cuir_chevelu": "normal", "chaleur": "jamais", "objectif": "hydratation",
            **r, "intensites": res["intensites"]}
    a = validate(data)
    assert a.type_cheveux == "3B" and a.specifiques


def test_resume_lisible():
    res = analyser("Cheveux crépus, très secs. Porosité forte.")
    assert "Sécheresse (beaucoup)" in res["resume"]
    assert "cheveux crépus ou frisés" in res["resume"]
    assert "porosité forte" in res["resume"]
    assert res["source"] == "regles"


def test_texte_trop_court_ou_trop_long():
    with pytest.raises(TexteErreur):
        analyser("abc")
    with pytest.raises(TexteErreur):
        analyser("a" * 2000)


# --- IA (simulée) ---------------------------------------------------------------------


def fausse_ia(parsed, stop_reason="end_turn"):
    appels = []

    def parse(**kw):
        appels.append(kw)
        return SimpleNamespace(stop_reason=stop_reason, parsed_output=parsed)

    return SimpleNamespace(beta=SimpleNamespace(messages=SimpleNamespace(parse=parse))), appels


def extraction(**kw):
    base = dict(preoccupations=[], demangeaisons_details=[], type_cheveux=None, famille=None,
                type_secondaire=None, epaisseur=None, densite=None, porosite=None,
                cuir_chevelu=None, traitements=[], chaleur=None, objectif=None, periodes=[],
                age=None, specifiques=[], sante=[], metisse=False)
    return ExtractionIA(**{**base, **kw})


def test_extraction_ia():
    parsed = extraction(preoccupations=[{"id": "chute", "intensite": "enormement"}],
                        type_cheveux="4C", periodes=["post_partum"])
    fake, appels = fausse_ia(parsed)
    res = texte.extraire_ia("Je perds énormément de cheveux depuis mon accouchement.", fake)
    assert res["reponses"] == {"preoccupations": ["chute"], "type_cheveux": "4C",
                               "periodes": ["post_partum"]}
    assert res["intensites"] == {"chute": "enormement"}
    kw = appels[0]
    assert kw["output_format"] is ExtractionIA
    assert kw["fallbacks"] == "default"
    assert "<description>" in kw["messages"][0]["content"]


def test_refus_de_l_ia():
    fake, _ = fausse_ia(None, stop_reason="refusal")
    with pytest.raises(TexteErreur):
        texte.extraire_ia("texte", fake)


def test_repli_sur_les_regles_si_l_ia_echoue(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")

    def echec(t):
        raise TexteErreur("non")

    monkeypatch.setattr(texte, "extraire_ia", echec)
    res = analyser("Mes cheveux sont très secs.", ia=True)
    assert res["source"] == "regles" and res["note"]
    assert res["reponses"]["preoccupations"] == ["secheresse"]


def test_pas_d_ia_sans_cle(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    monkeypatch.setattr(texte, "extraire_ia", lambda t: pytest.fail("IA appelée"))
    assert analyser("Cheveux secs.", ia=True)["source"] == "regles"


# --- API et page ------------------------------------------------------------------------


def test_api_analyse_texte():
    r = client.post("/api/analyse-texte", json={"texte": "J'ai des pellicules et ça gratte."})
    assert r.status_code == 200
    assert set(r.json()["reponses"]["preoccupations"]) == {"pellicules", "demangeaisons"}
    assert client.post("/api/analyse-texte", json={"texte": ""}).status_code == 422
    assert client.post("/api/analyse-texte", json={}).status_code == 422


def test_zone_de_texte_dans_le_questionnaire():
    r = client.get("/diagnostic")
    assert 'id="description"' in r.text
    assert "pré-remplit pendant que vous écrivez" in r.text
    assert 'id="texte-analyse"' not in r.text  # pas de bouton : c'est automatique
    # Le texte n'est pas envoyé avec le formulaire (aucun attribut name).
    assert '<textarea id="description" name=' not in r.text
    assert 'textarea name="description"' not in r.text
