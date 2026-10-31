"""Comptage des clics sur les liens d'achat.

Aucune donnée personnelle : on compte seulement combien de fois chaque lien est
cliqué. Les compteurs sont gardés en mémoire : ils repartent à zéro quand le site
redémarre (mise à jour, mise en veille de l'offre gratuite). Chaque clic est aussi
écrit dans les journaux (logs) de l'hébergeur. Pour les ventes et les commissions,
les tableaux de bord des programmes d'affiliation font foi.
"""

import datetime as dt
import logging
import threading
from collections import Counter

log = logging.getLogger("trichosens.clics")


class ClickCounter:
    def __init__(self) -> None:
        self._counts: Counter[str] = Counter()
        self._lock = threading.Lock()
        self.depuis = dt.datetime.now(dt.timezone.utc)

    def add(self, offre_id: str) -> None:
        with self._lock:
            self._counts[offre_id] += 1
        log.info("clic %s", offre_id)

    def snapshot(self) -> list[tuple[str, int]]:
        with self._lock:
            return self._counts.most_common()


counter = ClickCounter()
