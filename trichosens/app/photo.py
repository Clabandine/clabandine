"""Analyse d'une photo de cheveux par l'IA (Claude, d'Anthropic).

La photo est traitée en mémoire puis oubliée : elle n'est jamais enregistrée.
La fonctionnalité n'est active que si la variable d'environnement
ANTHROPIC_API_KEY est définie.
"""

import base64
import io
import logging
import os
import threading
import time
from collections import defaultdict, deque
from typing import Literal

import anthropic
from PIL import Image, ImageOps, UnidentifiedImageError
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)

MODEL = "claude-opus-5-5"
MAX_UPLOAD_BYTES = 15 * 1024 * 1024
MAX_SIDE = 1568  # au-delà, l'API réduit l'image elle-même : inutile d'envoyer plus


def is_enabled() -> bool:
    return bool(os.environ.get("ANTHROPIC_API_KEY"))


# --- Format de la réponse de l'IA --------------------------------------------

SigneId = Literal[
    "secheresse", "frisottis", "pointes", "casse", "terne", "definition", "volume", "alourdis"
]


class Signe(BaseModel):
    signe: SigneId
    intensite: Literal["leger", "modere", "marque"]
    explication: str = Field(description="Ce qui est visible sur la photo, en une phrase.")


class AnalysePhoto(BaseModel):
    exploitable: bool = Field(description="La photo montre-t-elle assez bien les cheveux ?")
    conseil_photo: str | None = Field(
        description="Si la photo n'est pas exploitable : comment en prendre une meilleure."
    )
    type_cheveux: Literal[
        "1A", "1B", "1C", "2A", "2B", "2C", "3A", "3B", "3C", "4A", "4B", "4C"
    ] | None
    confiance_type: Literal["faible", "moyenne", "elevee"]
    epaisseur: Literal["fin", "moyen", "epais", "indetermine"]
    densite: Literal["faible", "moyenne", "forte", "indetermine"]
    signes: list[Signe]
    observations: list[str] = Field(description="2 à 4 phrases courtes sur l'état des cheveux.")
    alerte_medicale: str | None = Field(
        description="Seulement si un signe justifie un avis médical (zones sans cheveux, "
                    "rougeurs, squames importantes)."
    )


SYSTEM_PROMPT = """\
Vous êtes l'outil d'analyse photo de TrichoSens, une plateforme de conseil capillaire \
personnalisé. Une personne qui fait son diagnostic capillaire vous envoie une photo de ses \
cheveux. Votre analyse complète ses réponses au questionnaire et sert à lui recommander \
une routine de soins.

Observez uniquement les cheveux et, s'il est visible, le cuir chevelu. N'identifiez jamais \
la personne et ne commentez ni son visage, ni son apparence, ni son origine.

Types de cheveux :
- 1A : raides, fins, plats et très brillants ;
- 1B : raides, moyennement épais, avec un peu de corps ;
- 1C : raides et épais ;
- 2A : ondulations souples et lâches en S ;
- 2B : ondulations plus marquées, qui frisent avec l'humidité ;
- 2C : ondulations prononcées, proches de petites boucles ;
- 3A : boucles larges, souples et bien définies ;
- 3B : boucles plus serrées, en ressorts ou tire-bouchons ;
- 3C : boucles très serrées, denses et volumineuses ;
- 4A : petites boucles très serrées mais encore définies et rebondies ;
- 4B : motif en Z, vagues très anguleuses, peu de boucles définies ;
- 4C : frisure extrêmement serrée, sans boucle vraiment définie, très dense.

Soyez prudent et honnête : ne signalez que ce qui est visible. Si la photo est floue, trop \
sombre, prise de trop loin, ou ne montre pas de cheveux, indiquez qu'elle n'est pas \
exploitable et expliquez comment en prendre une meilleure. Les cheveux coiffés, mouillés \
ou attachés rendent le type plus difficile à juger : baissez alors votre niveau de confiance.

Vous ne posez pas de diagnostic médical. Si vous voyez des zones sans cheveux, des rougeurs \
ou des squames importantes, conseillez seulement un avis médical, sans nommer de maladie.

Écrivez en français, au vouvoiement, avec des phrases courtes, concrètes et bienveillantes."""


