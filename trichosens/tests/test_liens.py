import pytest
from fastapi.testclient import TestClient

from app import engine, main
from app.catalog import CATALOG_PATH, load_catalog
from app.clicks import ClickCounter

client = TestClient(main.app)
HEADER = "produit_id;marchand;url;prix;affilie;actif;awin_mid\n"
LIENS = HEADER + (
    "cantu-leave-in;Amazon;https://www.amazon.fr/dp/EXEMPLE?tag=trichosens-21;8,90;oui;\n"
    "cantu-leave-in;Pharmacie;https://pharmacie.example/cantu;9,50;non;\n"
    "cantu-leave-in;Ancien site;https://old.example/cantu;7,00;non;non\n"
)
FORM = {"type_cheveux": "4C", "epaisseur": "fin", "densite": "forte", "porosite": "forte",
        "cuir_chevelu": "sec", "preoccupations": ["secheresse"], "gene_secheresse": "beaucoup",
        "chaleur": "jamais", "objectif": "hydratation"}


def catalog_with(tmp_path, content):
    f = tmp_path / "liens.csv"
    f.write_text(content, encoding="utf-8")
    return load_catalog(CATALOG_PATH, f)


def test_links_are_attached_cheapest_first_and_inactive_skipped(tmp_path):
    cat = catalog_with(tmp_path, LIENS)
    p = next(p for p in cat if p.id == "cantu-leave-in")
    assert [o.marchand for o in p.offres] == ["Amazon", "Pharmacie"]
    assert p.offres[0].affilie and not p.offres[1].affilie
    assert p.offres[0].id == "cantu-leave-in--amazon"


@pytest.mark.parametrize("line, message", [
    ("inconnu;Amazon;https://a.example;;;", "produit inconnu"),
    ("cantu-leave-in;Amazon;http://a.example;;;", "https://"),
    ("cantu-leave-in;;https://a.example;;;", "marchand manquant"),
])
def test_bad_link_rows_are_explained(tmp_path, line, message):
    with pytest.raises(ValueError, match=message):
        catalog_with(tmp_path, HEADER + line + "\n")


@pytest.fixture
def with_links(tmp_path, monkeypatch):
    cat = catalog_with(tmp_path, LIENS)
    monkeypatch.setattr(main, "load_catalog", lambda: cat)
    monkeypatch.setattr(engine, "load_catalog", lambda: cat)
    monkeypatch.setattr(main, "clics", ClickCounter())
    return cat


def test_result_shows_buy_buttons_and_affiliate_notice(with_links):
    r = client.post("/diagnostic", data=FORM)
    assert "Acheter chez Amazon · 8,90 €" in r.text
    assert 'href="/acheter/cantu-leave-in--amazon"' in r.text
    assert 'rel="sponsored noopener nofollow"' in r.text
    assert "Lien affilié" in r.text and "peut toucher une commission" in r.text
    assert "n'est lié à aucune" not in r.text


def test_without_affiliate_links_the_old_notice_stays(tmp_path, monkeypatch):
    cat = catalog_with(tmp_path, HEADER)
    monkeypatch.setattr(engine, "load_catalog", lambda: cat)
    r = client.post("/diagnostic", data=FORM)
    assert "n'est lié à aucune de ces marques" in r.text
    assert "Acheter chez" not in r.text


def test_real_catalogue_has_amazon_links_with_partner_tag():
    for p in load_catalog():
        amazon = [o for o in p.offres if o.amazon]
        assert amazon, p.id
        assert all("tag=trichosens-21" in o.url and o.affilie and o.prix is None for o in amazon), p.id


def test_amazon_disclosure_and_search_label():
    r = client.post("/diagnostic", data=FORM)
    assert "En tant que Partenaire Amazon, TrichoSens réalise un bénéfice" in r.text
    assert "Voir sur Amazon" in r.text


def test_buy_link_counts_and_redirects(with_links):
    r = client.get("/acheter/cantu-leave-in--amazon", follow_redirects=False)
    assert r.status_code == 302
    assert r.headers["location"].startswith("https://www.amazon.fr/")
    assert main.clics.snapshot() == [("cantu-leave-in--amazon", 1)]
    assert client.get("/acheter/https:--evil.example", follow_redirects=False).status_code == 404


def test_stats_page_needs_the_admin_key(with_links, monkeypatch):
    monkeypatch.delenv("ADMIN_CLE", raising=False)
    assert client.get("/admin/clics", params={"cle": ""}).status_code == 404
    monkeypatch.setenv("ADMIN_CLE", "secret")
    assert client.get("/admin/clics", params={"cle": "faux"}).status_code == 404
    client.get("/acheter/cantu-leave-in--amazon", follow_redirects=False)
    r = client.get("/admin/clics", params={"cle": "secret"})
    assert r.status_code == 200 and "Amazon · affilié" in r.text


def test_awin_link_is_built_from_product_page_and_advertiser_id(tmp_path):
    cat = catalog_with(tmp_path, HEADER + "cantu-leave-in;Notino;https://www.notino.fr/cantu/leave-in/?a=1;;;;12345\n")
    o = next(p for p in cat if p.id == "cantu-leave-in").offres[0]
    assert o.affilie
    assert o.url == ("https://www.awin1.com/cread.php?awinmid=12345&awinaffid=2944635"
                     "&ued=https%3A%2F%2Fwww.notino.fr%2Fcantu%2Fleave-in%2F%3Fa%3D1")


def test_bad_awin_id_is_explained(tmp_path):
    with pytest.raises(ValueError, match="Awin"):
        catalog_with(tmp_path, HEADER + "cantu-leave-in;Notino;https://www.notino.fr/x;;;;abc\n")
