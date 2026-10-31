"""Application web TrichoSens.

Lancer en local :  uvicorn app.main:app --reload   (depuis le dossier trichosens/)
"""

import datetime as dt
import logging
import os
from pathlib import Path

from fastapi import FastAPI, File, Form, HTTPException, Query, Request, UploadFile
from fastapi.responses import HTMLResponse, JSONResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pydantic import ValidationError
from starlette.concurrency import run_in_threadpool

from . import photo as photo_ai
from .catalog import CATEGORIES
from .engine import MOMENTS, NEEDS, PHASES, run_diagnostic
from .evolution import TENDANCE_LABEL, ResumeSuivi
from .hair_types import FAMILLES, HAIR_TYPES
from .pain_points import INTENSITES, PAIN_POINTS
from .questionnaire import QUESTIONS, STEPS, InvalidAnswers, validate
from .reminders import JOURS, RAPPELS, build_ics

logging.basicConfig(level=logging.INFO)

BASE_DIR = Path(__file__).parent
# Questionnaire d'avis des testeurs (modifiable avec la variable d'environnement AVIS_URL).
AVIS_URL = os.environ.get(
    "AVIS_URL",
    "https://docs.google.com/forms/d/e/1FAIpQLSe5vH5uiouUbUPDXzPx-1ez6kIwnHbCByc8VU3u0stc92FnTw/viewform",
)
STATIC_DIR = BASE_DIR / "static"

