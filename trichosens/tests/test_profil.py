import datetime as dt

from app.engine import run_diagnostic
from app.questionnaire import validate
from app.reminders import build_ics

BASE = {
    "type_cheveux": "3B", "epaisseur": "moyen", "densite": "moyenne", "porosite": "moyenne",
    "cuir_chevelu": "normal", "chaleur": "jamais", "objectif": "hydratation",
    "preoccupations": ["secheresse"], "intensites": {"secheresse": "beaucoup"},
}
HIVER, ETE = dt.date(2027, 1, 10), dt.date(2027, 7, 10)


def diag(today=HIVER, **kw):
    return run_diagnostic(validate({**BASE, **kw}), today=today)


def test_life_questions_are_optional():
    a = validate(BASE)
    assert a.age == "nc" and a.periodes == [] and a.saisons_sensibles == []


def test_none_option_is_dropped_when_combined():
    a = validate({**BASE, "periodes": ["aucune", "stress"], "saisons_sensibles": ["aucune"]})
    assert a.periodes == ["stress"] and a.saisons_sensibles == ["aucune"]


def test_winter_dryness_only_counts_in_winter():
    base_h, sens_h = diag(), diag(saisons_sensibles=["sec_hiver"])
    assert sens_h.besoins["nutrition"] > base_h.besoins["nutrition"]
    assert any("plus secs" in c for c in sens_h.conseils_saison)
    assert diag(ETE, saisons_sensibles=["sec_hiver"]).besoins == diag(ETE).besoins


def test_oily_in_summer_lightens_products():
    order = ["leger", "moyen", "riche"]
    d = diag(ETE, saisons_sensibles=["gras_ete"])
    assert order.index(d.poids_produits) <= order.index(diag(ETE).poids_produits)
    assert d.besoins["cuir_chevelu"] > diag(ETE).besoins["cuir_chevelu"]


def test_next_season_is_anticipated():
    d = diag(dt.date(2026, 11, 6), saisons_sensibles=["sec_hiver"])
    assert d.saison.id == "automne" and d.prochaine_saison.id == "hiver"
    assert any("masque plus nourrissant" in c for c in d.anticipation)


def test_age_and_life_stage_advice():
    d = diag(age="60_plus", periodes=["post_partum"])
    assert any("cheveux blancs" in c for c in d.conseils_vie)
    assert any("accouchement" in c for c in d.conseils_vie)
    assert d.besoins["nutrition"] > diag().besoins["nutrition"]


def test_no_hair_loss_product_during_pregnancy():
    d = diag(preoccupations=["chute"], intensites={"chute": "beaucoup"}, periodes=["grossesse"])
    soins = [s.produit for s in d.routine if s.categorie == "soin_cuir" and s.produit]
    assert all("anti_chute" not in p.besoins for p in soins)
    assert any("pharmacien" in c for c in d.conseils_vie)


def test_season_reminders():
    text = build_ics(jours=["SU"], heure=dt.time(19), rappels=["saison"], masque="chaque",
                     prochain_point=None, type_cheveux="3B", site_url="https://x.example",
                     today=dt.date(2026, 11, 6))
    assert text.count("BEGIN:VEVENT") == 4 and text.count("RRULE:FREQ=YEARLY") == 4
    assert "C'est l'hiver" in text and "DTSTART:20261221T190000" in text
