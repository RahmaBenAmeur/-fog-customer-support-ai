"""Nœud 2 : transcription, analyse (intention/sentiment/priorité), logique de support.
À placer à la racine du dépôt. Tout reste sur le réseau local.
Lancer : uvicorn core_node:app --host 0.0.0.0 --port 8001
"""
import json
import time

from fastapi import FastAPI, File, UploadFile
from pydantic import BaseModel

from chatbot.whisper_pipeline import generate_response
from metrics import record, router
from whisper_service import transcribe_audio

app = FastAPI()
app.include_router(router)  # ajoute /metrics et /events


class Req(BaseModel):
    message: str
    conversation: list = []


def _clean(obj):
    """Rend l'objet sérialisable en JSON (types numpy -> types Python)."""
    return json.loads(
        json.dumps(obj, default=lambda o: o.item() if hasattr(o, "item") else str(o))
    )


@app.get("/health")
def health():
    return {"status": "ok"}


# `def` (et non `async def`) : FastAPI l'exécute dans un thread, donc la
# transcription ne bloque pas les autres requêtes.
@app.post("/transcribe")
def transcribe(file: UploadFile = File(...)):
    t = time.perf_counter()
    data = file.file.read()
    name = file.filename or "audio.wav"
    ext = ("." + name.rsplit(".", 1)[-1]) if "." in name else ".wav"
    text = transcribe_audio(data, file_extension=ext)
    record("transcribe", (time.perf_counter() - t) * 1000)  # durée seulement
    return {"text": text}


@app.post("/chat")
def chat(req: Req):
    t = time.perf_counter()
    conv = list(req.conversation)
    response, analysis = generate_response(req.message, conv)
    record("chat", (time.perf_counter() - t) * 1000, state=analysis.get("state"))
    return {
        "response": response,
        "analysis": _clean(analysis),
        "conversation": _clean(conv),
    }