app = FastAPI(
    title="TrichoSens",
    description="Comprendre ses cheveux. Trouver les bons soins. Révéler leur potentiel.",
    version="0.2.0",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")


def visuel(name: str) -> str:
    """Adresse de l'image d'une réponse : la photo si elle existe, sinon l'illustration."""
    for ext in ("jpg", "jpeg", "webp", "png"):
        if (STATIC_DIR / "img" / "photos" / f"{name}.{ext}").exists():
            return f"/static/img/photos/{name}.{ext}"
    return f"/static/img/illustrations/{name}.svg"


templates.env.globals.update(
    NEEDS=NEEDS, MOMENTS=MOMENTS, CATEGORIES=CATEGORIES, INTENSITES=INTENSITES, visuel=visuel,
    FAMILLES=FAMILLES, AVIS_URL=AVIS_URL,
    PAIN_LABELS={pid: p.label for pid, p in PAIN_POINTS.items()},
    JOURS=JOURS, RAPPELS=RAPPELS, PHASES=PHASES, TENDANCE_LABEL=TENDANCE_LABEL,
)


@app.get("/sante", include_in_schema=False)
def sante():
    """Utilisé par l'hébergeur pour vérifier que le site répond."""
    return {"statut": "ok"}


# --- Pages -------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def accueil(request: Request):
    return templates.TemplateResponse(request, "index.html")


def _form_context(answers: dict, errors: dict) -> dict:
    return {
        "steps": STEPS,
        "questions": QUESTIONS,
        "answers": answers,
        "errors": errors,
        "photo_active": photo_ai.is_enabled(),
    }


@app.get("/diagnostic", response_class=HTMLResponse)
def diagnostic_form(request: Request):
    return templates.TemplateResponse(request, "diagnostic.html", _form_context({}, {}))


def _parse_photo(raw: str | None) -> photo_ai.AnalysePhoto | None:
    """Relit l'analyse photo renvoyée par le navigateur ; l'ignore si elle est invalide."""
    if not raw:
        return None
    try:
        return photo_ai.AnalysePhoto.model_validate_json(raw)
    except ValidationError:
        return None


def _parse_precedent(raw: str | None) -> ResumeSuivi | None:
    """Relit le résumé du diagnostic précédent envoyé par le navigateur."""
    if not raw:
        return None
    try:
        return ResumeSuivi.model_validate_json(raw)
    except ValidationError:
        return None


@app.get("/rappels.ics")
def rappels_ics(
    request: Request,
    jours: list[str] = Query(default=[]),
    heure: str = "19:00",
    rappels: list[str] = Query(default=[]),
    masque: str = "chaque",
    prochain: str = "",
    type_cheveux: str = "",
):
    """Fichier agenda avec les rappels de routine choisis."""
    try:
        h = dt.time.fromisoformat(heure)
        prochain_point = dt.date.fromisoformat(prochain) if prochain else None
    except ValueError:
        raise HTTPException(status_code=422, detail="Heure ou date invalide.")
    if (set(jours) - set(JOURS) or set(rappels) - set(RAPPELS)
            or masque not in {"chaque", "alterne"}
            or (type_cheveux and type_cheveux not in HAIR_TYPES)):
        raise HTTPException(status_code=422, detail="Paramètres de rappel invalides.")
    if not rappels:
        raise HTTPException(status_code=422, detail="Choisissez au moins un rappel.")
    site = str(request.base_url).rstrip("/")
    ics = build_ics(jours=jours, heure=h, rappels=rappels, masque=masque,
                    prochain_point=prochain_point, type_cheveux=type_cheveux or "?",
                    site_url=site)
    return Response(ics, media_type="text/calendar; charset=utf-8",
                    headers={"Content-Disposition": 'attachment; filename="trichosens-rappels.ics"'})


@app.get("/suivi", response_class=HTMLResponse)
def suivi(request: Request):
    return templates.TemplateResponse(request, "suivi.html")


@app.post("/diagnostic", response_class=HTMLResponse)
async def diagnostic_submit(request: Request):
    form = await request.form()
    raw: dict = {q.id: form.getlist(q.id) if q.multiple else form.get(q.id) for q in QUESTIONS}
    raw["intensites"] = {
        pid: form.get(f"gene_{pid}") for pid in form.getlist("preoccupations")
    }
    photo_json = form.get("analyse_photo") or ""
    precedent_json = form.get("precedent") or ""
    try:
        answers = validate(raw)
    except InvalidAnswers as e:
        ctx = _form_context(raw, e.errors)
        ctx["photo_json"] = photo_json
        return templates.TemplateResponse(request, "diagnostic.html", ctx, status_code=422)
    diagnostic = run_diagnostic(answers, photo=_parse_photo(photo_json),
                                precedent=_parse_precedent(precedent_json))
    return templates.TemplateResponse(request, "resultat.html", {"d": diagnostic})


# --- API JSON (pour le formulaire, une future application mobile ou des partenaires) ---


def _client_ip(request: Request) -> str:
    # Derrière l'hébergeur, la vraie adresse est la première de X-Forwarded-For.
    forwarded = request.headers.get("x-forwarded-for")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "inconnue"


@app.post("/api/analyse-photo")
async def api_analyse_photo(
    request: Request,
    photo: UploadFile = File(...),
    consentement: str = Form(""),
):
    if not photo_ai.is_enabled():
        raise HTTPException(status_code=503, detail="L'analyse photo n'est pas disponible.")
    if consentement != "oui":
        raise HTTPException(status_code=400, detail="Merci d'accepter l'analyse de votre photo.")
    try:
        data = await photo.read(photo_ai.MAX_UPLOAD_BYTES + 1)
        image_b64 = photo_ai.prepare_image(data)
        photo_ai.limiter.check(_client_ip(request))
        # L'appel à l'IA est bloquant : on le lance dans un fil séparé.
        result = await run_in_threadpool(photo_ai.analyse, image_b64)
    except photo_ai.PhotoError as e:
        return JSONResponse(status_code=422, content={"detail": str(e)})
    return result.model_dump()


@app.get("/api/questions")
def api_questions():
    return {
        "etapes": [{"id": s.id, "titre": s.titre, "intro": s.intro} for s in STEPS],
        "intensites": INTENSITES,
        "familles": [{"id": f.id, "titre": f.titre, "label": f.label, "image": visuel(f.visuel)}
                     for f in FAMILLES.values()],
        "questions": [
            {
                "id": q.id,
                "etape": q.step,
                "label": q.label,
                "help": q.help,
                "multiple": q.multiple,
                "required": q.required,
                "max_choices": q.max_choices,
                "options": [
                    {"value": o.value, "label": o.label, "hint": o.hint,
                     "image": visuel(o.visuel) if o.visuel else None,
                     "famille": o.groupe or None}
                    for o in q.options
                ],
            }
            for q in QUESTIONS
        ],
    }


@app.post("/api/diagnostic")
def api_diagnostic(payload: dict):
    try:
        answers = validate(payload)
    except InvalidAnswers as e:
        raise HTTPException(status_code=422, detail=e.errors)
    photo = None
    if payload.get("photo"):
        try:
            photo = photo_ai.AnalysePhoto.model_validate(payload["photo"])
        except ValidationError as e:
            raise HTTPException(status_code=422, detail={"photo": str(e)})
    precedent = None
    if payload.get("precedent"):
        try:
            precedent = ResumeSuivi.model_validate(payload["precedent"])
        except ValidationError as e:
            raise HTTPException(status_code=422, detail={"precedent": str(e)})
    return run_diagnostic(answers, photo=photo, precedent=precedent).to_dict()
