import datetime as dt
import threading
from dataclasses import replace
from http.server import BaseHTTPRequestHandler, HTTPServer

import pytest
from fastapi.testclient import TestClient

from app import main
from app.catalog import Offre, load_catalog, parse_product, raison_a_revoir
from scripts.verifier_catalogue import verifier_lien

TODAY = dt.date(2026, 11, 1)


@pytest.fixture(scope="module")
def serveur():
    class H(BaseHTTPRequestHandler):
        def do_GET(self):
            code = {"/ok": 200, "/mort": 404, "/bloque": 503}.get(self.path, 404)
            self.send_response(code)
            self.end_headers()

        def log_message(self, *a):
            pass

    srv = HTTPServer(("127.0.0.1", 0), H)
    threading.Thread(target=srv.serve_forever, daemon=True).start()
    yield f"http://127.0.0.1:{srv.server_port}"
    srv.shutdown()


def test_link_checker(serveur):
    assert verifier_lien(serveur + "/ok").statut == "ok"
    assert verifier_lien(serveur + "/mort").statut == "mort"
    assert verifier_lien(serveur + "/bloque", essais=1).statut == "non_verifiable"
    assert verifier_lien("https://www.amazon.fr/s?k=cantu&tag=x").statut == "recherche"
    assert verifier_lien("http://127.0.0.1:9/rien", timeout=1, essais=1).statut == "non_verifiable"


def produit(**kw):
    base = parse_product({"id": "x", "marque": "M", "nom": "N", "categorie": "masque",
                          "a_verifier": "non", "date_verification": "2026-09-01"})
    kw.setdefault("offres", (Offre("x--a", "x", "A", "https://a.example"),))
    return replace(base, **kw)


def test_review_reasons():
    assert raison_a_revoir(produit(), TODAY) is None
    assert raison_a_revoir(produit(verifie_le=None), TODAY) == "Jamais vérifiée"
    assert "à vérifier" in raison_a_revoir(produit(a_verifier=True), TODAY)
    assert "plus de 6 mois" in raison_a_revoir(produit(verifie_le=dt.date(2026, 1, 2)), TODAY)
    assert raison_a_revoir(produit(offres=()), TODAY) == "Aucun lien d'achat"


def test_french_date_format_is_accepted():
    p = parse_product({"id": "x", "marque": "M", "nom": "N", "categorie": "masque",
                       "date_verification": "30/11/2026"})
    assert p.verifie_le == dt.date(2026, 11, 30)
    with pytest.raises(ValueError, match="date de vérification"):
        parse_product({"id": "x", "marque": "M", "nom": "N", "categorie": "masque",
                       "date_verification": "bientôt"})


def test_admin_catalogue_page(monkeypatch):
    client = TestClient(main.app)
    monkeypatch.setenv("ADMIN_CLE", "secret")
    assert client.get("/admin/catalogue", params={"cle": "faux"}).status_code == 404
    r = client.get("/admin/catalogue", params={"cle": "secret"})
    assert r.status_code == 200
    assert f"<strong>{len(load_catalog())}</strong> fiches" in r.text  # aucune vérifiée pour l'instant
