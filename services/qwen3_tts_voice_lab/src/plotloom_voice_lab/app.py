"""Private same-origin project-scoped Voice Lab API."""

from __future__ import annotations

import os
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Literal

from fastapi import FastAPI, HTTPException, Query
from fastapi.responses import FileResponse

from .contracts import (
    CandidateCreate, CandidateDelete, CandidateUpdate, CloneCreate,
    GenerationCreate, PairedCreation, ProjectCreate, ProjectDelete, ProjectUpdate,
    PublishCreate, SelectionCreate,
)
from .engines.catalog import public_catalog
from .engines.process import ProcessEngine
from .media import file_sha256
from .store import Store
from .worker import Worker


WEB_DIR = Path(__file__).parent / "web"


def _api_error(error: ValueError) -> HTTPException:
    code = str(error)
    status = 404 if code.endswith(".not_found") else 409
    return HTTPException(status_code=status, detail={"code": code})


def _verified_file(store: Store, path: str | None, expected_hash: str | None) -> Path:
    if not path or not expected_hash:
        raise HTTPException(status_code=409, detail={"code": "audio.not_ready"})
    try:
        source = store.owned_file(path)
        if not source.is_file() or file_sha256(source) != expected_hash:
            raise ValueError("audio.corrupt")
    except (ValueError, OSError) as error:
        raise HTTPException(status_code=409, detail={"code": "audio.corrupt"}) from error
    return source


