import io
import json
from types import SimpleNamespace

import pytest
from fastapi.testclient import TestClient
from PIL import Image

from app import photo as photo_ai
from app.main import app

client = TestClient(app)

ANALYSE = {
    "exploitable": True, "conseil_photo": None, "texture": "frise", "confiance_texture": "elevee",
    "epaisseur": "fin", "densite": "forte",
    "signes": [{"signe": "secheresse", "intensite": "modere", "explication": "Pointes sèches."}],
    "observations": ["Vos boucles sont serrées et un peu sèches."], "alerte_medicale": None,
}


def jpeg_bytes(size=(3000, 2000)) -> bytes:
    out = io.BytesIO()
    Image.new("RGB", size, (90, 60, 40)).save(out, format="JPEG")
    return out.getvalue()


def test_prepare_image_resizes_large_photos():
    import base64
    b64 = photo_ai.prepare_image(jpeg_bytes())
    img = Image.open(io.BytesIO(base64.b64decode(b64)))
    assert max(img.size) == photo_ai.MAX_SIDE


def test_prepare_image_rejects_non_images():
    with pytest.raises(photo_ai.PhotoError):
        photo_ai.prepare_image(b"ceci n'est pas une image")


def test_rate_limiter_blocks_after_limit():
    limiter = photo_ai.RateLimiter(per_ip_per_hour=2, per_day=100)
    limiter.check("1.1.1.1")
    limiter.check("1.1.1.1")
    with pytest.raises(photo_ai.PhotoError):
        limiter.check("1.1.1.1")
    limiter.check("2.2.2.2")  # une autre personne n'est pas bloquée


class FakeMessages:
    def __init__(self, stop_reason="end_turn", parsed=None):
        self.stop_reason = stop_reason
        self.parsed = parsed
        self.kwargs = None

    def parse(self, **kwargs):
        self.kwargs = kwargs
        return SimpleNamespace(stop_reason=self.stop_reason, parsed_output=self.parsed)


def fake_client(**kw):
    messages = FakeMessages(**kw)
    return SimpleNamespace(beta=SimpleNamespace(messages=messages)), messages


def test_analyse_sends_image_and_returns_result():
    result = photo_ai.AnalysePhoto.model_validate(ANALYSE)
    c, messages = fake_client(parsed=result)
    assert photo_ai.analyse("abc", client=c) is result
    assert messages.kwargs["output_format"] is photo_ai.AnalysePhoto
    assert messages.kwargs["fallbacks"] == "default"
    image = messages.kwargs["messages"][0]["content"][0]
    assert image["type"] == "image" and image["source"]["data"] == "abc"


def test_analyse_handles_refusal():
    c, _ = fake_client(stop_reason="refusal", parsed=None)
    with pytest.raises(photo_ai.PhotoError):
        photo_ai.analyse("abc", client=c)


def test_photo_step_hidden_without_api_key(monkeypatch):
    monkeypatch.delenv("ANTHROPIC_API_KEY", raising=False)
    assert 'id="photo-input"' not in client.get("/diagnostic").text
    r = client.post("/api/analyse-photo", files={"photo": ("p.jpg", jpeg_bytes(), "image/jpeg")},
                    data={"consentement": "oui"})
    assert r.status_code == 503


def test_photo_endpoint(monkeypatch):
    monkeypatch.setenv("ANTHROPIC_API_KEY", "test")
    monkeypatch.setattr(photo_ai, "limiter", photo_ai.RateLimiter(10, 100))
    monkeypatch.setattr(photo_ai, "analyse",
                        lambda b64: photo_ai.AnalysePhoto.model_validate(ANALYSE))
    assert 'id="photo-input"' in client.get("/diagnostic").text

    files = {"photo": ("p.jpg", jpeg_bytes(), "image/jpeg")}
    assert client.post("/api/analyse-photo", files=files).status_code == 400  # sans consentement
    r = client.post("/api/analyse-photo", files=files, data={"consentement": "oui"})
    assert r.status_code == 200
    assert r.json()["texture"] == "frise"


def test_form_with_photo_analysis_shows_it():
    form = {
        "texture": "frise", "epaisseur": "fin", "densite": "forte", "porosite": "forte",
        "cuir_chevelu": "sec", "preoccupations": ["secheresse"], "gene_secheresse": "beaucoup",
        "chaleur": "jamais", "objectif": "hydratation", "analyse_photo": json.dumps(ANALYSE),
    }
    r = client.post("/diagnostic", data=form)
    assert r.status_code == 200
    assert "Confirmé sur votre photo" in r.text
    assert "Vos boucles sont serrées" in r.text


def test_form_ignores_tampered_photo_analysis():
    form = {
        "texture": "frise", "epaisseur": "fin", "densite": "forte", "porosite": "forte",
        "cuir_chevelu": "sec", "preoccupations": ["secheresse"], "gene_secheresse": "beaucoup",
        "chaleur": "jamais", "objectif": "hydratation", "analyse_photo": '{"texture": "pirate"}',
    }
    r = client.post("/diagnostic", data=form)
    assert r.status_code == 200
    assert "analyse de votre photo" not in r.text
