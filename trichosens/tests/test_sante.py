from fastapi.testclient import TestClient

from app.engine import run_diagnostic
from app.feedback import valeurs
from app.main import app
from app.questionnaire import validate
from app.sante import FACTEURS
from app.texte import extraire_regles

client = TestClient(app)

BASE = {
    "type_cheveux": "3C", "epaisseur": "moyen", "densite": "forte", "porosite": "moyenne",
    "elasticite": "equilibre", "cuir_chevelu": "normal", "chaleur": "jamais",
    "objectif": "hydratation", "preoccupations": ["chute"], "intensites": {"chute": "beaucoup"},
}


def diag(**kw):
    return run_diagnostic(validate({**BASE, **kw}))


def produits(d):
    return [p.id for c in d.cures for p in c["produits"]]


def test_question_sante_facultative_et_aucun_seul():
    assert validate(BASE).sante == []
    assert validate({**BASE, "sante": ["aucun", "thyroide"]}).sante == ["thyroide"]


def test_facteurs_de_sante_bien_decrits():
    for f in FACTEURS.values():
        if f.id != "aucun":
            assert f.explication and f.groupe in {"connu", "signe"}


def test_manque_de_fer_orientation_et_cure_sur_avis():
    d = diag(sante=["carence_fer"])
    noms = [s["nom"] for s in d.orientation["specialistes"]]
    assert noms == ["Médecin généraliste"]
    assert "ferritine" in d.orientation["bilan"]
    assert produits(d)[0] == "divers-fer-bisglycinate"
    assert "prise de sang" in d.cures_message


def test_sopk_gyneco_et_dermato():
    d = diag(sante=["sopk"])
    assert [s["nom"] for s in d.orientation["specialistes"]] == ["Dermatologue", "Gynécologue"]


def test_thyroide_previent_pour_la_biotine():
    d = diag(sante=["thyroide"])
    assert d.orientation["specialistes"][0]["nom"] == "Endocrinologue"
    assert "biotine" in d.cures_message


def test_pas_de_cure_pendant_une_chimiotherapie():
    d = diag(sante=["chimio"])
    assert d.cures == [] and "équipe médicale" in d.cures_message


def test_fatigue_sans_carence_confirmee_pas_de_fer():
    d = diag(sante=["fatigue"])
    assert "divers-fer-bisglycinate" not in produits(d)
    assert "ferritine" in d.cures_message
    assert "TSH" in d.orientation["bilan"]


def test_carence_sans_gene_declenche_une_cure():
    d = diag(preoccupations=["frisottis"], intensites={"frisottis": "un_peu"},
             sante=["carence_vitd"])
    assert "divers-vitamine-d3" in produits(d)


def test_chute_enorme_conseille_un_medecin_meme_sans_reponse_sante():
    d = diag(intensites={"chute": "enormement"})
    assert d.orientation["specialistes"][0]["nom"] == "Médecin généraliste"
    assert diag().orientation["specialistes"] == []


def test_donnees_de_sante_jamais_dans_les_avis_ni_le_suivi():
    d = diag(sante=["sopk", "carence_fer"])
    texte = " ".join(valeurs(d).values()).lower()
    assert "sopk" not in texte and "fer" not in texte.replace("fiabilité", "")
    assert "sante" not in d.suivi


def test_texte_libre_repere_la_sante():
    r = extraire_regles("J'ai une anémie et un SOPK, et je perds mes cheveux par poignées.")
    assert set(r["reponses"]["sante"]) == {"carence_fer", "sopk", "chute_brutale"}


def test_resultat_onglet_complements_et_orientation():
    form = {**{k: v for k, v in BASE.items() if k not in {"preoccupations", "intensites"}},
            "preoccupations": ["chute"], "gene_chute": "beaucoup",
            "sante": ["carence_fer", "regles_abondantes"]}
    r = client.post("/diagnostic", data=form)
    assert r.status_code == 200
    assert "Parlez-en à un professionnel de santé" in r.text
    assert "💊 Compléments" in r.text
    assert "Fer, sur avis médical" in r.text
    assert "Gynécologue" in r.text


def test_question_sante_dans_le_questionnaire():
    r = client.get("/diagnostic")
    assert "Votre santé" in r.text and "Ce que vous remarquez" in r.text