def create_app(data_dir: Path, engine=None, *, lane_client=None, dispatch_key=None) -> FastAPI:
    store = Store(data_dir)
    engine = engine or ProcessEngine()
    worker = Worker(store, engine, lane_client=lane_client)
    if lane_client is not None and hasattr(lane_client, "bind"):
        lane_client.bind(worker)

    @asynccontextmanager
    async def lifespan(_: FastAPI):
        store.reconcile_interrupted()
        worker.start()
        yield
        worker.stop()

    app = FastAPI(title="Spark Voice Lab", lifespan=lifespan, docs_url=None, redoc_url=None)
    app.state.store = store
    app.state.worker = worker
    from .take_api import install_take_api
    install_take_api(app, store, worker, _verified_file, _api_error, dispatch_key=dispatch_key)

    @app.get("/takes.js")
    def takes_javascript():
        return FileResponse(WEB_DIR / "takes.js", media_type="application/javascript")

    @app.get("/")
    def index():
        return FileResponse(WEB_DIR / "index.html", media_type="text/html")

    @app.get("/app.js")
    def javascript():
        return FileResponse(WEB_DIR / "app.js", media_type="application/javascript")

    @app.get("/reuse.js")
    def reuse_javascript():
        return FileResponse(WEB_DIR / "reuse.js", media_type="application/javascript")

    @app.get("/styles.css")
    def stylesheet():
        return FileResponse(WEB_DIR / "styles.css", media_type="text/css")

    @app.get("/health")
    def health():
        return {
            "service": "voice_lab", "status": "ok",
            "engines": engine.availability(),
            "workerActive": worker.active is not None,
        }

    @app.get("/api/engines")
    def engines():
        return {"engines": public_catalog(), "availability": engine.availability()}

    @app.post("/api/projects/{project_id}/paired-generations", status_code=202)
    def paired_generations(project_id: str, body: PairedCreation):
        try:
            project, generation_ids = store.projects.create_paired(project_id, body)
        except ValueError as error:
            raise _api_error(error) from error
        for generation_id in generation_ids:
            worker.submit("generation", generation_id)
        return {"project": project, "generationIds": generation_ids}

    @app.get("/api/projects")
    def list_projects():
        return {"projects": store.projects.list()}

    @app.post("/api/projects", status_code=201)
    def create_project(body: ProjectCreate):
        return store.projects.create(body.name)

    @app.get("/api/projects/{project_id}")
    def get_project(project_id: str):
        try:
            return store.projects.get(project_id)
        except ValueError as error:
            raise _api_error(error) from error

    @app.put("/api/projects/{project_id}")
    def update_project(project_id: str, body: ProjectUpdate):
        try:
            return store.projects.update(project_id, body.expectedRevision, body.name, body.brief, body.auditionText)
        except ValueError as error:
            raise _api_error(error) from error

    @app.delete("/api/projects/{project_id}", status_code=204)
    def delete_project(project_id: str, body: ProjectDelete):
        try:
            store.projects.delete(project_id, body.expectedRevision, body.confirmName)
        except ValueError as error:
            raise _api_error(error) from error

    @app.post("/api/projects/{project_id}/candidates", status_code=201)
    def add_candidate(project_id: str, body: CandidateCreate):
        try:
            return store.projects.add_candidate(project_id, body.expectedProjectRevision, body.direction, body.engineId)
        except ValueError as error:
            raise _api_error(error) from error

    @app.put("/api/candidates/{candidate_id}")
    def edit_candidate(candidate_id: str, body: CandidateUpdate):
        try:
            return store.projects.edit_candidate(candidate_id, body.expectedProjectRevision,
                                                 body.expectedCandidateRevision, body.direction, body.engineId)
        except ValueError as error:
            raise _api_error(error) from error

    @app.delete("/api/candidates/{candidate_id}")
    def delete_candidate(candidate_id: str, body: CandidateDelete):
        try:
            return store.projects.delete_candidate(candidate_id, body.expectedProjectRevision,
                                                   body.expectedCandidateRevision)
        except ValueError as error:
            raise _api_error(error) from error

    @app.post("/api/candidates/{candidate_id}/generations", status_code=202)
    def create_generation(candidate_id: str, body: GenerationCreate):
        try:
            result = store.generations.create(candidate_id, body.expectedProjectRevision,
                                              body.expectedCandidateRevision, body.seed)
        except ValueError as error:
            raise _api_error(error) from error
        worker.submit("generation", result["generationId"])
        return result

    @app.get("/api/candidates/{candidate_id}/generations")
    def generation_history(candidate_id: str):
        try:
            return {"generations": store.generations.history(candidate_id)}
        except ValueError as error:
            raise _api_error(error) from error

    @app.get("/api/generations/{generation_id}")
    def get_generation(generation_id: str):
        try:
            return store.generations.get(generation_id)
        except ValueError as error:
            raise _api_error(error) from error

    @app.get("/api/generations/{generation_id}/progress")
    def generation_progress(generation_id: str):
        try:
            generation = store.generations.get(generation_id)
        except ValueError as error:
            raise _api_error(error) from error
        status = generation["status"]
        live = worker.progress("generation", generation_id) if status in {"queued", "running"} else None
        return {"generationId": generation_id, "status": status,
                "queueAhead": live["queueAhead"] if live else None,
                "phase": live["phase"] if live else None,
                "elapsedSeconds": live["elapsedSeconds"] if live else None,
                "errorCode": generation["errorCode"]}

    @app.get("/api/generations/{generation_id}/audio")
    def generation_audio(generation_id: str, kind: Literal["source", "h3"] = Query(default="source")):
        try:
            result = store.generations.get(generation_id, private=True)
        except ValueError as error:
            raise _api_error(error) from error
        source = _verified_file(store, result[f"{kind}Path"], result[f"{kind}Sha256"])
        return FileResponse(source, media_type="audio/wav", filename=f"{generation_id}-{kind}.wav")

    @app.post("/api/projects/{project_id}/selections", status_code=201)
    def select_generation(project_id: str, body: SelectionCreate):
        try:
            return store.generations.select(project_id, body.generationId)
        except ValueError as error:
            raise _api_error(error) from error

    @app.get("/api/projects/{project_id}/selections")
    def selection_history(project_id: str):
        try:
            store.projects.get(project_id)
            return {"history": store.generations.selections(project_id)}
        except ValueError as error:
            raise _api_error(error) from error

    @app.post("/api/clone-trials", status_code=202)
    def create_clone(body: CloneCreate):
        try:
            result = store.clones.create(body.projectId, body.generationId, body.text, body.seed,
                                         body.engineId, body.delivery)
        except ValueError as error:
            raise _api_error(error) from error
        worker.submit("clone", result["trialId"])
        return result

    @app.get("/api/clone-trials")
    def list_clones(projectId: str):
        return {"trials": store.clones.list(projectId)}

    @app.get("/api/clone-trials/{trial_id}")
    def get_clone(trial_id: str):
        try:
            return store.clones.get(trial_id)
        except ValueError as error:
            raise _api_error(error) from error

    @app.get("/api/clone-trials/{trial_id}/audio")
    def clone_audio(trial_id: str):
        try:
            result = store.clones.get(trial_id, private=True)
        except ValueError as error:
            raise _api_error(error) from error
        source = _verified_file(store, result["audioPath"], result["audioSha256"])
        return FileResponse(source, media_type="audio/wav", filename=f"{trial_id}.wav")

    @app.get("/api/clone-trials/{trial_id}/progress")
    def clone_progress(trial_id: str):
        try:
            trial = store.clones.get(trial_id)
        except ValueError as error:
            raise _api_error(error) from error
        live = worker.progress("clone", trial_id) if trial["status"] in {"queued", "running"} else None
        return {"trialId": trial_id, "status": trial["status"], "errorCode": trial["errorCode"],
                "phase": live["phase"] if live else None, "queueAhead": live["queueAhead"] if live else None,
                "elapsedSeconds": live["elapsedSeconds"] if live else None,
                "executionDetails": trial["executionDetails"]}

    @app.post("/api/voices", status_code=201)
    def publish_voice(body: PublishCreate):
        try:
            return store.voices.publish(body.projectId, body.generationId)
        except ValueError as error:
            raise _api_error(error) from error

    @app.get("/api/voices")
    def list_voices():
        return {"voices": store.voices.list()}

    @app.get("/api/voices/{voice_id}")
    def get_voice(voice_id: str):
        try:
            return store.voices.get(voice_id)
        except ValueError as error:
            raise _api_error(error) from error

    @app.get("/api/voices/{voice_id}/audio")
    def voice_audio(voice_id: str, kind: Literal["source", "h3"] = Query(default="h3")):
        try:
            result = store.voices.get(voice_id, private=True)
        except ValueError as error:
            raise _api_error(error) from error
        source = _verified_file(store, result[f"{kind}Path"], result[f"{kind}Sha256"])
        return FileResponse(source, media_type="audio/wav", filename=f"{voice_id}-{kind}.wav")

    return app


app = create_app(Path(os.environ.get("VOICE_LAB_DATA_ROOT", str(Path.home() / ".local/share/plotloom-voice-lab"))))
