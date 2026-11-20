import pytest
from fastapi.testclient import TestClient

from app.catalog import load_catalog
from app.engine import run_diagnostic
from app.evolution import ResumeSuivi
from app.feedback import valeurs
from app.main import app
from app.questionnaire import InvalidAnswers, validate

client = TestClient(app)

ENFANT = {
    "pour": "enfant", "age_jeune": "enfant", "type_cheveux": "4A", "epaisseur": "fin",
    "densite": "forte", "porosite": "forte", "cuir_chevelu": "sec", "objectif": "demelage",
    "preoccupations": ["demelage", "poux"], "intensites": {"demelage": "enormement", "poux": "un_peu"},
}
ADO = {
    "pour": "ado", "age_jeune": "ado", "type_cheveux": "2B", "epaisseur": "moyen",
    "densite": "moyenne", "porosite": "moyenne", "cuir_chevelu": "gras", "chaleur": "souvent",
    "objectif": "autonomie", "preoccupations": ["alourdis"], "intensites": {"alourdis": "beaucoup"},
}


def diag(base, **kw):
    return run_diagnostic(validate({**base, **kw}))


def titres(d):
    return [s.titre for s in d.routine]


# --- Questionnaire --------------------------------------------------------------------


def test_parcours_enfant_ignore_les_questions_d_adulte():
    a = validate({**ENFANT, "chaleur": "souvent", "traitements": ["decoloration"],
                  "periodes": ["grossesse"], "age": "30_44"})
    assert a.pour == "enfant" and a.chaleur == "jamais" and a.traitements == []
    assert a.periodes == [] and a.age == "moins_18"


def test_reponses_propres_a_un_parcours():
    adulte = {k: v for k, v in ENFANT.items() if k not in {"pour", "age_jeune"}}
    with pytest.raises(InvalidAnswers) as e:
        validate({**adulte, "chaleur": "jamais"})
    assert "preoccupations" in e.value.errors and "objectif" in e.value.errors
    with pytest.raises(InvalidAnswers):
        validate({**ADO, "periodes": ["grossesse"]})


def test_ado_doit_repondre_sur_la_chaleur():
    with pytest.raises(InvalidAnswers) as e:
        validate({k: v for k, v in ADO.items() if k != "chaleur"})
    assert "chaleur" in e.value.errors


# --- Enfant ----------------------------------------------------------------------------


def test_routine_enfant_courte_et_douce():
    d = diag(ENFANT)
    t = titres(d)
    assert "Démêlant" in t and "Vérifier les poux" in t and "Coiffer sans tirer" in t
    assert "Protection thermique" not in t and "Shampoing clarifiant" not in t
    assert len(d.routine) <= 10
    produits = {s.titre: s.produit.id for s in d.routine if s.produit}
    assert produits["Protéger les cheveux"] == "bonnet-satin"
    assert produits["Vérifier les poux"] == "divers-peigne-anti-poux"
    assert not any("Masque" in a for ph in d.programme for a in ph["actions"])
    for s in d.routine:
        if s.produit:
            assert s.produit.public in {"enfant", "tous"}, s.produit.id


def test_bebe_routine_minimale_et_croutes_de_lait():
    d = diag(ENFANT, age_jeune="bebe", preoccupations=["croutes_lait"],
             intensites={"croutes_lait": "beaucoup"})
    assert titres(d) == ["Shampoing doux", "Croûtes de lait"]
    assert d.recettes == []
    assert "bébé" in d.frequence_lavage


def test_chute_chez_l_enfant_pediatre_et_dermato():
    d = diag(ENFANT, preoccupations=["chute"], intensites={"chute": "un_peu"})
    assert any("pédiatre" in a and "teigne" in a for a in d.alertes)
    noms = [s["nom"] for s in d.orientation["specialistes"]]
    assert noms[:2] == ["Pédiatre ou médecin traitant", "Dermatologue"]


def test_pas_de_complement_ni_de_conseil_ado_pour_un_enfant():
    d = diag(ENFANT)
    assert d.cures == [] and "pédiatre" in d.cures_message
    assert not any("puberté" in c or "hormonaux" in c for c in d.conseils + d.conseils_vie)
    assert any("démêlage sans larmes" in c for c in d.conseils)
    assert "Le profil" not in d.resume and d.resume.startswith("Enfant de 6 à 11 ans")


def test_coiffures_serrees_et_piscine():
    d = diag(ENFANT, coiffures=["serrees", "piscine"])
    assert any("tirent sur les tempes" in c for c in d.conseils)
    assert any("Piscine" in c for c in d.conseils)


# --- Ado ---------------------------------------------------------------------------------


def test_ado_conseils_et_pas_de_cure():
    d = diag(ADO, preoccupations=["chute"], intensites={"chute": "beaucoup"})
    assert any("puberté" in c for c in d.conseils)
    assert any("protecteur thermique" in c for c in d.conseils)
    assert any("16 ans" in c for c in d.conseils)
    assert any("Pour vous lancer" in c for c in d.conseils)
    assert d.cures == [] and "18 ans" in d.cures_message
    assert "Protection thermique" in titres(d)


def test_ado_orientation_pediatre_ou_medecin_traitant():
    d = diag(ADO, sante=["regles_abondantes"])
    assert d.orientation["specialistes"][0]["nom"] == "Pédiatre ou médecin traitant"


# --- Produits, suivi, avis -------------------------------------------------------------


def test_adulte_ne_recoit_jamais_de_produit_enfant():
    enfants = {p.id for p in load_catalog() if p.public == "enfant"}
    d = run_diagnostic(validate({**{k: v for k, v in ADO.items() if k not in {"pour", "age_jeune"}},
                                 "objectif": "hydratation"}))
    assert not ({s.produit.id for s in d.routine if s.produit} & enfants)


def test_pas_de_comparaison_entre_parcours():
    prec = ResumeSuivi(id="x", date="2026-10-01", type_cheveux="3B", pour="adulte",
                       intensites={"secheresse": "beaucoup"})
    d = run_diagnostic(validate(ENFANT), precedent=prec)
    assert d.evolution is None and d.suivi["pour"] == "enfant"


def test_parcours_dans_les_avis():
    assert valeurs(diag(ENFANT))["TS_RESUME"].startswith("Parcours enfant")


# --- Pages ----------------------------------------------------------------------------------


def test_lien_direct_vers_le_parcours_enfant():
    r = client.get("/diagnostic?pour=enfant")
    assert 'name="pour" value="enfant" checked' in r.text
    assert "Pour un·e ado" in r.text and "Poux ou lentes" in r.text
    assert 'data-publics="enfant"' in r.text


def test_accueil_propose_les_parcours_jeunes():
    r = client.get("/")
    assert "/diagnostic?pour=enfant" in r.text and "/diagnostic?pour=ado" in r.text


def test_resultat_enfant():
    form = {k: v for k, v in ENFANT.items() if k not in {"preoccupations", "intensites"}}
    form.update({"prenom": "Inès", "preoccupations": ["demelage"], "gene_demelage": "beaucoup"})
    r = client.post("/diagnostic", data=form)
    assert r.status_code == 200
    assert "Le profil capillaire d’Inès" in r.text
