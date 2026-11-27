import csv
import shutil
import sqlite3
from dataclasses import replace

import pytest
from fastapi.testclient import TestClient

from app import engine, partenaires
from app.catalog import Offre, load_catalog, load_offres
from app.engine import run_diagnostic
from app.main import app
from app.questionnaire import validate

client = TestClient(app)

ANSWERS = {
    "type_cheveux": "3C", "epaisseur": "moyen", "densite": "forte", "porosite": "forte",
    "cuir_chevelu": "normal", "chaleur": "jamais", "objectif": "hydratation",
    "preoccupations": ["secheresse"], "intensites": {"secheresse": "beaucoup"},
}
FORM = {**{k: v for k, v in ANSWERS.items() if k not in {"preoccupations", "intensites"}},
        "preoccupations": ["secheresse"], "gene_secheresse": "beaucoup"}


# --- Liens par pays ----------------------------------------------------------------------


def ecrire_liens(tmp_path, lignes):
    p = tmp_path / "liens.csv"
    with open(p, "w", encoding="utf-8", newline="") as f:
        w = csv.writer(f, delimiter=";")
        w.writerow(["produit_id", "marchand", "url", "prix", "affilie", "actif", "awin_mid", "pays"])
        w.writerows(lignes)
    return p


def test_pays_lus_et_trichosens_en_tete(tmp_path):
    p = ecrire_liens(tmp_path, [
        ["a", "Amazon", "https://www.amazon.fr/dp/X", "", "oui", "", "", "fr|be"],
        ["a", "Amazon Canada", "https://www.amazon.ca/dp/X", "", "oui", "", "", "CA"],
        ["a", "TrichoSens", "https://boutique.trichosens.fr/x", "29", "non", "", "", ""],
    ])
    offres = load_offres(p, {"a"})["a"]
    assert offres[0].trichosens and offres[0].pays == ()
    assert {o.marchand: o.pays for o in offres}["Amazon"] == ("FR", "BE")


def test_pays_mal_ecrit_refuse(tmp_path):
    p = ecrire_liens(tmp_path, [["a", "Amazon", "https://www.amazon.fr/dp/X", "", "oui", "", "", "France"]])
    with pytest.raises(ValueError, match="2 lettres"):
        load_offres(p, {"a"})


def test_liens_amazon_fr_pour_la_france_et_ses_voisins():
    amazon = [o for p in load_catalog() for o in p.offres if o.marchand == "Amazon"]
    assert amazon and all(o.pays == ("FR", "BE", "LU", "MC") for o in amazon)


def test_resultat_marque_les_pays_et_propose_le_choix():
    r = client.post("/diagnostic", data=FORM)
    assert 'data-pays="FR BE LU MC"' in r.text
    assert 'id="pays-livraison"' in r.text and "Canada" in r.text
    assert "Livraison depuis la France" in r.text


def test_script_amazon_autre_pays(tmp_path, monkeypatch):
    from scripts import liens_amazon
    for f in ("produits.csv", "liens.csv"):
        shutil.copy(liens_amazon.DATA / f, tmp_path / f)
    monkeypatch.setattr(liens_amazon, "DATA", tmp_path)
    with pytest.raises(SystemExit):
        liens_amazon.main(["--boutique", "ca"])  # identifiant obligatoire
    liens_amazon.main(["--boutique", "ca", "--tag", "trichosens-20"])
    lignes = list(csv.DictReader(open(tmp_path / "liens.csv", encoding="utf-8"), delimiter=";"))
    ca = [l for l in lignes if l["marchand"] == "Amazon Canada"]
    assert ca and all(l["pays"] == "CA" and "amazon.ca" in l["url"] and "trichosens-20" in l["url"] for l in ca)
    # Relancer n'ajoute pas de doublons.
    liens_amazon.main(["--boutique", "ca", "--tag", "trichosens-20"])
    assert len([l for l in csv.DictReader(open(tmp_path / "liens.csv", encoding="utf-8"), delimiter=";")
                if l["marchand"] == "Amazon Canada"]) == len(ca)


# --- Acheter chez TrichoSens et coffret ------------------------------------------------------


