"""Direct project-folder H3 video service and explicit recovery admission."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..stage_contracts import StageName
from ..video_backends.minimax_h3.catalog import closest_h3_duration
from ..video_ingestion import ObservedVideo, probe_video
from ..video_jobs import VideoJobService
from ..video_provider import (
    VideoAdapterPort,
    VideoBackendBinding,
    VideoBackendInstanceIdentity,
    VideoProviderPort,
)
from .application_store import ApplicationStore
from .format import ProjectStorageError
from .project_handle import ProjectStore
from .project_video import ProjectVideoRepository


class ProjectVideoService:
    """Use the existing typed H3 compiler over project-local media bytes."""

    def __init__(
        self,
        application: ApplicationStore,
        provider: VideoProviderPort,
        adapter: VideoAdapterPort,
        *,
        probe: Callable[[bytes], ObservedVideo] = probe_video,
    ) -> None:
        self._application = application
        self._provider = provider
        self._adapter = adapter
        self._probe = probe

    def public_capability(self) -> dict[str, Any]:
        return self._adapter.public_capability()

    def budget(self) -> dict[str, Any]:
        return self._application.video_accounting_budget()

    def prepare(self, store: ProjectStore, **kwargs: Any) -> dict[str, Any]:
        binding = self._configured_backend_binding()
        if (binding.adapter_id == "minimax_h3_gateway" and kwargs.get("requested_seconds") is None
                and kwargs.get("playback_intent") in (None, "whole_take")):
            board = store.authoring.get_stage_payload(store.manifest.project_id, StageName.STORYBOARD)
            shot = next((shot for shot in board.shots if shot.id == kwargs["shot_id"]), None)
            if shot is not None:
                kwargs["requested_seconds"] = closest_h3_duration(shot.duration_units)
        return self._job_service(store, backend_binding=binding).prepare(store.manifest.project_id, **kwargs)

    def submit(self, store: ProjectStore, video_job_id: str) -> dict[str, Any]:
        repository = self._repository(store)
        backend_binding = self._configured_backend_binding()
        repository.assert_submit_allowed(video_job_id, backend_binding=backend_binding)
        service = self._job_service(store, repository=repository, backend_binding=backend_binding)
        while True:
            result = service.submit(store.manifest.project_id, video_job_id)
            successor = repository.prepare_video_retry(store.manifest.project_id, result["id"])
            if successor is None:
                return result
            if successor == video_job_id:
                return result
            video_job_id = successor
            current = next(job for job in self.jobs(store) if job["id"] == successor)
            if current["state"] != "prepared":
                return current
            repository.assert_submit_allowed(video_job_id, backend_binding=backend_binding)

    def reconcile(self, store: ProjectStore, video_job_id: str) -> dict[str, Any]:
        repository = self._repository(store)
        backend_binding = self._configured_backend_binding()
        repository.assert_reconcile_allowed(
            video_job_id,
            backend_binding=backend_binding,
        )
        result = self._job_service(store, repository=repository, backend_binding=backend_binding).reconcile(
            store.manifest.project_id, video_job_id)
        successor = repository.prepare_video_retry(store.manifest.project_id, video_job_id)
        if successor is not None:
            current = next(job for job in self.jobs(store) if job["id"] == successor)
            return self.submit(store, successor) if current["state"] == "prepared" else current
        return result

    def retry_failed(self, store, video_job_id):
        return self._repository(store).prepare_video_retry(store.manifest.project_id, video_job_id)

    def cancel(self, store: ProjectStore, video_job_id: str) -> dict[str, Any]:
        return self._repository(store).cancel_video_job(store.manifest.project_id, video_job_id)

    def review(self, store: ProjectStore, video_job_id: str, **kwargs: Any) -> dict[str, Any]:
        return self._repository(store).review_video_job(
            store.manifest.project_id, video_job_id, **kwargs
        )

    def jobs(self, store: ProjectStore) -> list[dict[str, Any]]:
        return self._repository(store).list_video_jobs(store.manifest.project_id)

    def output(self, store: ProjectStore, video_job_id: str) -> dict[str, Any]:
        return self._repository(store).get_video_output_storage(
            store.manifest.project_id, video_job_id
        )

    def _repository(self, store: ProjectStore) -> ProjectVideoRepository:
        return ProjectVideoRepository(store, self._application)

    def _job_service(
        self,
        store: ProjectStore,
        *,
        repository: ProjectVideoRepository | None = None,
        backend_binding: VideoBackendBinding | None = None,
    ) -> VideoJobService:
        return VideoJobService(
            repository or self._repository(store),
            store.artifacts,
            self._provider,
            adapter=self._adapter,
            backend_binding=backend_binding,
            claim_before_provider_calls=True,
            verify_backend_binding=(
                lambda video_job_id: (repository or self._repository(store)).assert_backend_binding(
                    video_job_id,
                    backend_binding=self._configured_backend_binding(),
                )
            ),
            probe=self._probe,
        )

    def _configured_backend_binding(self) -> VideoBackendBinding:
        """Read the injected transport's local identity without contacting it."""

        identity_factory = getattr(self._provider, "configured_backend_identity", None)
        if not callable(identity_factory):
            raise ProjectStorageError(
                "project-folder video requires a configured backend instance identity"
            )
        try:
            identity = identity_factory()
            if not isinstance(identity, VideoBackendInstanceIdentity):
                raise TypeError("configured backend identity has the wrong type")
            return VideoBackendBinding(
                adapter_id=self._adapter.adapter_id,
                adapter_version=self._adapter.adapter_version,
                instance=identity,
            )
        except (TypeError, ValueError) as error:
            raise ProjectStorageError(
                "project-folder video backend identity is unavailable"
            ) from error
