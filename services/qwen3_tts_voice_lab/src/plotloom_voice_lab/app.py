"""Private same-origin Voice Lab API and reviewed browser interface."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from .contracts import CloneCreate, RoundCreate, SelectionCreate
from .engine import QwenEngine
from .media import file_sha256
from .store import Store
from .worker import Worker


WEB_DIR = Path(__file__).parent / "web"


def _not_found() -> HTTPException:
    return HTTPException(status_code=404, detail={"code": "record.not_found"})


def _verified_file(path: str | None, expected_hash: str | None) -> Path:
    if not path or not expected_hash:
        raise HTTPException(status_code=409, detail={"code": "audio.not_ready"})
    source = Path(path)
    if not source.is_file() or file_sha256(source) != expected_hash:
        raise HTTPException(status_code=409, detail={"code": "audio.corrupt"})
    return source


def create_app(data_dir: Path, engine=None) -> FastAPI:
    store = Store(data_dir)
    engine = engine or QwenEngine(
        Path(os.environ.get("VOICE_LAB_DESIGN_MODEL_DIR", "/home/wjmao/models/qwen3-tts/voice-design-1.7b")),
        Path(os.environ.get("VOICE_LAB_BASE_MODEL_DIR", "/home/wjmao/models/qwen3-tts/base-1.7b")),
    )
    worker = Worker(store, engine)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.reconcile_interrupted()
        worker.start()
        yield
        worker.stop()

    app = FastAPI(title="Spark Voice Lab", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.store = store
    app.state.worker = worker

    @app.get("/")
    def index():
        return FileResponse(WEB_DIR / "index.html", media_type="text/html")

    @app.get("/app.js")
    def javascript():
        return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")

    @app.get("/styles.css")
    def stylesheet():
        return FileResponse(WEB_DIR / "styles.css", media_type="text/css")

    @app.get("/health")
    def health():
        return {
            "service": "voice_lab", "status": "ok",
            "designModelAvailable": (engine.design_model_dir / "model.safetensors").is_file()
                if hasattr(engine, "design_model_dir") else True,
            "baseModelAvailable": (engine.base_model_dir / "model.safetensors").is_file()
                if hasattr(engine, "base_model_dir") else True,
            "workerActive": worker.active is not None,
        }

    @app.post("/api/rounds", status_code=202)
    def create_round(body: RoundCreate):
        round_id = store.create_round(body.auditionText, body.directions)
        worker.submit("round", round_id)
        return {"roundId": round_id, "status": "queued"}

    @app.get("/api/rounds")
    def list_rounds():
        return {"rounds": store.list_rounds()}

    @app.get("/api/rounds/{round_id}")
    def get_round(round_id: str):
        result = store.get_round(round_id)
        if result is None:
            raise _not_found()
        return result

    @app.get("/api/candidates/{candidate_id}/audio")
    def candidate_audio(candidate_id: str, kind: Literal["source", "h3"] = Query(default="source")):
        candidate = store.get_candidate(candidate_id, private=True)
        if candidate is None:
            raise _not_found()
        key = "source" if kind == "source" else "h3"
        source = _verified_file(candidate[f"{key}Path"], candidate[f"{key}Sha256"])
        return FileResponse(source, media_type="audio/wav", filename=f"{candidate_id}-{key}.wav")

    @app.post("/api/selections", status_code=201)
    def select_candidate(body: SelectionCreate):
        candidate = store.get_candidate(body.candidateId, private=True)
        if candidate is None:
            raise _not_found()
        if candidate["status"] != "completed":
            raise HTTPException(status_code=409, detail={"code": "candidate.not_ready"})
        _verified_file(candidate["sourcePath"], candidate["sourceSha256"])
        return store.select(body.candidateId)

    @app.get("/api/selections")
    def get_selections():
        return {"current": store.current_selection(), "history": store.selection_history()}

    @app.post("/api/clone-trials", status_code=202)
    def create_clone(body: CloneCreate):
        try:
            clone_id = store.create_clone(body.candidateId, body.text, body.seed)
        except ValueError as error:
            raise HTTPException(status_code=409, detail={"code": str(error)}) from error
        worker.submit("clone", clone_id)
        return {"trialId": clone_id, "status": "queued"}

    @app.get("/api/clone-trials")
    def list_clones(candidateId: str):
        return {"trials": store.list_clones(candidateId)}

    @app.get("/api/clone-trials/{clone_id}")
    def get_clone(clone_id: str):
        result = store.get_clone(clone_id)
        if result is None:
            raise _not_found()
        return result

    @app.get("/api/clone-trials/{clone_id}/audio")
    def clone_audio(clone_id: str):
        trial = store.get_clone(clone_id, private=True)
        if trial is None:
            raise _not_found()
        source = _verified_file(trial["audioPath"], trial["audioSha256"])
        return FileResponse(source, media_type="audio/wav", filename=f"{clone_id}.wav")

    return app


app = create_app(Path(os.environ.get("VOICE_LAB_DATA_ROOT", str(Path.home() / ".local/share/plotloom-voice-lab"))))
