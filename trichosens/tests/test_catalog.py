import pytest

from app.catalog import CATEGORIES, load_catalog, parse_product, parse_types
from app.hair_types import HAIR_TYPES

ROW = {
    "id": "test", "marque": "Marque", "nom": "Produit", "categorie": "masque",
    "description": "", "besoins": "hydratation", "poids": "moyen", "types": "3A-4C",
    "cuir_chevelu": "", "sans_parfum": "", "sans_sulfates": "oui", "sans_silicones": "",
    "vegan": "non", "saisons": "été|hiver", "prix_indicatif": "12,50", "contenance": "",
    "ingredients_cles": "", "a_verifier": "oui",
}


def test_type_ranges():
    assert parse_types("3A-4C") == ("3A", "3B", "3C", "4A", "4B", "4C")
    assert parse_types("1a|4C") == ("1A", "4C")
    assert parse_types("") == ()
    assert parse_types("tous") == ()
    with pytest.raises(ValueError):
        parse_types("5A")


def test_parse_row():
    p = parse_product(ROW)
    assert p.types[0] == "3A" and p.prix == 12.5
    assert p.saisons == ("ete", "hiver")
    assert p.sans_sulfates is True and p.vegan is False and p.sans_parfum is None
    assert p.labels == ["Sans sulfates"]


def test_invalid_row_is_explained():
    with pytest.raises(ValueError, match="catégorie inconnue"):
        parse_product({**ROW, "categorie": "parfum"})


def test_real_catalogue_is_complete():
    catalog = load_catalog()
    assert len(catalog) >= 40
    assert {p.categorie for p in catalog} == set(CATEGORIES)
    for code in HAIR_TYPES:
        for cat in ("shampoing", "masque", "leave_in", "huile"):
            assert any(p.categorie == cat and (not p.types or code in p.types) for p in catalog), (code, cat)
