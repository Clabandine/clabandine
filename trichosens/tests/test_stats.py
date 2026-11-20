import datetime as dt
import os
import sqlite3
from collections import Counter

import pytest
from fastapi.testclient import TestClient

from app import admin
from app.main import app
from app.stats import BaseSQL, Memoire, Statistiques, aujourd_hui, stats, synthese

client = TestClient(app)

FORM = {
    "type_cheveux": "3C", "epaisseur": "moyen", "densite": "forte", "porosite": "inconnue",
    "cuir_chevelu": "sec", "preoccupations": ["secheresse"], "gene_secheresse": "beaucoup",
    "chaleur": "jamais", "objectif": "hydratation", "prenom": "Awa",
    "periodes": ["grossesse"], "sante": ["carence_fer"],
}


def total(evenement, valeur=None):
    lignes = stats.lire(1)
    return sum(n for _, e, v, n in lignes if e == evenement and (valeur is None or v == valeur))


# --- Stockage -----------------------------------------------------------------------


def test_memoire_compte_par_jour():
    s = Statistiques(Memoire())
    s.compter("gene", "casse")
    s.compter("gene", "casse")
    s.compter("gene", "frisottis")
    lignes = s.lire(7)
    assert sorted((e, v, n) for _, e, v, n in lignes) == [("gene", "casse", 2), ("gene", "frisottis", 1)]


def test_valeur_douteuse_remplacee():
    s = Statistiques(Memoire())
    s.compter("clic_marchand", "<script>alert(1)</script>")
    assert s.lire(1)[0][2] == "autre"


def test_base_sql_additionne_les_lots(tmp_path):
    chemin = tmp_path / "stats.db"
    base = BaseSQL(lambda: sqlite3.connect(chemin), marque="?")
    s = Statistiques(base, intervalle=60)
    s.compter("type", "4C")
    s.compter("type", "4C")
    s.vider()
    s.compter("type", "4C")
    lignes = s.lire(1)  # lire vide d'abord ce qui est en attente
    assert [(e, v, n) for _, e, v, n in lignes] == [("type", "4C", 3)]
    # Un nouveau démarrage relit les mêmes chiffres : ils sont durables.
    assert BaseSQL(lambda: sqlite3.connect(chemin), marque="?").lire(aujourd_hui())[0][3] == 3


def test_base_injoignable_garde_les_compteurs():
    class Panne:
        persistant = True

        def ecrire(self, lots):
            raise OSError("base injoignable")

        def lire(self, depuis):
            return []

    s = Statistiques(Panne(), intervalle=60)
    s._fil = object()  # pas de fil d'arrière-plan pendant le test
    s.compter("type", "1A")
    s.vider()
    assert s.erreur and s._attente == Counter({(aujourd_hui(), "type", "1A"): 1})


@pytest.mark.skipif(not os.environ.get("TEST_DATABASE_URL"), reason="Postgres non disponible")
def test_postgres_reel():
    from app.stats import _postgres
    base = _postgres(os.environ["TEST_DATABASE_URL"])
    s = Statistiques(base, intervalle=60)
    s.compter("test_pg", "a", 2)
    s.vider()
    s.compter("test_pg", "a", 1)
    assert sum(n for _, e, v, n in s.lire(1) if e == "test_pg") >= 3


def test_synthese_calendrier_complet():
    hier = aujourd_hui() - dt.timedelta(days=1)
    s = synthese([(hier, "diagnostic_termine", "adulte", 2), (aujourd_hui(), "diagnostic_termine", "enfant", 1)], 7)
    assert s["totaux"]["diagnostic_termine"] == 3
    assert len(s["courbe"]["diagnostic_termine"]) == 7
    assert s["courbe"]["diagnostic_termine"][-2:] == [(hier, 2), (aujourd_hui(), 1)]


# --- Ce qui est compté -----------------------------------------------------------------


def test_diagnostic_compte_sans_donnees_personnelles_ni_sante():
    avant = total("diagnostic_termine", "adulte"), total("type", "3C")
    r = client.post("/diagnostic", data=FORM)
    assert r.status_code == 200
    assert total("diagnostic_termine", "adulte") == avant[0] + 1
    assert total("type", "3C") == avant[1] + 1
    evenements = {e for _, e, v, n in stats.lire(1)}
    valeurs = {v for _, e, v, n in stats.lire(1)}
    assert not {"sante", "periodes", "prenom"} & evenements
    assert not {"carence_fer", "grossesse", "Awa"} & valeurs


def test_robots_non_comptes():
    avant = total("visite_accueil")
    client.get("/", headers={"user-agent": "Googlebot/2.1"})
    client.get("/", headers={"user-agent": "UptimeRobot/2.0"})
    assert total("visite_accueil") == avant
    client.get("/", headers={"user-agent": "Mozilla/5.0 (iPhone)"})
    assert total("visite_accueil") == avant + 1


def test_evenements_du_navigateur_liste_fermee():
    avant = total("onglet_resultat", "naturel")
    assert client.post("/api/evenement", json={"nom": "onglet_resultat", "valeur": "naturel"}).status_code == 204
    assert total("onglet_resultat", "naturel") == avant + 1
    client.post("/api/evenement", json={"nom": "n_importe_quoi", "valeur": "x"})
    client.post("/api/evenement", content=b"pas du json")
    assert total("n_importe_quoi") == 0


def test_clic_produit_compte():
    from app.catalog import load_catalog
    p = next(p for p in load_catalog() if p.offres)
    avant = total("clic_produit", p.id)
    client.get(f"/acheter/{p.offres[0].id}", follow_redirects=False)
    assert total("clic_produit", p.id) == avant + 1


# --- Tableau de bord -----------------------------------------------------------------------


def test_tableau_protege_par_la_cle(monkeypatch):
    monkeypatch.setenv("ADMIN_CLE", "secret")
    assert client.get("/admin").status_code == 404
    assert client.get("/admin?cle=mauvaise").status_code == 404
    r = client.get("/admin?cle=secret")
    assert r.status_code == 200
    assert "Tableau de bord" in r.text and "Diagnostics terminés" in r.text


def test_tableau_affiche_les_chiffres(monkeypatch):
    monkeypatch.setenv("ADMIN_CLE", "secret")
    client.post("/diagnostic", data=FORM)
    t = admin.tableau(stats, 7)
    chiffres = {c["label"]: c["valeur"] for c in t["chiffres"]}
    assert chiffres["Diagnostics terminés"] >= 1
    types = dict((titre, lignes) for titre, lignes in t["sections"])["Types de cheveux"]
    assert any(l["label"].startswith("3C") for l in types)
    r = client.get("/admin?cle=secret&jours=7")
    assert "3C · Boucles très serrées" in r.text
    assert "<svg" in r.text


def test_export_csv(monkeypatch):
    monkeypatch.setenv("ADMIN_CLE", "secret")
    client.post("/diagnostic", data=FORM)
    r = client.get("/admin/export.csv?cle=secret&jours=7")
    assert r.status_code == 200 and r.headers["content-type"].startswith("text/csv")
    assert "jour;evenement;valeur;nombre" in r.text and ";type;3C;" in r.text
    assert client.get("/admin/export.csv").status_code == 404