class PhotoError(Exception):
    """Erreur à afficher telle quelle à la personne."""


# --- Préparation de l'image ---------------------------------------------------


def prepare_image(data: bytes) -> str:
    """Vérifie, redresse et réduit l'image ; renvoie le JPEG encodé en base64."""
    if len(data) > MAX_UPLOAD_BYTES:
        raise PhotoError("La photo est trop lourde (15 Mo maximum).")
    try:
        img = Image.open(io.BytesIO(data))
        img = ImageOps.exif_transpose(img)
        img = img.convert("RGB")
    except (UnidentifiedImageError, OSError, Image.DecompressionBombError):
        raise PhotoError("Ce fichier n'est pas une image lisible. Essayez une photo JPEG ou PNG.")
    img.thumbnail((MAX_SIDE, MAX_SIDE))
    out = io.BytesIO()
    img.save(out, format="JPEG", quality=85)
    return base64.standard_b64encode(out.getvalue()).decode("ascii")


# --- Limite d'utilisation (chaque analyse a un coût) --------------------------


class RateLimiter:
    def __init__(self, per_ip_per_hour: int, per_day: int):
        self.per_ip_per_hour = per_ip_per_hour
        self.per_day = per_day
        self._ip: dict[str, deque] = defaultdict(deque)
        self._day: deque = deque()
        self._lock = threading.Lock()

    def check(self, ip: str) -> None:
        now = time.time()
        with self._lock:
            hits = self._ip[ip]
            while hits and now - hits[0] > 3600:
                hits.popleft()
            while self._day and now - self._day[0] > 86400:
                self._day.popleft()
            if len(self._day) >= self.per_day:
                raise PhotoError("L'analyse photo est très demandée aujourd'hui. "
                                 "Réessayez demain, ou continuez sans photo.")
            if len(hits) >= self.per_ip_per_hour:
                raise PhotoError("Vous avez atteint la limite d'analyses pour cette heure. "
                                 "Réessayez plus tard, ou continuez sans photo.")
            hits.append(now)
            self._day.append(now)


limiter = RateLimiter(
    per_ip_per_hour=int(os.environ.get("PHOTO_MAX_PAR_HEURE", "5")),
    per_day=int(os.environ.get("PHOTO_MAX_PAR_JOUR", "200")),
)


# --- Appel à l'IA -------------------------------------------------------------

_client: anthropic.Anthropic | None = None


def get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic(timeout=90, max_retries=2)
    return _client


def analyse(image_b64: str, client: anthropic.Anthropic | None = None) -> AnalysePhoto:
    client = client or get_client()
    try:
        response = client.beta.messages.parse(
            model=MODEL,
            max_tokens=8000,
            # Si le modèle décline la demande, l'API la relance sur un autre modèle.
            betas=["server-side-fallback-2026-07-01"],
            fallbacks="default",
            output_config={"effort": "medium"},
            output_format=AnalysePhoto,
            system=SYSTEM_PROMPT,
            messages=[{
                "role": "user",
                "content": [
                    {"type": "image",
                     "source": {"type": "base64", "media_type": "image/jpeg", "data": image_b64}},
                    {"type": "text", "text": "Voici la photo de mes cheveux. Analysez-la."},
                ],
            }],
        )
    except anthropic.RateLimitError:
        raise PhotoError("Le service d'analyse est saturé. Réessayez dans une minute.")
    except anthropic.APIStatusError as e:
        log.error("Erreur API Anthropic %s : %s", e.status_code, e.message)
        raise PhotoError("L'analyse n'a pas pu aboutir. Réessayez, ou continuez sans photo.")
    except anthropic.APIConnectionError:
        log.exception("Connexion à l'API Anthropic impossible")
        raise PhotoError("Le service d'analyse ne répond pas. Réessayez, ou continuez sans photo.")

    if response.stop_reason == "refusal" or response.parsed_output is None:
        log.warning("Analyse photo sans résultat (stop_reason=%s)", response.stop_reason)
        raise PhotoError("Cette photo n'a pas pu être analysée. Essayez avec une autre photo "
                         "qui montre seulement vos cheveux.")
    return response.parsed_output
