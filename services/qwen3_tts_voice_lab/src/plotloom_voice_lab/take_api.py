"""Published-identity takes and authenticated shared-lane execution."""

import hmac
import os
from typing import Literal

from fastapi import Depends, Header, HTTPException, Query
from fastapi.responses import FileResponse

from .contracts import TakeCreate, TakeDelete
from .dispatch import ExecutionGrant


def install_take_api(app, store, worker, verified_file, api_error, *, dispatch_key=None):
    key = dispatch_key if dispatch_key is not None else os.environ.get("VOICE_LAB_DISPATCH_KEY", "")

    def authorize(authorization: str | None = Header(default=None)):
        if not key or authorization is None or not hmac.compare_digest(authorization, f"Bearer {key}"):
            raise HTTPException(401, detail={"code": "dispatch.unauthorized"})

    def create(body: TakeCreate):
        try:
            take = store.takes.create(body)
            worker.submit("take", take["takeId"])
            return take
        except ValueError as error:
            raise api_error(error) from error

    def list_takes(voiceId: str):
        try:
            return {"takes": store.takes.list(voiceId)}
        except ValueError as error:
            raise api_error(error) from error

    def get(take_id: str):
        try:
            result = store.takes.get(take_id)
            progress = worker.progress("take", take_id)
            result.update({key: value for key, value in progress.items() if key != "errorCode"})
            result["dispatchErrorCode"] = progress.get("errorCode")
            return result
        except ValueError as error:
            raise api_error(error) from error

    def audio(take_id: str, kind: Literal["source", "h3"] = Query(default="source")):
        try:
            result = store.takes.get(take_id, private=True)
        except ValueError as error:
            raise api_error(error) from error
        source = verified_file(store, result.get(f"{kind}Path"), result.get(f"{kind}Sha256"))
        return FileResponse(source, media_type="audio/wav", filename=f"{take_id}-{kind}.wav")

    def delete(take_id: str, body: TakeDelete):
        try:
            store.takes.delete(take_id, body.confirmTakeId)
        except ValueError as error:
            raise api_error(error) from error

    for prefix, dependencies in (("/api", []), ("/internal", [Depends(authorize)])):
        app.add_api_route(prefix + "/voice-takes", create, methods=["POST"], status_code=202, dependencies=dependencies)
        app.add_api_route(prefix + "/voice-takes", list_takes, methods=["GET"], dependencies=dependencies)
        app.add_api_route(prefix + "/voice-takes/{take_id}", get, methods=["GET"], dependencies=dependencies)
        app.add_api_route(prefix + "/voice-takes/{take_id}/audio", audio, methods=["GET"], dependencies=dependencies)
        app.add_api_route(prefix + "/voice-takes/{take_id}", delete, methods=["DELETE"], status_code=204, dependencies=dependencies)

    @app.post("/internal/executions", dependencies=[Depends(authorize)], status_code=202)
    def execute(body: ExecutionGrant):
        try:
            return worker.execute(body)
        except ValueError as error:
            raise api_error(error) from error

    @app.get("/internal/executions/{grant_id}", dependencies=[Depends(authorize)])
    def execution(grant_id: str):
        try:
            return store.dispatch.execution(grant_id)
        except ValueError as error:
            raise api_error(error) from error
