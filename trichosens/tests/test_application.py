import json
from pathlib import Path

from fastapi.testclient import TestClient

from app.main import app
from app.stats import stats

client = TestClient(app)
STATIQUE = Path(__file__).resolve().parent.parent / "app" / "static"


def total(evt):
    return sum(n for _, e, v, n in stats.lire(1) if e == evt)


def test_manifeste_installable():
    r = client.get("/site.webmanifest")
    assert r.status_code == 200 and "manifest+json" in r.headers["content-type"]
    m = json.loads(r.content)
    assert m["display"] == "standalone" and m["start_url"] == "/?source=app" and m["scope"] == "/"
    tailles = {(i["sizes"], i.get("purpose", "any")) for i in m["icons"]}
    assert {("192x192", "any"), ("512x512", "any"), ("512x512", "maskable")} <= tailles
    for icone in m["icons"]:
        assert (STATIQUE / icone["src"].removeprefix("/static/")).exists(), icone["src"]


def test_service_worker_a_la_racine():
    r = client.get("/sw.js")
    assert r.status_code == 200 and "javascript" in r.headers["content-type"]
    assert r.headers["cache-control"] == "no-cache"
    assert "__VERSION__" not in r.text and "trichosens-dev" in r.text
    assert '"/suivi"' in r.text and '"/hors-ligne"' in r.text


def test_version_du_cache_suit_la_mise_en_ligne(monkeypatch):
    monkeypatch.setenv("RENDER_GIT_COMMIT", "abc123def4567890")
    assert "trichosens-abc123def456" in client.get("/sw.js").text


def test_pages_application_et_hors_ligne():
    assert "Comment l'installer" in client.get("/application").text
    assert "Voir mon suivi" in client.get("/hors-ligne").text


def test_chaque_page_propose_l_installation():
    r = client.get("/").text
    assert 'rel="manifest" href="/site.webmanifest"' in r
    assert "installer.js" in r and 'id="installer-aide"' in r
    assert "data-installer" in r and 'apple-mobile-web-app-capable' in r


def test_lien_play_store_seulement_si_configure(monkeypatch):
    assert client.get("/.well-known/assetlinks.json").status_code == 404
    monkeypatch.setenv("ANDROID_PACKAGE", "fr.trichosens.app")
    monkeypatch.setenv("ANDROID_CERT_SHA256", "AA:BB")
    data = client.get("/.well-known/assetlinks.json").json()
    assert data[0]["target"]["package_name"] == "fr.trichosens.app"
    assert data[0]["target"]["sha256_cert_fingerprints"] == ["AA:BB"]


def test_ouvertures_de_l_application_comptees_a_part():
    avant = total("ouverture_app"), total("visite_accueil")
    client.get("/?source=app", headers={"user-agent": "Mozilla/5.0 (iPhone)"})
    assert (total("ouverture_app"), total("visite_accueil")) == (avant[0] + 1, avant[1])
    client.post("/api/evenement", json={"nom": "app_installee"})
    assert total("app_installee") >= 1
