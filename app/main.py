from __future__ import annotations

from fastapi import FastAPI, HTTPException
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel

from app.config import settings
from app.data_store import build_dashboard, build_replay
from app.services.agent import answer_question

app = FastAPI(
    title='ThermoCharge AI',
    version='1.0.0',
    description='Thermal capacity intelligence for EV charging networks.',
)

app.mount('/static', StaticFiles(directory=settings.static_dir), name='static')


@app.get('/health')
def health() -> dict[str, str]:
    return {'status': 'ok'}


@app.get('/api/dashboard')
def dashboard():
    try:
        return build_dashboard()
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get('/api/replay')
def replay():
    """Full Heat Event Replay: one precomputed dashboard frame per fetched
    time point (see pilot.json replay_times_local). 404s cleanly with setup
    instructions if scripts/fetch_fortyguard.py hasn't been run yet."""
    try:
        return build_replay()
    except FileNotFoundError as exc:
        raise HTTPException(status_code=404, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


class AskRequest(BaseModel):
    question: str


@app.post('/api/ask')
def ask(body: AskRequest):
    """Goal-driven Q&A layer: answers a plain-language operator question,
    grounded entirely in the already-computed, already-audited dashboard
    state. Never invents a number; works with or without an LLM key."""
    question = (body.question or '').strip()
    if not question:
        raise HTTPException(status_code=400, detail='question must not be empty')
    try:
        state = build_dashboard()
        result = answer_question(question, state, settings.openai_api_key, settings.openai_model)
        return {'question': question, **result}
    except Exception as exc:
        raise HTTPException(status_code=500, detail=str(exc)) from exc


@app.get('/')
def index():
    return FileResponse(settings.static_dir / 'index.html')
