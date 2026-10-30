import itertools

import pytest

from app.catalog import CATEGORIES, load_catalog
from app.engine import run_diagnostic
from app.pain_points import PAIN_POINTS
from app.photo import AnalysePhoto
from app.questionnaire import QUESTIONS_BY_ID, InvalidAnswers, validate

BASE = {
    "texture": "boucle",
    "epaisseur": "moyen",
    "densite": "moyenne",
    "porosite": "moyenne",
    "cuir_chevelu": "normal",
    "preoccupations": ["secheresse"],
    "intensites": {"secheresse": "beaucoup"},
    "traitements": [],
    "chaleur": "jamais",
    "objectif": "hydratation",
}


def diag(photo=None, **overrides):
    data = {**BASE, **overrides}
    if "preoccupations" in overrides and "intensites" not in overrides:
        data["intensites"] = {p: "beaucoup" for p in overrides["preoccupations"]}
    return run_diagnostic(validate(data), photo=photo)


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
        validate({**BASE, "preoccupations": ["secheresse", "casse", "chute", "volume"],
                  "intensites": dict.fromkeys(["secheresse", "casse", "chute", "volume"], "un_peu")})
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


def test_missing_intensity_is_rejected():
    with pytest.raises(InvalidAnswers) as e:
        validate({**BASE, "preoccupations": ["casse"], "intensites": {}})
    assert "gene_casse" in e.value.errors


def test_stronger_pain_means_stronger_need():
    weak = diag(preoccupations=["casse"], intensites={"casse": "un_peu"})
    strong = diag(preoccupations=["casse"], intensites={"casse": "enormement"})
    assert strong.besoins["proteines"] > weak.besoins["proteines"]


def test_pain_reports_are_personalised_and_sorted():
    d = diag(preoccupations=["frisottis", "casse"],
             intensites={"frisottis": "un_peu", "casse": "enormement"},
             traitements=["decoloration"])
    assert [p.id for p in d.douleurs] == ["casse", "frisottis"]
    casse = d.douleurs[0]
    assert any("décoloration" in c for c in casse.causes)
    assert casse.actions and casse.a_eviter and casse.delai


def test_every_pain_point_has_engine_points():
    from app.engine import PREOCCUPATION_POINTS
    assert set(PAIN_POINTS) == set(PREOCCUPATION_POINTS)


def photo(**overrides):
    data = {
        "exploitable": True, "conseil_photo": None, "texture": "boucle",
        "confiance_texture": "elevee", "epaisseur": "moyen", "densite": "moyenne",
        "signes": [], "observations": ["Les longueurs paraissent sèches."], "alerte_medicale": None,
    }
    return AnalysePhoto.model_validate({**data, **overrides})


def test_photo_confirms_pain_point():
    d = diag(photo=photo(signes=[{"signe": "secheresse", "intensite": "marque",
                                  "explication": "Pointes ternes et rêches."}]))
    assert d.douleurs[0].vu_sur_photo
    assert d.douleurs[0].note_photo == "Pointes ternes et rêches."


def test_photo_adds_unchosen_signs_and_raises_needs():
    sign = {"signe": "casse", "intensite": "modere", "explication": "Cheveux cassés visibles."}
    d = diag(photo=photo(signes=[sign]))
    assert [s["id"] for s in d.signes_photo_en_plus] == ["casse"]
    assert d.besoins["proteines"] > diag().besoins["proteines"]


def test_photo_texture_disagreement_is_explained():
    d = diag(photo=photo(texture="crepu"))
    assert any("crépus" in n for n in d.notes_photo)
    assert not diag(photo=photo(texture="crepu", confiance_texture="faible")).notes_photo


def test_unusable_photo_changes_nothing():
    p = photo(exploitable=False, conseil_photo="Prenez la photo à la lumière du jour.",
              signes=[{"signe": "casse", "intensite": "marque", "explication": "x"}])
    d = diag(photo=p)
    assert d.besoins == diag().besoins
    assert "lumière du jour" in d.notes_photo[0]


def test_photo_medical_alert_is_shown():
    d = diag(photo=photo(alerte_medicale="Une zone sans cheveux mérite un avis médical."))
    assert "Une zone sans cheveux mérite un avis médical." in d.alertes
