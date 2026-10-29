import itertools

import pytest

from app.catalog import CATEGORIES, load_catalog
from app.engine import run_diagnostic
from app.questionnaire import QUESTIONS_BY_ID, InvalidAnswers, validate

BASE = {
    "texture": "boucle",
    "epaisseur": "moyen",
    "densite": "moyenne",
    "porosite": "moyenne",
    "cuir_chevelu": "normal",
    "preoccupations": ["secheresse"],
    "traitements": [],
    "chaleur": "jamais",
    "objectif": "hydratation",
}


def diag(**overrides):
    return run_diagnostic(validate({**BASE, **overrides}))


def titles(d):
    return [s.titre for s in d.routine]


def test_catalog_is_valid():
    catalog = load_catalog()
    ids = [p.id for p in catalog]
    assert len(ids) == len(set(ids)), "identifiants en double"
    assert {p.categorie for p in catalog} == set(CATEGORIES)


def test_missing_answer_is_rejected():
    with pytest.raises(InvalidAnswers) as e:
        validate({**BASE, "texture": None})
    assert "texture" in e.value.errors


def test_unknown_answer_is_rejected():
    with pytest.raises(InvalidAnswers) as e:
        validate({**BASE, "porosite": "enorme"})
    assert "porosite" in e.value.errors


def test_too_many_concerns_is_rejected():
    with pytest.raises(InvalidAnswers) as e:
        validate({**BASE, "preoccupations": ["secheresse", "casse", "chute", "volume"]})
    assert "preoccupations" in e.value.errors


def test_curly_hair_needs_more_hydration_than_straight():
    assert diag(texture="crepu").besoins["hydratation"] > diag(texture="lisse").besoins["hydratation"]


def test_bleached_hair_needs_repair_and_proteins():
    d = diag(traitements=["decoloration"], preoccupations=["casse"])
    assert "reparation" in d.priorites
    assert "proteines" in d.priorites


def test_heat_protection_only_when_using_heat():
    assert "Protection thermique" not in titles(diag(chaleur="jamais"))
    assert "Protection thermique" in titles(diag(chaleur="souvent"))


def test_hair_loss_triggers_medical_alert():
    assert diag(preoccupations=["chute"]).alertes
    assert not diag().alertes


def test_sensitive_scalp_gets_fragrance_free_shampoo():
    d = diag(cuir_chevelu="sensible")
    shampoo = next(s.produit for s in d.routine if s.categorie == "shampoing")
    assert shampoo.sans_parfum


def test_fine_straight_hair_gets_light_products():
    d = diag(texture="lisse", epaisseur="fin", densite="faible", porosite="faible",
             preoccupations=["volume"], objectif="volume")
    assert d.poids_produits == "leger"
    assert all(s.produit.poids != "riche" for s in d.routine if s.produit)


def test_coily_hair_gets_rich_products_and_night_care():
    d = diag(texture="crepu", epaisseur="epais", porosite="forte")
    assert d.poids_produits == "riche"
    assert "Protéger les cheveux" in titles(d)


def test_every_profile_gets_a_product_for_each_step():
    """Toutes les combinaisons de réponses simples doivent produire une routine complète."""
    ids = ["texture", "epaisseur", "densite", "porosite", "cuir_chevelu", "chaleur", "objectif"]
    choices = [[o.value for o in QUESTIONS_BY_ID[i].options] for i in ids]
    for combo in itertools.product(*choices):
        d = diag(**dict(zip(ids, combo)))
        missing = [s.titre for s in d.routine if s.categorie and s.produit is None]
        assert not missing, f"{combo} : aucun produit pour {missing}"
