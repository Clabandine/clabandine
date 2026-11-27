"""Inscriptions facultatives aux conseils et rappels par e-mail.

Chaque consentement est distinct : conseils et rappels TrichoSens (obligatoire pour
s'inscrire), personnalisation selon le type de cheveux, offres des marques partenaires.
On garde la date et la version du texte accepté, comme preuve du consentement. Les
e-mails eux-mêmes s'envoient avec un outil dédié (Brevo par exemple), à partir de
l'export CSV de l'espace admin.
"""

import csv
import datetime as dt
import io
import logging
import os
import re
from dataclasses import dataclass

from .hair_types import HAIR_TYPES
from .partenaires import Limiteur

log = logging.getLogger("trichosens.inscriptions")

EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[A-Za-z]{2,}$")
VERSION_CONSENTEMENT = "2026-11-27"


class InscriptionInvalide(ValueError):
    pass


@dataclass
class Inscription:
    email: str
    conseils: bool
    partenaires: bool
    type_cheveux: str = ""
    cree_le: dt.datetime | None = None
    version: str = VERSION_CONSENTEMENT


def valider(data: dict) -> Inscription:
    email = " ".join(str(data.get("email") or "").split()).lower()[:120]
    if not EMAIL_RE.match(email):
        raise InscriptionInvalide("Indiquez une adresse e-mail valide.")
    if data.get("conseils") not in (True, "oui", "on"):
        raise InscriptionInvalide("Cochez la case pour recevoir les conseils et rappels.")
    type_cheveux = str(data.get("type_cheveux") or "")
    return Inscription(
        email=email, conseils=True,
        partenaires=data.get("partenaires") in (True, "oui", "on"),
        type_cheveux=type_cheveux if type_cheveux in HAIR_TYPES else "",
    )


class Memoire:
    persistant = False

    def __init__(self) -> None:
        self.inscrits: dict[str, Inscription] = {}

    def ajouter(self, i: Inscription) -> None:
        self.inscrits[i.email] = i  # une nouvelle inscription remplace l'ancienne

    def retirer(self, email: str) -> bool:
        return self.inscrits.pop(email, None) is not None

    def lister(self) -> list[Inscription]:
        return sorted(self.inscrits.values(), key=lambda i: i.cree_le, reverse=True)


class BaseSQL:
    persistant = True
    CREATION = (
        "CREATE TABLE IF NOT EXISTS inscriptions ("
        " email TEXT PRIMARY KEY, conseils BOOLEAN NOT NULL, partenaires BOOLEAN NOT NULL,"
        " type_cheveux TEXT NOT NULL DEFAULT '', cree_le TEXT NOT NULL, version TEXT NOT NULL)"
    )

    def __init__(self, connecter, marque: str = "%s") -> None:
        self._connecter, self._m = connecter, marque
        with self._connecter() as conn:
            conn.execute(self.CREATION)
            conn.commit()

    def ajouter(self, i: Inscription) -> None:
        m = self._m
        with self._connecter() as conn:
            conn.execute(
                "INSERT INTO inscriptions (email, conseils, partenaires, type_cheveux, cree_le, version)"
                f" VALUES ({m}, {m}, {m}, {m}, {m}, {m}) ON CONFLICT (email) DO UPDATE SET"
                " conseils = excluded.conseils, partenaires = excluded.partenaires,"
                " type_cheveux = excluded.type_cheveux, cree_le = excluded.cree_le,"
                " version = excluded.version",
                (i.email, i.conseils, i.partenaires, i.type_cheveux, i.cree_le.isoformat(), i.version))
            conn.commit()

    def retirer(self, email: str) -> bool:
        with self._connecter() as conn:
            n = conn.execute(f"DELETE FROM inscriptions WHERE email = {self._m}", (email,)).rowcount
            conn.commit()
        return bool(n)

    def lister(self) -> list[Inscription]:
        with self._connecter() as conn:
            lignes = conn.execute(
                "SELECT email, conseils, partenaires, type_cheveux, cree_le, version FROM inscriptions"
                " ORDER BY cree_le DESC").fetchall()
        return [Inscription(email=e, conseils=bool(c), partenaires=bool(p), type_cheveux=t,
                            cree_le=dt.datetime.fromisoformat(d), version=v)
                for e, c, p, t, d, v in lignes]


def _creer():
    url = os.environ.get("DATABASE_URL", "").strip()
    if url:
        try:
            import psycopg

            return BaseSQL(lambda: psycopg.connect(url, connect_timeout=10))
        except Exception as e:
            log.error("Base injoignable, inscriptions en mémoire : %s", e)
    return Memoire()


stockage = _creer()
limiteur = Limiteur(par_heure=5)


def inscrire(i: Inscription) -> None:
    i.cree_le = dt.datetime.now(dt.timezone.utc)
    stockage.ajouter(i)


def export_csv() -> str:
    """Pour importer les contacts dans l'outil d'envoi d'e-mails (Brevo, Mailchimp…)."""
    sortie = io.StringIO()
    w = csv.writer(sortie, delimiter=";")
    w.writerow(["email", "conseils", "offres_partenaires", "type_cheveux", "inscrit_le", "version_consentement"])
    for i in stockage.lister():
        w.writerow([i.email, "oui", "oui" if i.partenaires else "non", i.type_cheveux,
                    i.cree_le.isoformat(timespec="seconds"), i.version])
    return sortie.getvalue()
