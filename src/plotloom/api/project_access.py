"""Per-application request admission and scoped project-store ownership."""

from __future__ import annotations

from contextlib import contextmanager
from contextvars import ContextVar

from fastapi import FastAPI

from ..project_storage import ProjectFolderStorage


def register_project_access(app: FastAPI, storage: ProjectFolderStorage):
    read_request: ContextVar[bool] = ContextVar("project_read_request", default=False)

    @app.middleware("http")
    async def project_read_admission(request, call_next):
        token = read_request.set(request.method in {"GET", "HEAD"})
        try:
            return await call_next(request)
        finally:
            read_request.reset(token)

    @contextmanager
    def opened_project(project_id: str):
        from ..project_storage.proof_scope import proof_scope

        with proof_scope():
            store = (
                storage.projects.read_open(project_id)
                if read_request.get()
                else storage.projects.open(project_id)
            )
            try:
                yield store
            finally:
                store.close()

    @contextmanager
    def inspected_project(project_id: str):
        store = storage.projects.inspect(project_id)
        try:
            yield store
        finally:
            store.close()

    @contextmanager
    def inspected_open_project(project_id: str):
        store = storage.projects.read_open(project_id, admission="inspection")
        try:
            yield store
        finally:
            store.close()

    return opened_project, inspected_project, inspected_open_project