@pytest.fixture
def catalogue_trichosens(monkeypatch):
    base = load_catalog()
    shampoing = next(p for p in base if p.id == "cantu-shampoo")
    offre = Offre(id="cantu-shampoo--trichosens", produit_id="cantu-shampoo", marchand="TrichoSens",
                  url="https://boutique.trichosens.fr/cantu", prix=9.5)
    coffret = replace(shampoing, id="coffret-3c", marque="TrichoSens", nom="Coffret routine boucles serrées",
                      categorie="coffret", description="Shampoing, masque et crème pour les types 3C à 4A.",
                      types=("3C", "4A"), prix=39.0,
                      offres=(Offre(id="coffret-3c--trichosens", produit_id="coffret-3c",
                                    marchand="TrichoSens", url="https://boutique.trichosens.fr/coffret-3c"),))
    cat = [replace(p, offres=(offre, *p.offres)) if p.id == "cantu-shampoo" else p for p in base] + [coffret]
    monkeypatch.setattr(engine, "load_catalog", lambda: cat)
    return cat


def test_coffret_propose_au_bon_profil(catalogue_trichosens):
    assert run_diagnostic(validate(ANSWERS)).coffret.id == "coffret-3c"
    assert run_diagnostic(validate({**ANSWERS, "type_cheveux": "1A"})).coffret is None


def test_pas_de_coffret_sans_produit():
    assert run_diagnostic(validate(ANSWERS)).coffret is None


def test_bouton_acheter_chez_trichosens(catalogue_trichosens):
    r = client.post("/diagnostic", data=FORM)
    assert "Votre routine en un coffret" in r.text and "Coffret routine boucles serrées" in r.text
    assert "Acheter chez TrichoSens" in r.text and "Vendu et expédié par TrichoSens" in r.text
    assert 'class="offre offre-trichosens"' in r.text


# --- Marques partenaires ------------------------------------------------------------------


DEMANDE = {"marque": "Belles Boucles", "type": "marque", "nom": "Inès", "email": "ines@bellesboucles.fr",
           "site": "bellesboucles.fr", "message": "Gamme pour cheveux 4C.", "accord": "oui"}


@pytest.fixture
def demandes(monkeypatch):
    stockage = partenaires.Memoire()
    monkeypatch.setattr(partenaires, "stockage", stockage)
    monkeypatch.setattr(partenaires, "limiteur", partenaires.Limiteur(par_heure=2))
    return stockage


def test_page_marques():
    r = client.get("/marques")
    assert r.status_code == 200 and "Travaillons ensemble" in r.text and "Notre charte" in r.text
    assert 'href="/marques"' in client.get("/").text


def test_demande_enregistree(demandes):
    r = client.post("/marques", data=DEMANDE)
    assert r.status_code == 200 and "Merci" in r.text
    d = demandes.lister()[0]
    assert d.marque == "Belles Boucles" and d.site == "https://bellesboucles.fr"


def test_demande_incomplete(demandes):
    r = client.post("/marques", data={**DEMANDE, "email": "pas-un-email", "accord": ""})
    assert r.status_code == 422 and "adresse e-mail valide" in r.text
    assert demandes.lister() == []


def test_robots_et_envois_en_masse(demandes):
    client.post("/marques", data={**DEMANDE, "site_web_2": "spam"})
    assert demandes.lister() == []
    for _ in range(2):
        client.post("/marques", data=DEMANDE)
    r = client.post("/marques", data=DEMANDE)
    assert r.status_code == 429 and len(demandes.lister()) == 2


def test_admin_partenaires(demandes, monkeypatch):
    monkeypatch.setenv("ADMIN_CLE", "secret")
    client.post("/marques", data=DEMANDE)
    assert client.get("/admin/partenaires").status_code == 404
    r = client.get("/admin/partenaires?cle=secret")
    assert "Belles Boucles" in r.text and "mailto:ines@bellesboucles.fr" in r.text
    assert "Demandes de partenariat</a> (1)" in client.get("/admin?cle=secret").text


def test_stockage_sql(tmp_path):
    chemin = tmp_path / "p.db"
    base = partenaires.BaseSQL(lambda: sqlite3.connect(chemin), marque="?")
    d = partenaires.valider(DEMANDE)
    partenaires.stockage, ancien = base, partenaires.stockage
    try:
        partenaires.enregistrer(d)
    finally:
        partenaires.stockage = ancien
    relu = partenaires.BaseSQL(lambda: sqlite3.connect(chemin), marque="?").lister()
    assert relu[0].email == "ines@bellesboucles.fr" and relu[0].cree_le is not None
