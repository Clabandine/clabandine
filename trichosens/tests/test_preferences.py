from app.engine import BUDGET_MAX, run_diagnostic
from app.questionnaire import validate

BASE = {
    "type_cheveux": "3B", "epaisseur": "moyen", "densite": "moyenne", "porosite": "forte",
    "cuir_chevelu": "normal", "chaleur": "parfois", "objectif": "definition",
    "preoccupations": ["secheresse"], "intensites": {"secheresse": "beaucoup"},
}


def diag(**overrides):
    return run_diagnostic(validate({**BASE, **overrides}))


def produits(d):
    return [s for s in d.routine if s.produit]


def test_preferences_are_optional():
    a = validate(BASE)
    assert a.preferences == [] and a.budget == "indifferent"
    assert all(not s.hors_preferences for s in produits(diag()))


def test_small_budget_picks_cheaper_products():
    d = diag(budget="petit")
    for s in produits(d):
        assert s.produit.prix is None or s.produit.prix <= BUDGET_MAX["petit"] or "budget" in s.hors_preferences
    assert d.cout_total < diag().cout_total


def test_vegan_preference_is_respected_or_flagged():
    d = diag(preferences=["vegan"])
    for s in produits(d):
        assert s.produit.vegan is True or "vegan" in s.hors_preferences
    assert any(s.produit.vegan for s in produits(d))


def test_unknown_preference_is_rejected():
    import pytest
    from app.questionnaire import InvalidAnswers
    with pytest.raises(InvalidAnswers):
        validate({**BASE, "preferences": ["bio"]})


def test_preferences_are_kept_in_history():
    d = diag(preferences=["sans_sulfates"], budget="moyen")
    assert d.suivi["preferences"] == ["sans_sulfates"] and d.suivi["budget"] == "moyen"
