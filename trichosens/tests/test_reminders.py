import datetime as dt
import re

from fastapi.testclient import TestClient

from app.main import app
from app.reminders import build_ics, jours_suggeres

client = TestClient(app)
TODAY = dt.date(2026, 10, 31)  # un samedi


def ics(**overrides):
    params = dict(jours=["WE", "SU"], heure=dt.time(19, 0),
                  rappels=["lavage", "clarifiant", "pousse", "coupe", "diagnostic"],
                  masque="chaque", prochain_point=dt.date(2026, 11, 28), type_cheveux="3B",
                  site_url="https://trichosens.example", today=TODAY)
    return build_ics(**{**params, **overrides})


def test_calendar_structure():
    text = ics()
    assert text.startswith("BEGIN:VCALENDAR\r\n") and text.endswith("END:VCALENDAR\r\n")
    assert text.count("BEGIN:VEVENT") == 5 == text.count("END:VEVENT")
    assert text.count("BEGIN:VALARM") == 5
    assert all(len(line.encode()) <= 75 for line in text.split("\r\n"))


def test_wash_days_repeat_weekly_from_next_chosen_day():
    text = ics(rappels=["lavage"])
    assert "RRULE:FREQ=WEEKLY;BYDAY=WE,SU" in text
    assert "DTSTART:20261101T190000" in text  # dimanche 1er novembre


def test_next_diagnostic_is_a_single_event():
    text = ics(rappels=["diagnostic"])
    assert "DTSTART:20261128T190000" in text and "RRULE" not in text


def test_maintenance_phase_mentions_alternate_mask():
    unfolded = ics(rappels=["lavage"], masque="alterne").replace("\r\n ", "")
    assert "Masque 1 lavage sur 2" in unfolded


def test_suggested_days():
    assert jours_suggeres(1) == ["SU"]
    assert jours_suggeres(2.5) == ["WE", "SU"]
    assert len(jours_suggeres(4)) == 4


def test_endpoint_returns_calendar_file():
    r = client.get("/rappels.ics", params={"jours": ["MO", "TH"], "heure": "08:30",
                                           "rappels": ["lavage", "diagnostic"],
                                           "prochain": "2026-12-01", "type_cheveux": "4C"})
    assert r.status_code == 200
    assert r.headers["content-type"].startswith("text/calendar")
    assert "attachment" in r.headers["content-disposition"]
    assert "BYDAY=MO,TH" in r.text and "T083000" in r.text


def test_endpoint_rejects_bad_input():
    assert client.get("/rappels.ics", params={"rappels": ["lavage"], "jours": ["XX"]}).status_code == 422
    assert client.get("/rappels.ics", params={"rappels": ["lavage"], "heure": "25:99"}).status_code == 422
    assert client.get("/rappels.ics").status_code == 422


def test_result_page_offers_reminders():
    form = {"type_cheveux": "4C", "epaisseur": "fin", "densite": "forte", "porosite": "forte",
            "cuir_chevelu": "sec", "preoccupations": ["secheresse"], "gene_secheresse": "beaucoup",
            "chaleur": "jamais", "objectif": "hydratation"}
    r = client.post("/diagnostic", data=form)
    assert "Ajouter à mon agenda" in r.text
    assert re.search(r'name="jours" value="SU"\s+checked', r.text)  # 4C : lavage le dimanche


def test_monthly_reminders_start_on_a_matching_day():
    text = ics(rappels=["clarifiant", "pousse"])
    assert "DTSTART:20261104T190000" in text and "BYDAY=1WE" in text  # 1er mercredi de novembre
    assert "DTSTART:20261101T190000" in text and "BYDAY=1SU" in text  # 1er dimanche de novembre
