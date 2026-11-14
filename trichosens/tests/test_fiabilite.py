from fastapi.testclient import TestClient

from app.engine import fiabilite, run_diagnostic
from app.feedback import valeurs
from app.main import app
from app.photo import AnalysePhoto
from app.questionnaire import QUESTIONS_BY_ID, validate

client = TestClient(app)

BASE = {
    "type_cheveux": "3B", "epaisseur": "moyen", "densite": "moyenne", "porosite": "moyenne",
    "elasticite": "equilibre", "cuir_chevelu": "normal", "chaleur": "jamais",
    "objectif": "hydratation", "preoccupations": ["secheresse"],
    "intensites": {"secheresse": "beaucoup"},
}


def answers(**kw):
    return validate({**BASE, **kw})


# --- Petits tests à faire chez soi ---------------------------------------------------


def test_chaque_test_donne_des_reponses_valides():
    for qid in ("epaisseur", "densite", "porosite", "elasticite"):
        q = QUESTIONS_BY_ID[qid]
        assert q.test, qid
        assert {v for _, v in q.test.resultats} <= q.values()


def test_elasticite_facultative_par_defaut_non_testee():
    data = {k: v for k, v in BASE.items() if k != "elasticite"}
    assert validate(data).elasticite == "non_teste"


def test_elasticite_oriente_les_besoins_et_les_conseils():
    proteines = run_diagnostic(answers(elasticite="manque_proteines"))
    hydratation = run_diagnostic(answers(elasticite="manque_hydratation"))
    assert proteines.besoins["proteines"] > hydratation.besoins["proteines"]
    assert hydratation.besoins["hydratation"] >= proteines.besoins["hydratation"]
    assert any("manque de protéines" in c for c in proteines.conseils)
    assert any("manque d'hydratation" in c for c in hydratation.conseils)


def test_tests_affiches_dans_le_questionnaire():
    r = client.get("/diagnostic")
    for titre in ("Le test du fil", "Le test de la queue de cheval", "Le test du verre d&#39;eau",
                  "Le test d&#39;élasticité"):
        assert titre in r.text or titre.replace("&#39;", "'") in r.text
    assert 'data-test-q="porosite" data-test-v="forte"' in r.text


# --- Fiabilité ----------------------------------------------------------------------------


def test_reponses_completes_fiabilite_elevee():
    f = fiabilite(answers(), photo_dispo=False)
    assert f["score"] == 100 and f["niveau"] == "elevee"
    assert f["a_ameliorer"] == [] and f["a_verifier"] == []


def test_tests_non_faits_baissent_la_fiabilite():
    f = fiabilite(answers(porosite="inconnue", elasticite="non_teste"), photo_dispo=False)
    assert f["score"] == 75 and f["niveau"] == "bonne"
    assert any("verre d'eau" in x for x in f["a_ameliorer"])
    assert any("élasticité" in x for x in f["a_ameliorer"])


def test_photo_conseillee_seulement_si_disponible():
    assert not any("photo" in x for x in fiabilite(answers(), photo_dispo=False)["a_ameliorer"])
    assert any("photo" in x for x in fiabilite(answers(), photo_dispo=True)["a_ameliorer"])


def test_incoherence_raides_et_boucles():
    f = fiabilite(answers(type_cheveux="1B", preoccupations=["definition"],
                          intensites={"definition": "beaucoup"}), photo_dispo=False)
    assert f["score"] == 90
    assert any("type 2" in x for x in f["a_verifier"])


def test_incoherence_porosite_forte_sur_cheveux_raides_naturels():
    f = fiabilite(answers(type_cheveux="1A", porosite="forte"), photo_dispo=False)
    assert any("porosité forte est rare" in x for x in f["a_verifier"])
    f = fiabilite(answers(type_cheveux="1A", porosite="forte", traitements=["decoloration"]),
                  photo_dispo=False)
    assert f["a_verifier"] == []


def photo(code, confiance="elevee"):
    return AnalysePhoto(exploitable=True, conseil_photo=None, type_cheveux=code,
                        confiance_type=confiance, epaisseur="moyen", densite="moyenne",
                        signes=[], observations=["Cheveux visibles."], alerte_medicale=None)


def test_photo_d_une_autre_famille():
    f = fiabilite(answers(), photo("1B"), photo_dispo=True)
    assert any("type 1B" in x for x in f["a_verifier"])
    assert f["score"] == 85
    # Même famille, ou second type de la famille vue : rien à vérifier.
    assert fiabilite(answers(), photo("3C"), photo_dispo=True)["a_verifier"] == []
    assert fiabilite(answers(type_secondaire="4A"), photo("4B"), photo_dispo=True)["a_verifier"] == []
    # Confiance faible : on ne conclut rien.
    assert fiabilite(answers(), photo("1B", "faible"), photo_dispo=True)["a_verifier"] == []


def test_niveau_a_preciser():
    f = fiabilite(answers(type_cheveux="1A", porosite="inconnue", elasticite="non_teste",
                          preoccupations=["definition"], intensites={"definition": "un_peu"}),
                  photo_dispo=True)
    assert f["niveau"] == "a_preciser"


def test_fiabilite_dans_le_resultat_et_les_avis():
    d = run_diagnostic(answers(porosite="inconnue"))
    assert d.fiabilite["score"] < 100
    assert "Fiabilité" in valeurs(d)["TS_RESUME"]
    form = {**{k: v for k, v in BASE.items() if k not in {"preoccupations", "intensites"}},
            "preoccupations": ["secheresse"], "gene_secheresse": "beaucoup",
            "porosite": "inconnue"}
    r = client.post("/diagnostic", data=form)
    assert "Fiabilité de votre diagnostic" in r.text
    assert "test du verre d&#39;eau" in r.text or "test du verre d'eau" in r.text
