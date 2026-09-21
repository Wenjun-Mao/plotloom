"""Native-worker leases outlive product cancellation and invalid packages."""
from __future__ import annotations

from contextlib import contextmanager
from typing import Any

from fastapi import FastAPI
from fastapi.testclient import TestClient

from plotloom.api.project_folder_image_jobs import (
    register_project_folder_image_job_routes,
)
from plotloom.image_job_contracts import ImageJobError


class RecordingDispatcher:
    def __init__(self) -> None:
        self.completed: list[str] = []

    def complete(self, job_id: str) -> None:
        self.completed.append(job_id)


class ConflictExchange:
    def verify_package(self, **_kwargs: Any) -> None:
        raise ImageJobError("package_conflict", "fixture froze a conflicting package")


class FinalSecretManifestExchange:
    def verify_package(self, **_kwargs: Any) -> None:
        return None

    def read_delivery(self, **_kwargs: Any) -> None:
        # The diagnostic is safe to retain; no untrusted manifest bytes or
        # secret-like value crosses the persistence boundary.
        raise ImageJobError(
            "delivery_manifest_secret", "completion manifest contains secret-like content",
            publication_phase="final",
        )


class TerminalManifest:
    delivery_id = "fixture-delivery"

    def model_dump(self, **_kwargs: Any) -> dict[str, str]:
        return {"deliveryId": self.delivery_id}


class TerminalDelivery:
    manifest = TerminalManifest()
    manifest_hash = "b" * 64
    outputs: list[Any] = []


class TerminalExchange:
    def verify_package(self, **_kwargs: Any) -> None:
        return None

    def read_delivery(self, **_kwargs: Any) -> TerminalDelivery:
        return TerminalDelivery()


class SafetyMedia:
    def __init__(self) -> None:
        self.rejections: list[tuple[str, str, str, str | None]] = []

    def cancel_character_reference_proposal(
        self, _project_id: str, proposal_id: str, _reason: str
    ) -> dict[str, str]:
        return {"id": proposal_id, "state": "cancelled"}

    def cancel_image_job(
        self, _project_id: str, job_id: str, _reason: str
    ) -> dict[str, str]:
        return {"id": job_id, "state": "cancelled"}

    def character_reference_proposal_delivery_context(
        self, _project_id: str, proposal_id: str
    ) -> dict[str, Any]:
        return {
            "id": proposal_id,
            "requestHash": "a" * 64,
            "request": {
                "frozenSnapshot": {"references": []},
                "specialistPreflight": {"version": "p1.5-pin.v1"},
            },
        }

    def record_character_reference_proposal_rejection(
        self, project_id: str, proposal_id: str, code: str, *, publication_phase: str | None = None,
    ) -> None:
        self.rejections.append((project_id, proposal_id, code, publication_phase))


class SafetyStore:
    def __init__(self, exchange: Any | None = None) -> None:
        self.media = SafetyMedia()
        self.exchange = exchange or ConflictExchange()

    def image_exchange_for(self, _context: dict[str, Any]) -> Any:
        return self.exchange


def _client(exchange: Any | None = None) -> tuple[TestClient, RecordingDispatcher, SafetyStore]:
    store = SafetyStore(exchange)
    dispatcher = RecordingDispatcher()

    @contextmanager
    def opened_project(_project_id: str):
        yield store

    app = FastAPI()
    register_project_folder_image_job_routes(
        app,
        opened_project,
        image_job_target_id=lambda _body: "fixture",
        require_media_draft_scope=lambda **_kwargs: None,
        project_h3_target=lambda _project_id: {},
        image_dispatcher=dispatcher,  # type: ignore[arg-type]
    )
    return TestClient(app, raise_server_exceptions=False), dispatcher, store


