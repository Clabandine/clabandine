from fastapi.testclient import TestClient

from app.catalog import load_catalog
from app.engine import run_diagnostic
from app.main import app
from app.naturel import RECETTES
from app.questionnaire import validate

client = TestClient(app)

BASE = {
    "type_cheveux": "4B", "epaisseur": "moyen", "densite": "forte", "porosite": "forte",
    "cuir_chevelu": "normal", "chaleur": "jamais", "objectif": "hydratation",
    "preoccupations": ["secheresse"], "intensites": {"secheresse": "beaucoup"},
}


def diag(**overrides):
    data = {**BASE, **overrides}
    if "preoccupations" in overrides and "intensites" not in overrides:
        data["intensites"] = {p: "beaucoup" for p in overrides["preoccupations"]}
    return run_diagnostic(validate(data))


def ids(d):
    return [r["recette"].id for r in d.recettes]


def test_ingredients_a_acheter_existent_avec_un_lien():
    catalogue = {p.id: p for p in load_catalog()}
    for r in RECETTES.values():
        for _, pid in r.ingredients:
            if pid:
                assert pid in catalogue, pid
                assert catalogue[pid].offres, pid


def test_recettes_proposees_et_reliees_a_la_routine():
    d = diag()
    assert 1 <= len(d.recettes) <= 4
    categories = [r["recette"].categorie for r in d.recettes]
    assert len(categories) == len(set(categories))  # une recette par étape au plus
    alternatives = [s for s in d.routine if s.alternative]
    assert alternatives
    for s in alternatives:
        assert s.alternative.categorie == s.categorie


def test_gel_de_lin_seulement_pour_cheveux_ondules_a_crepus():
    assert "gel_lin" not in ids(diag(type_cheveux="1A", preoccupations=["definition"]))
    assert "gel_lin" in ids(diag(type_cheveux="3A", preoccupations=["definition"]))


def test_demangeaisons_soin_aloe_et_pas_de_vinaigre_sur_cuir_irrite():
    d = diag(preoccupations=["demangeaisons"], demangeaisons_details=["rougeurs"])
    assert "aloe_cuir" in ids(d)
    assert "rincage_cidre" not in ids(d)


def test_romarin_evite_pendant_la_grossesse():
    d = diag(preoccupations=["chute"], periodes=["grossesse"])
    assert "lotion_romarin" not in ids(d)
    assert "lotion_romarin" in ids(diag(preoccupations=["chute"]))


def test_pas_d_eau_de_riz_sur_porosite_faible():
    assert "eau_riz" not in ids(diag(porosite="faible", preoccupations=["casse"]))


def test_cure_si_chute_avec_bilan_sanguin():
    d = diag(preoccupations=["chute"])
    produits = [p.id for c in d.cures for p in c["produits"]]
    assert "arkopharma-forcapil" in produits and "divers-levure-biere" in produits
    assert "bilan sanguin" in d.cures_message
    assert "pharmacien" in d.cures_message


def test_pas_de_cure_pendant_la_grossesse():
    d = diag(preoccupations=["chute"], periodes=["grossesse"])
    assert d.cures == []
    assert "sage-femme" in d.cures_message


def test_pas_de_cure_avant_18_ans():
    d = diag(preoccupations=["casse"], age="moins_18")
    assert d.cures == [] and "18 ans" in d.cures_message


def test_pas_de_cure_sans_raison():
    d = diag(preoccupations=["frisottis"])
    assert d.cures == [] and d.cures_message == ""


def test_cure_post_partum_previent_pour_l_allaitement():
    d = diag(preoccupations=["frisottis"], periodes=["post_partum"])
    assert d.cures and "allaitez" in d.cures_message


def test_conseils_naturels_toujours_presents():
    assert len(diag().conseils_naturels) >= 2


def test_api_renvoie_les_alternatives():
    r = client.post("/api/diagnostic", json={**BASE, "preoccupations": ["chute"],
                                             "intensites": {"chute": "beaucoup"}})
    body = r.json()
    assert body["recettes"] and body["cures"]
    assert body["recettes"][0]["ingredients"]


def test_onglet_naturel_dans_le_resultat():
    form = {"type_cheveux": "3C", "epaisseur": "moyen", "densite": "forte",
            "porosite": "forte", "cuir_chevelu": "normal", "preoccupations": ["chute"],
            "gene_chute": "beaucoup", "chaleur": "jamais", "objectif": "hydratation"}
    r = client.post("/diagnostic", data=form)
    assert r.status_code == 200
    assert "Les alternatives naturelles" in r.text
    assert "Version maison" in r.text
    assert "Cure fortifiante cheveux" in r.text
    assert "/acheter/" in r.text
