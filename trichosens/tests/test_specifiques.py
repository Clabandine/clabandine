import pytest
from fastapi.testclient import TestClient

from app.feedback import valeurs
from app.engine import cuir_effectif, run_diagnostic
from app.main import app
from app.partage import texte_partage
from app.questionnaire import validate
from app.specifiques import (
    CODES, DETAILS_DEMANGEAISONS, SPECIFICITES, TAILLES, ReponseInvalide, trouver_type,
)

client = TestClient(app)

BASE = {
    "type_cheveux": "3C", "epaisseur": "moyen", "densite": "forte", "porosite": "moyenne",
    "cuir_chevelu": "normal", "chaleur": "jamais", "objectif": "hydratation",
    "preoccupations": ["secheresse"], "intensites": {"secheresse": "beaucoup"},
}


def answers(**overrides):
    data = {**BASE, **overrides}
    if "preoccupations" in overrides and "intensites" not in overrides:
        data["intensites"] = {p: "beaucoup" for p in overrides["preoccupations"]}
    return validate(data)


def demangeaisons(*details, **overrides):
    return answers(preoccupations=["demangeaisons"], demangeaisons_details=list(details),
                   **overrides)


# --- Trouver son type ---------------------------------------------------------


def test_trouver_type_simple():
    r = trouver_type("3", "B", "beaucoup", "une")
    assert r == {"type": "3B", "secondaire": None, "explication": r["explication"]}


@pytest.mark.parametrize("forme,taille,retractation,textures,attendu", [
    ("3", "C", "enorme", "une", "4A"),          # se rétracte plus que la moyenne : vers le 4A
    ("2", "A", "aucune", "une", "1C"),          # se rétracte moins : vers le 1C
    ("3", "B", "beaucoup", "plus_serrees", "3C"),
    ("4", "A", "enorme", "plus_souples", "3C"),  # cheveux métissés : nuque 4A, dessus 3C
])
def test_trouver_type_entre_deux(forme, taille, retractation, textures, attendu):
    r = trouver_type(forme, taille, retractation, textures)
    assert r["secondaire"] == attendu
    assert "deux types" in r["explication"]


def test_trouver_type_aux_extremes_pas_de_second_type():
    assert trouver_type("1", "A", "aucune", "plus_souples")["secondaire"] is None
    assert trouver_type("4", "C", "enorme", "plus_serrees")["secondaire"] is None


def test_toutes_les_combinaisons_donnent_un_type_valide():
    for forme, tailles in TAILLES.items():
        for t in tailles:
            for r in ("", "aucune", "peu", "beaucoup", "enorme"):
                for x in ("une", "plus_serrees", "plus_souples"):
                    res = trouver_type(forme, t.value, r, x)
                    assert res["type"] in CODES
                    assert res["secondaire"] in CODES + [None]
                    assert res["secondaire"] != res["type"]


def test_trouver_type_refuse_les_reponses_inconnues():
    with pytest.raises(ReponseInvalide):
        trouver_type("5", "A")
    with pytest.raises(ReponseInvalide):
        trouver_type("3", "B", "inconnue")


def test_api_trouver_type():
    r = client.post("/api/trouver-type", json={"forme": "4", "taille": "A",
                                               "retractation": "enorme",
                                               "textures": "plus_souples"})
    assert r.status_code == 200
    assert r.json()["type"] == "4A" and r.json()["secondaire"] == "3C"
    assert client.post("/api/trouver-type", json={"forme": "3"}).status_code == 422


# --- Validation ---------------------------------------------------------------


def test_second_type_identique_ignore():
    assert answers(type_secondaire="3C").type_secondaire == ""
    assert answers(type_secondaire="4A").type_secondaire == "4A"


def test_situations_filtrees_selon_la_famille():
    a = answers(type_cheveux="1B", specifiques=["racines_grasses", "retractation"])
    assert a.specifiques == ["racines_grasses"]
    # Avec un second type d'une autre famille, ses situations sont gardées.
    a = answers(type_cheveux="2C", type_secondaire="3A",
                specifiques=["ondulations_disparaissent", "retractation", "secs_lendemain"])
    assert a.specifiques == ["ondulations_disparaissent", "retractation", "secs_lendemain"]


