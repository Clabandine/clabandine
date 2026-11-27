"""Améliorations issues des retours de test : accès, achat, simplicité, crédibilité,
budget et relation client."""

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import inscriptions, liens_admin
from app.catalog import load_catalog
from app.engine import run_diagnostic
from app.main import app
from app.questionnaire import validate

client = TestClient(app)
RACINE = Path(__file__).resolve().parent.parent.parent

ANSWERS = {
    "type_cheveux": "3C", "epaisseur": "moyen", "densite": "forte", "porosite": "forte",
    "elasticite": "equilibre", "cuir_chevelu": "normal", "chaleur": "jamais",
    "objectif": "hydratation", "preoccupations": ["secheresse"], "intensites": {"secheresse": "beaucoup"},
}
FORM = {**{k: v for k, v in ANSWERS.items() if k not in {"preoccupations", "intensites"}},
        "preoccupations": ["secheresse"], "gene_secheresse": "beaucoup"}


def diag(**kw):
    return run_diagnostic(validate({**ANSWERS, **kw}))


# --- 1. Accès -----------------------------------------------------------------------------


def test_pages_marquees_pour_le_cache_de_l_application():
    assert client.get("/").headers["x-trichosens"] == "1"
    sw = client.get("/sw.js").text
    assert 'X-TrichoSens' in sw and "event.waitUntil(reseau" in sw


def test_reveil_automatique_du_site():
    wf = (RACINE / ".github" / "workflows" / "trichosens-reveil.yml").read_text(encoding="utf-8")
    assert "*/10 5-22 * * *" in wf and "/sante" in wf


# --- 2. Liens d'achat exacts ---------------------------------------------------------------


def test_lien_amazon_nettoye_avec_l_identifiant():
    url, affilie = liens_admin.normaliser(
        "https://www.amazon.fr/Cantu-Shampoing/dp/B01LTHM8LG/ref=sr_1_3?keywords=cantu&qid=1")
    assert url == "https://www.amazon.fr/dp/B01LTHM8LG?tag=trichosens-21" and affilie


@pytest.mark.parametrize("url,message", [
    ("https://amzn.eu/d/abc123", "lien court"),
    ("https://www.amazon.fr/s?k=cantu", "fiche produit"),
    ("https://www.amazon.ca/dp/B01LTHM8LG", "identifiant"),
    ("http://www.amazon.fr/dp/B01LTHM8LG", "https://"),
])
def test_liens_refuses(url, message):
    with pytest.raises(liens_admin.LienInvalide, match=message):
        liens_admin.normaliser(url)


def test_revendeur_officiel_garde_tel_quel():
    assert liens_admin.normaliser("https://www.aroma-zone.com/info/fiche/x") == (
        "https://www.aroma-zone.com/info/fiche/x", False)


@pytest.fixture
def ajustements(monkeypatch):
    monkeypatch.setattr(liens_admin, "stockage", liens_admin.Memoire())
    liens_admin._changement()
    yield
    liens_admin._changement()


def test_fiche_exacte_remplace_la_recherche(ajustements):
    liens_admin.ajuster("cantu-shampoo", "Amazon", "https://www.amazon.fr/dp/B01LTHM8LG")
    liens_admin.ajuster("cantu-shampoo", "Site officiel", "https://www.cantubeauty.com/shampoo")
    p = next(x for x in liens_admin.catalogue_complet(load_catalog()) if x.id == "cantu-shampoo")
    amazon = next(o for o in p.offres if o.marchand == "Amazon")
    assert not amazon.recherche and amazon.pays == ("FR", "BE", "LU", "MC")
    assert any(o.marchand == "Site officiel" for o in p.offres)
    r = client.get(f"/acheter/{amazon.id}", follow_redirects=False)
    assert r.headers["location"] == "https://www.amazon.fr/dp/B01LTHM8LG?tag=trichosens-21"


def test_admin_liens(ajustements, monkeypatch):
    monkeypatch.setenv("ADMIN_CLE", "secret")
    assert client.get("/admin/liens").status_code == 404
    r = client.get("/admin/liens?cle=secret")
    assert "n'ont encore qu'un lien de recherche" in r.text
    r = client.post("/admin/liens", data={"cle": "secret", "produit_id": "cantu-shampoo", "marchand": "Amazon",
                                          "url": "https://www.amazon.fr/dp/B01LTHM8LG"}, follow_redirects=False)
    assert r.status_code == 303 and "message=" in r.headers["location"]
    r = client.post("/admin/liens", data={"cle": "secret", "produit_id": "cantu-shampoo", "marchand": "Amazon",
                                          "url": "https://amzn.eu/d/x"}, follow_redirects=False)
    assert "erreur=" in r.headers["location"]
    csv = client.get("/admin/liens.csv?cle=secret").text
    assert "cantu-shampoo;Amazon;https://www.amazon.fr/dp/B01LTHM8LG?tag=trichosens-21" in csv


# --- 3. Simplicité --------------------------------------------------------------------------


