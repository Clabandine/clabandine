import itertools

import pytest

from app.catalog import CATEGORIES, load_catalog
from app.engine import run_diagnostic
from app.hair_types import HAIR_TYPES, TYPE_POINTS
from app.pain_points import PAIN_POINTS
from app.photo import AnalysePhoto
from app.questionnaire import QUESTIONS_BY_ID, InvalidAnswers, validate

BASE = {
    "type_cheveux": "3B",
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
        validate({**BASE, "type_cheveux": None})
    assert "type_cheveux" in e.value.errors


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
    assert diag(type_cheveux="4C").besoins["hydratation"] > diag(type_cheveux="1B").besoins["hydratation"]


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
    d = diag(type_cheveux="1A", epaisseur="fin", densite="faible", porosite="faible",
             preoccupations=["volume"], objectif="volume")
    assert d.poids_produits == "leger"
    assert all(s.produit.poids != "riche" for s in d.routine if s.produit)


def test_coily_hair_gets_rich_products_and_night_care():
    d = diag(type_cheveux="4C", epaisseur="epais", porosite="forte")
    assert d.poids_produits == "riche"
    assert "Protéger les cheveux" in titles(d)


def test_every_profile_gets_a_product_for_each_step():
    """Toutes les combinaisons de réponses simples doivent produire une routine complète."""
    ids = ["type_cheveux", "epaisseur", "densite", "porosite", "cuir_chevelu", "chaleur", "objectif"]
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
        "exploitable": True, "conseil_photo": None, "type_cheveux": "3B",
        "confiance_type": "elevee", "epaisseur": "moyen", "densite": "moyenne",
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


def test_photo_type_disagreement_is_explained():
    d = diag(photo=photo(type_cheveux="4C"))
    assert any("type 4C" in n and "refaites le diagnostic" in n for n in d.notes_photo)
    assert not diag(photo=photo(type_cheveux="4C", confiance_type="faible")).notes_photo
    close = diag(photo=photo(type_cheveux="3A"))  # même famille : simple remarque
    assert any("restent adaptés" in n for n in close.notes_photo)


def test_unusable_photo_changes_nothing():
    p = photo(exploitable=False, conseil_photo="Prenez la photo à la lumière du jour.",
              signes=[{"signe": "casse", "intensite": "marque", "explication": "x"}])
    d = diag(photo=p)
    assert d.besoins == diag().besoins
    assert "lumière du jour" in d.notes_photo[0]


def test_photo_medical_alert_is_shown():
    d = diag(photo=photo(alerte_medicale="Une zone sans cheveux mérite un avis médical."))
    assert "Une zone sans cheveux mérite un avis médical." in d.alertes


def test_hair_types_are_complete():
    assert len(HAIR_TYPES) == 12
    assert set(TYPE_POINTS) == set(HAIR_TYPES)
    for t in HAIR_TYPES.values():
        assert t.problemes, t.code
        assert all(pid in PAIN_POINTS for pid, _ in t.problemes), t.code


def test_type_drives_texture_and_frequent_problems():
    d = diag(type_cheveux="4C", preoccupations=["casse"])
    assert d.texture == "crepu"
    problems = {p["id"]: p for p in d.problemes_type}
    assert problems["casse"]["signale"] and not problems["pousse"]["signale"]
    casse = d.douleurs[0]
    assert any(c.startswith("Fréquent chez le type 4C") for c in casse.causes)


def test_type_problem_seen_on_photo_is_flagged():
    sign = {"signe": "frisottis", "intensite": "modere", "explication": "Halo de frisottis."}
    d = diag(photo=photo(signes=[sign]))
    problems = {p["id"]: p for p in d.problemes_type}
    assert problems["frisottis"]["vu_photo"] and not problems["demelage"]["vu_photo"]


def test_fine_type_1a_gets_lighter_products_than_1c():
    order = ["leger", "moyen", "riche"]
    light = diag(type_cheveux="1A", epaisseur="moyen", porosite="moyenne").poids_produits
    heavy = diag(type_cheveux="1C", epaisseur="moyen", porosite="moyenne").poids_produits
    assert order.index(light) < order.index(heavy)
