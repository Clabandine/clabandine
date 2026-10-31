import datetime as dt

from app.engine import run_diagnostic
from app.evolution import ResumeSuivi
from app.questionnaire import validate

TODAY = dt.date(2026, 11, 2)
BASE = {
    "type_cheveux": "3B", "epaisseur": "moyen", "densite": "moyenne", "porosite": "moyenne",
    "cuir_chevelu": "normal", "chaleur": "jamais", "objectif": "hydratation",
    "preoccupations": ["secheresse", "frisottis"],
    "intensites": {"secheresse": "beaucoup", "frisottis": "beaucoup"},
}


def diag(today=TODAY, precedent=None, **overrides):
    return run_diagnostic(validate({**BASE, **overrides}), today=today, precedent=precedent)


def previous(days_ago, **overrides):
    first = diag(today=TODAY - dt.timedelta(days=days_ago), **overrides)
    return ResumeSuivi.model_validate(first.suivi)


def test_first_diagnostic_starts_intensive_programme():
    d = diag()
    assert d.evolution is None and d.phase == "intensive"
    assert d.prochain_point == TODAY + dt.timedelta(weeks=4)
    assert [p["titre"] for p in d.programme] == ["Phase intensive", "Entretien"]


def test_too_early_to_judge():
    d = diag(precedent=previous(5))
    assert "encore tôt" in d.evolution.messages[-1]
    assert d.phase == "intensive"


def test_improvement_switches_to_maintenance():
    d = diag(precedent=previous(35), preoccupations=["frisottis"], intensites={"frisottis": "un_peu"})
    tendances = {c.id: c.tendance for c in d.evolution.changements}
    assert tendances == {"frisottis": "mieux", "secheresse": "resolu"}
    assert d.phase == "entretien"
    masque = next(s for s in d.routine if s.categorie == "masque")
    assert masque.conseil.startswith("Un lavage sur deux")


def test_worsening_adjusts_with_specific_advice():
    d = diag(precedent=previous(30), preoccupations=["secheresse", "casse"],
             intensites={"secheresse": "enormement", "casse": "beaucoup"})
    assert d.phase == "ajustement"
    assert any("masque plus riche" in m for m in d.evolution.messages)
    assert any("casse augmente" in m for m in d.evolution.messages)


def test_type_change_is_explained():
    d = diag(precedent=previous(40), type_cheveux="4A")
    assert any("contre 3B" in m for m in d.evolution.messages)


def test_season_changes_advice_and_needs():
    hiver = diag(today=dt.date(2027, 1, 10))
    ete = diag(today=dt.date(2027, 7, 10))
    assert hiver.saison.id == "hiver" and ete.saison.id == "ete"
    assert hiver.besoins["nutrition"] > ete.besoins["nutrition"]
    assert ete.besoins["protection"] > hiver.besoins["protection"]
    assert any("soleil" in c for c in ete.conseils_saison)


def test_no_hair_loss_product_without_hair_loss():
    d = diag(cuir_chevelu="gras", objectif="sante_cuir")
    soins = [s.produit for s in d.routine if s.categorie == "soin_cuir"]
    assert soins and all("anti_chute" not in p.besoins for p in soins)