def test_parcours_express_valeurs_par_defaut():
    a = validate({"mode": "express", "type_cheveux": "3C", "cuir_chevelu": "sec", "chaleur": "jamais",
                  "objectif": "hydratation", "preoccupations": ["secheresse"],
                  "intensites": {"secheresse": "beaucoup"}})
    assert (a.mode, a.epaisseur, a.densite, a.porosite) == ("express", "moyen", "moyenne", "inconnue")
    d = run_diagnostic(a)
    assert any("diagnostic express" in x for x in d.fiabilite["a_ameliorer"])


def test_pages_du_parcours_express():
    html = client.get("/diagnostic").text
    assert 'name="mode" value="express" checked' in html
    assert 'data-step="texture"' in html and 'data-express="0"' in html
    assert "data-affiner" in html and "Répondre aux questions santé" in html
    assert 'name="mode" value="complet" checked' in client.get("/diagnostic?mode=complet").text


def test_trois_actions_essentielles():
    d = diag()
    assert len(d.actions_cles) == 3
    assert d.actions_cles[0]["titre"] == "Contre sécheresse"
    assert d.actions_cles[1]["produit"] in d.essentiels
    r = client.post("/diagnostic", data=FORM).text
    assert "Vos 3 actions essentielles" in r
    assert r.index("Vos 3 actions essentielles") < r.index("Les besoins de vos cheveux")


def test_onglet_complements_seulement_si_utile():
    assert 'id="tab-complements"' not in client.post("/diagnostic", data=FORM).text
    form = {**FORM, "preoccupations": ["chute"], "gene_chute": "beaucoup"}
    assert 'id="tab-complements"' in client.post("/diagnostic", data=form).text


# --- 4. Crédibilité -------------------------------------------------------------------------


def test_profil_renseigne_sans_note_sur_100():
    assert diag().fiabilite["label"] == "Profil complet"
    r = client.post("/diagnostic", data=FORM).text
    bloc = r.split('class="card fiabilite')[1].split("</div>")[0]
    assert "/100" not in bloc and "Comment est-ce évalué" in bloc


# --- 5. Budget ------------------------------------------------------------------------------


def test_indispensables_et_cout_pour_commencer():
    d = diag(budget="petit")
    essentiels = {s.categorie for s in d.routine if s.essentiel}
    assert "shampoing" in essentiels and "leave_in" in essentiels
    assert not {"huile", "shampoing_clarifiant", "accessoire"} & essentiels
    assert 0 < d.cout_essentiel < d.cout_total
    r = client.post("/diagnostic", data={**FORM, "budget": "petit"}).text
    assert "Pour commencer" in r and "Pour aller plus loin" in r and "Indispensable" in r


def test_protecteur_thermique_indispensable_si_chaleur():
    d = diag(chaleur="souvent")
    assert any(s.categorie == "protecteur_thermique" and s.essentiel for s in d.routine)


# --- 6. Relation client ----------------------------------------------------------------------


@pytest.fixture
def inscrits(monkeypatch):
    stockage = inscriptions.Memoire()
    monkeypatch.setattr(inscriptions, "stockage", stockage)
    monkeypatch.setattr(inscriptions, "limiteur", inscriptions.Limiteur(par_heure=10))
    return stockage


def test_inscription_consentements_distincts(inscrits):
    r = client.post("/api/inscription", json={"email": "Awa@Exemple.fr", "conseils": True,
                                              "partenaires": False, "type_cheveux": "3C"})
    assert r.status_code == 200
    i = inscrits.lister()[0]
    assert (i.email, i.conseils, i.partenaires, i.type_cheveux) == ("awa@exemple.fr", True, False, "3C")
    assert i.version and i.cree_le


def test_inscription_refusee_sans_accord_ou_mauvais_email(inscrits):
    assert client.post("/api/inscription", json={"email": "a@b.fr", "conseils": False}).status_code == 422
    assert client.post("/api/inscription", json={"email": "pas-un-email", "conseils": True}).status_code == 422
    client.post("/api/inscription", json={"email": "robot@x.fr", "conseils": True, "site": "spam"})
    assert inscrits.lister() == []


def test_inscription_sans_javascript_et_desinscription(inscrits):
    r = client.post("/inscription", data={"email": "lea@exemple.fr", "conseils": "oui"})
    assert r.status_code == 200 and "Merci" in r.text
    r = client.post("/desinscription", data={"email": "lea@exemple.fr"})
    assert "supprimée" in r.text and inscrits.lister() == []


def test_formulaire_apres_le_resultat_et_admin(inscrits, monkeypatch):
    r = client.post("/diagnostic", data=FORM).text
    assert "data-inscription" in r and 'name="partenaires"' in r and 'value="3C"' in r
    monkeypatch.setenv("ADMIN_CLE", "secret")
    client.post("/api/inscription", json={"email": "ines@exemple.fr", "conseils": True, "partenaires": True})
    assert "ines@exemple.fr" in client.get("/admin/inscriptions?cle=secret").text
    csv = client.get("/admin/inscriptions.csv?cle=secret").text
    assert "ines@exemple.fr;oui;oui;" in csv
    assert client.get("/admin/inscriptions.csv").status_code == 404


def test_confidentialite_mentionne_les_emails():
    assert "Conseils et rappels par e-mail" in client.get("/confidentialite").text