def _terminal_client() -> tuple[TestClient, RecordingDispatcher]:
    dispatcher = RecordingDispatcher()

    class TerminalMedia:
        @staticmethod
        def character_reference_proposal_delivery_context(
            _project_id: str, proposal_id: str
        ) -> dict[str, Any]:
            return {
                "id": proposal_id,
                "requestHash": "a" * 64,
                "request": {"frozenSnapshot": {"references": []}},
            }

        @staticmethod
        def image_job_delivery_context(
            _project_id: str, job_id: str
        ) -> dict[str, Any]:
            return {
                "id": job_id,
                "requestHash": "a" * 64,
                "request": {"frozenSnapshot": {"references": []}},
            }

        @staticmethod
        def record_character_reference_proposal_delivery(
            *_args: Any, **_kwargs: Any
        ) -> dict[str, str]:
            return {"state": "accepted"}

        @staticmethod
        def record_image_job_delivery(*_args: Any, **_kwargs: Any) -> dict[str, str]:
            return {"state": "accepted"}

    class TerminalStore:
        media = TerminalMedia()

        @staticmethod
        def image_exchange_for(_context: dict[str, Any]) -> TerminalExchange:
            return TerminalExchange()

    @contextmanager
    def opened_project(_project_id: str):
        yield TerminalStore()

    app = FastAPI()
    register_project_folder_image_job_routes(
        app,
        opened_project,
        image_job_target_id=lambda _body: "fixture",
        require_media_draft_scope=lambda **_kwargs: None,
        project_h3_target=lambda _project_id: {},
        image_dispatcher=dispatcher,  # type: ignore[arg-type]
    )
    return TestClient(app), dispatcher


def test_cancelling_character_proposal_does_not_release_native_worker_lease() -> None:
    client, dispatcher, _store = _client()
    try:
        response = client.post(
            "/api/v2/projects/project/character-reference-proposals/ij_abcdefghijklmnopqrst/cancel",
            json={"reason": "Creator stopped publication, not the native worker."},
        )
        assert response.status_code == 200
        assert dispatcher.completed == []
    finally:
        client.close()


def test_cancelling_image_job_does_not_release_native_worker_lease() -> None:
    client, dispatcher, _store = _client()
    try:
        response = client.post(
            "/api/v2/projects/project/image-jobs/ij_abcdefghijklmnopqrst/cancel",
            json={"reason": "Creator stopped publication, not the native worker."},
        )
        assert response.status_code == 200
        assert dispatcher.completed == []
    finally:
        client.close()


def test_package_conflict_does_not_release_native_worker_lease() -> None:
    client, dispatcher, store = _client()
    try:
        response = client.post(
            "/api/v2/projects/project/character-reference-proposals/ij_abcdefghijklmnopqrst/refresh"
        )
        assert response.status_code == 500
        assert store.media.rejections == [
            ("project", "ij_abcdefghijklmnopqrst", "package_conflict", None)
        ]
        assert dispatcher.completed == []
    finally:
        client.close()


def test_final_secret_manifest_persists_only_safe_final_diagnostic() -> None:
    client, dispatcher, store = _client(FinalSecretManifestExchange())
    try:
        response = client.post(
            "/api/v2/projects/project/character-reference-proposals/ij_abcdefghijklmnopqrst/refresh"
        )
        assert response.status_code == 500
        assert store.media.rejections == [
            ("project", "ij_abcdefghijklmnopqrst", "delivery_manifest_secret", "final")
        ]
        assert dispatcher.completed == []
    finally:
        client.close()


def test_terminal_delivery_releases_native_worker_lease_for_both_route_owners() -> None:
    client, dispatcher = _terminal_client()
    try:
        character = client.post(
            "/api/v2/projects/project/character-reference-proposals/ij_abcdefghijklmnopqrst/refresh"
        )
        image = client.post(
            "/api/v2/projects/project/image-jobs/ij_bcdefghijklmnopqrstu/refresh"
        )
        assert character.status_code == 200
        assert image.status_code == 200
        assert dispatcher.completed == [
            "ij_abcdefghijklmnopqrst",
            "ij_bcdefghijklmnopqrstu",
        ]
    finally:
        client.close()