def test_chaque_famille_a_ses_situations():
    for famille in "1234":
        assert sum(famille in s.familles for s in SPECIFICITES.values()) >= 4


def test_details_demangeaisons_ignores_sans_demangeaisons():
    a = answers(demangeaisons_details=["rougeurs"])
    assert a.demangeaisons_details == []


# --- Démangeaisons -------------------------------------------------------------


def test_demangeaisons_dans_le_rapport():
    d = run_diagnostic(demangeaisons("pellicules_grasses"))
    rapport = d.douleurs[0]
    assert rapport.id == "demangeaisons"
    assert any("Malassezia" in c for c in rapport.causes)
    assert rapport.actions[0] == DETAILS_DEMANGEAISONS["pellicules_grasses"].conseil
    assert d.besoins["cuir_chevelu"] >= 60
    titres = [s.titre for s in d.routine]
    assert "Apaiser sans gratter" in titres and "Soin du cuir chevelu" in titres


def test_pellicules_grasses_shampoing_antipelliculaire():
    a = demangeaisons("pellicules_grasses")
    assert cuir_effectif(a) == "pellicules"
    shampoing = next(s for s in run_diagnostic(a).routine if s.categorie == "shampoing")
    assert "pellicules" in shampoing.produit.cuir_chevelu
    assert "temps de pose" in shampoing.conseil or "3 à 5 minutes" in shampoing.conseil


def test_rougeurs_soins_pour_cuir_sensible():
    a = demangeaisons("rougeurs", cuir_chevelu="sec")
    assert cuir_effectif(a) == "sensible"
    for s in run_diagnostic(a).routine:
        if s.categorie in {"shampoing", "soin_cuir"} and s.produit:
            assert "sensible" in s.produit.cuir_chevelu


def test_plaques_alerte_medicale_precise():
    d = run_diagnostic(demangeaisons("plaques"))
    assert any("dermatologue" in x and "Plaques" in x for x in d.alertes)
    assert len(d.alertes) == 1


def test_demangeaisons_sans_detail_alerte_generale():
    d = run_diagnostic(demangeaisons())
    assert any("démangeaisons" in x for x in d.alertes)


def test_allergie_coloration_alerte():
    d = run_diagnostic(demangeaisons("apres_produit"))
    assert any("urgence" in x for x in d.alertes)


def test_sous_les_tresses_etape_de_lavage():
    d = run_diagnostic(demangeaisons("sous_coiffure", type_cheveux="4C"))
    assert "Laver sous les tresses" in [s.titre for s in d.routine]


# --- Second type et situations propres au type -----------------------------------


def test_second_type_dans_le_resultat():
    d = run_diagnostic(answers(type_secondaire="4A"))
    assert d.type_code == "3C/4A"
    assert "part de 4A" in d.resume
    assert any(p["type"] == "4A" for p in d.problemes_type)
    assert any("mélangent les types 3C et 4A" in c for c in d.conseils)
    assert valeurs(d)["TS_TYPE"] == "3C/4A"
    assert "avec une part de 4A" in texte_partage(d, "https://exemple.fr/")
    assert d.suivi["type_secondaire"] == "4A"


def test_second_type_plus_serre_augmente_l_hydratation():
    seul = run_diagnostic(answers(type_cheveux="3A"))
    mixte = run_diagnostic(answers(type_cheveux="3A", type_secondaire="4C"))
    assert mixte.besoins["hydratation"] > seul.besoins["hydratation"]


def test_situations_propres_au_type():
    d = run_diagnostic(answers(type_cheveux="4B", specifiques=["tempes_clairsemees", "noeuds_fees"]))
    assert [s["id"] for s in d.specifiques] == ["tempes_clairsemees", "noeuds_fees"]
    assert "dermatologue" in d.specifiques[0]["conseil"]


