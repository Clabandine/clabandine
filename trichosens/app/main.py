"""Application web TrichoSens.

Lancer en local :  uvicorn app.main:app --reload   (depuis le dossier trichosens/)
"""

from pathlib import Path

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from .catalog import CATEGORIES
from .engine import MOMENTS, NEEDS, run_diagnostic
from .questionnaire import QUESTIONS, InvalidAnswers, validate

BASE_DIR = Path(__file__).parent

app = FastAPI(
    title="TrichoSens",
    description="Comprendre ses cheveux. Trouver les bons soins. Révéler leur potentiel.",
    version="0.1.0",
)
app.mount("/static", StaticFiles(directory=BASE_DIR / "static"), name="static")
templates = Jinja2Templates(directory=BASE_DIR / "templates")
templates.env.globals.update(NEEDS=NEEDS, MOMENTS=MOMENTS, CATEGORIES=CATEGORIES)


@app.get("/sante", include_in_schema=False)
def sante():
    """Utilisé par l'hébergeur pour vérifier que le site répond."""
    return {"statut": "ok"}


# --- Pages -------------------------------------------------------------------


@app.get("/", response_class=HTMLResponse)
def accueil(request: Request):
    return templates.TemplateResponse(request, "index.html")


@app.get("/diagnostic", response_class=HTMLResponse)
def diagnostic_form(request: Request):
    return templates.TemplateResponse(
        request, "diagnostic.html", {"questions": QUESTIONS, "answers": {}, "errors": {}}
    )


@app.post("/diagnostic", response_class=HTMLResponse)
async def diagnostic_submit(request: Request):
    form = await request.form()
    raw = {q.id: form.getlist(q.id) if q.multiple else form.get(q.id) for q in QUESTIONS}
    try:
        answers = validate(raw)
    except InvalidAnswers as e:
        return templates.TemplateResponse(
            request,
            "diagnostic.html",
            {"questions": QUESTIONS, "answers": raw, "errors": e.errors},
            status_code=422,
        )
    return templates.TemplateResponse(
        request, "resultat.html", {"d": run_diagnostic(answers)}
    )


# --- API JSON (pour une future application mobile ou des partenaires) ---------


@app.get("/api/questions")
def api_questions():
    return [
        {
            "id": q.id,
            "label": q.label,
            "help": q.help,
            "multiple": q.multiple,
            "required": q.required,
            "max_choices": q.max_choices,
            "options": [{"value": o.value, "label": o.label, "hint": o.hint} for o in q.options],
        }
        for q in QUESTIONS
    ]


@app.post("/api/diagnostic")
def api_diagnostic(payload: dict):
    try:
        answers = validate(payload)
    except InvalidAnswers as e:
        raise HTTPException(status_code=422, detail=e.errors)
    return run_diagnostic(answers).to_dict()
