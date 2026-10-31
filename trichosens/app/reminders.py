"""Rappels de routine : fichier agenda (.ics) à importer dans le téléphone.

Pas besoin de compte ni de serveur de notifications : les rappels vivent dans
l'agenda de la personne (Calendrier sur iPhone, Google Agenda sur Android…).
"""

import datetime as dt
import uuid

JOURS = {"MO": "Lundi", "TU": "Mardi", "WE": "Mercredi", "TH": "Jeudi", "FR": "Vendredi",
         "SA": "Samedi", "SU": "Dimanche"}
JOURS_ORDRE = list(JOURS)  # lundi = 0, comme date.weekday()

RAPPELS = {
    "lavage": "Jours de lavage",
    "clarifiant": "Shampoing clarifiant (1 fois par mois)",
    "pousse": "Mesure de la mèche témoin (1 fois par mois)",
    "coupe": "Coupe des pointes (tous les 3 mois)",
    "diagnostic": "Prochain diagnostic",
}


def jours_suggeres(lavages_par_semaine: float) -> list[str]:
    """Jours de lavage proposés par défaut, répartis dans la semaine."""
    if lavages_par_semaine >= 4:
        return ["MO", "WE", "FR", "SU"]
    if lavages_par_semaine >= 3:
        return ["MO", "WE", "FR"]
    if lavages_par_semaine >= 2:
        return ["WE", "SU"]
    return ["SU"]


def _escape(text: str) -> str:
    return (text.replace("\\", "\\\\").replace(";", "\\;").replace(",", "\\,")
            .replace("\n", "\\n"))


def _fold(line: str) -> str:
    """Coupe les lignes trop longues (75 octets max, norme iCalendar)."""
    out, current = [], b""
    for ch in line:
        b = ch.encode("utf-8")
        if len(current) + len(b) > 74:
            out.append(current.decode("utf-8"))
            current = b" " + b
        else:
            current += b
    out.append(current.decode("utf-8"))
    return "\r\n".join(out)


def _prochain(jour: dt.date, codes: list[str]) -> dt.date:
    """Première date, à partir de demain, qui tombe un des jours choisis."""
    wanted = {JOURS_ORDRE.index(c) for c in codes}
    d = jour + dt.timedelta(days=1)
    while d.weekday() not in wanted:
        d += dt.timedelta(days=1)
    return d


def _premier_du_mois(jour: dt.date, code: str) -> dt.date:
    """Premier <jour de la semaine> d'un mois, à partir de demain."""
    wd = JOURS_ORDRE.index(code)
    y, m = jour.year, jour.month
    while True:
        d = dt.date(y, m, 1)
        d += dt.timedelta(days=(wd - d.weekday()) % 7)
        if d > jour:
            return d
        y, m = (y + 1, 1) if m == 12 else (y, m + 1)


def _event(summary: str, description: str, start: dt.datetime, rrule: str | None,
           url: str, now: dt.datetime) -> list[str]:
    lines = [
        "BEGIN:VEVENT",
        f"UID:{uuid.uuid4()}@trichosens",
        f"DTSTAMP:{now.strftime('%Y%m%dT%H%M%SZ')}",
        # Heure « flottante » : l'agenda l'interprète dans le fuseau du téléphone.
        f"DTSTART:{start.strftime('%Y%m%dT%H%M%S')}",
        f"DTEND:{(start + dt.timedelta(minutes=30)).strftime('%Y%m%dT%H%M%S')}",
        f"SUMMARY:{_escape(summary)}",
        f"DESCRIPTION:{_escape(description)}",
    ]
    if url:
        lines.append(f"URL:{url}")
    if rrule:
        lines.append(f"RRULE:{rrule}")
    lines += [
        "BEGIN:VALARM",
        "ACTION:DISPLAY",
        f"DESCRIPTION:{_escape(summary)}",
        "TRIGGER:PT0M",
        "END:VALARM",
        "END:VEVENT",
    ]
    return lines


def build_ics(*, jours: list[str], heure: dt.time, rappels: list[str], masque: str,
              prochain_point: dt.date | None, type_cheveux: str, site_url: str,
              today: dt.date | None = None) -> str:
    today = today or dt.date.today()
    now = dt.datetime.now(dt.timezone.utc)
    jours = [j for j in JOURS_ORDRE if j in jours] or ["SU"]
    premier = _prochain(today, jours)
    debut = dt.datetime.combine(premier, heure)
    events: list[str] = []
    # Rappels mensuels : premier <jour de lavage> du mois.
    mois_a, mois_b = jours[0], jours[-1]

    if "lavage" in rappels:
        soin = ("Masque 1 lavage sur 2, après-shampoing les autres fois."
                if masque == "alterne" else "Masque à chaque lavage.")
        events += _event(
            "TrichoSens · Jour de lavage",
            f"Votre routine de lavage (type {type_cheveux}). {soin} "
            "Détails : votre dernier résultat TrichoSens.",
            debut, f"FREQ=WEEKLY;BYDAY={','.join(jours)}", site_url + "/suivi", now)
    if "clarifiant" in rappels:
        events += _event(
            "TrichoSens · Shampoing clarifiant",
            "Une fois par mois, un shampoing clarifiant enlève les résidus de produits.",
            dt.datetime.combine(_premier_du_mois(today, mois_a), heure),
            f"FREQ=MONTHLY;BYDAY=1{mois_a}", site_url, now)
    if "pousse" in rappels:
        events += _event(
            "TrichoSens · Mesure de la mèche témoin",
            "Mesurez votre mèche témoin et notez-la dans « Mon suivi ».",
            dt.datetime.combine(_premier_du_mois(today, mois_b), heure),
            f"FREQ=MONTHLY;BYDAY=1{mois_b}", site_url + "/suivi", now)
    if "coupe" in rappels:
        coupe = dt.datetime.combine(today + dt.timedelta(days=90), heure)
        events += _event(
            "TrichoSens · Coupe des pointes",
            "Pensez à faire couper vos pointes abîmées.",
            coupe, "FREQ=MONTHLY;INTERVAL=3", site_url, now)
    if "diagnostic" in rappels and prochain_point:
        events += _event(
            "TrichoSens · Refaire mon diagnostic",
            "C'est le moment de faire le point : refaites votre diagnostic pour suivre "
            "l'évolution de vos cheveux et adapter votre routine.",
            dt.datetime.combine(prochain_point, heure), None, site_url + "/diagnostic", now)

    lines = ["BEGIN:VCALENDAR", "VERSION:2.0", "PRODID:-//TrichoSens//Rappels//FR",
             "CALSCALE:GREGORIAN", "METHOD:PUBLISH", "X-WR-CALNAME:TrichoSens",
             *events, "END:VCALENDAR"]
    return "\r\n".join(_fold(line) for line in lines) + "\r\n"