def test_page_resultat_avec_les_nouveautes():
    form = {
        "type_cheveux": "3C", "type_secondaire": "4A", "specifiques": ["retractation"],
        "epaisseur": "moyen", "densite": "forte", "porosite": "forte", "cuir_chevelu": "normal",
        "preoccupations": ["demangeaisons"], "gene_demangeaisons": "beaucoup",
        "demangeaisons_details": ["pellicules_grasses"],
        "chaleur": "jamais", "objectif": "hydratation",
    }
    r = client.post("/diagnostic", data=form)
    assert r.status_code == 200
    assert "Spécifique à vos cheveux de type 3C/4A" in r.text
    assert "Démangeaisons" in r.text
    assert "Type 4A" in r.text


def test_page_questionnaire_propose_l_aide():
    r = client.get("/diagnostic")
    assert "Je ne suis pas sûre de mon type" in r.text
    assert "Votre cuir chevelu : qu&#39;observez-vous" in r.text or "Votre cuir chevelu : qu'observez-vous" in r.text
    assert "mélangent-ils deux types" in r.text


# --- Pellicules ---------------------------------------------------------------


def pellicules(**overrides):
    return answers(preoccupations=["pellicules"], **overrides)


def test_pellicules_proposees_des_la_premiere_page():
    r = client.get("/diagnostic")
    assert 'value="pellicules"' in r.text
    assert 'data-show-if="demangeaisons pellicules"' in r.text


def test_pellicules_rapport_et_shampoing_antipelliculaire():
    d = run_diagnostic(pellicules())
    assert d.douleurs[0].id == "pellicules"
    assert any("Malassezia" in c for c in d.douleurs[0].causes)
    shampoing = next(s for s in d.routine if s.categorie == "shampoing")
    assert "pellicules" in shampoing.produit.cuir_chevelu
    assert "3 à 5 minutes" in shampoing.conseil
    assert "Soin du cuir chevelu" in [s.titre for s in d.routine]
    assert any("dermatologue" in x for x in d.alertes)


def test_pellicules_cuir_sec_shampoing_pour_cuir_sec():
    shampoing = next(s for s in run_diagnostic(pellicules(cuir_chevelu="sec")).routine
                     if s.categorie == "shampoing")
    assert {"pellicules", "sec"} <= set(shampoing.produit.cuir_chevelu)


def test_pellicules_cuir_sensible_shampoing_doux_et_antipelliculaire():
    shampoing = next(s for s in run_diagnostic(pellicules(cuir_chevelu="sensible")).routine
                     if s.categorie == "shampoing")
    assert {"pellicules", "sensible"} <= set(shampoing.produit.cuir_chevelu)


def test_precisions_cuir_chevelu_gardees_avec_les_pellicules():
    a = pellicules(demangeaisons_details=["pellicules_grasses"])
    assert a.demangeaisons_details == ["pellicules_grasses"]
    d = run_diagnostic(a)
    assert d.douleurs[0].actions[0] == DETAILS_DEMANGEAISONS["pellicules_grasses"].conseil


def test_precisions_affichees_une_seule_fois_avec_pellicules_et_demangeaisons():
    a = answers(preoccupations=["pellicules", "demangeaisons"],
                demangeaisons_details=["pellicules_grasses"])
    d = run_diagnostic(a)
    conseil = DETAILS_DEMANGEAISONS["pellicules_grasses"].conseil
    assert sum(conseil in r.actions for r in d.douleurs) == 1


def test_photo_peut_signaler_des_pellicules():
    from app.photo import AnalysePhoto
    photo = AnalysePhoto.model_validate({
        "exploitable": True, "conseil_photo": None, "type_cheveux": "3C",
        "confiance_type": "moyenne", "epaisseur": "moyen", "densite": "forte",
        "signes": [{"signe": "pellicules", "intensite": "modere",
                    "explication": "Petites peaux blanches visibles à la racine."}],
        "observations": ["Cuir chevelu visible à la raie."], "alerte_medicale": None,
    })
    d = run_diagnostic(answers(), photo=photo)
    assert any(s["id"] == "pellicules" for s in d.signes_photo_en_plus)
