"""Direct project-folder H3 video service and explicit recovery admission."""

from __future__ import annotations

from collections.abc import Callable
from typing import Any

from ..video_ingestion import ObservedVideo, probe_video
from ..video_jobs import VideoJobService
from ..video_provider import VideoAdapterPort, VideoProviderPort
from .application_store import ApplicationStore
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
        return self._job_service(store).prepare(store.manifest.project_id, **kwargs)

    def submit(self, store: ProjectStore, video_job_id: str) -> dict[str, Any]:
        repository = self._repository(store)
        repository.assert_submit_allowed(video_job_id)
        return self._job_service(store, repository=repository).submit(
            store.manifest.project_id, video_job_id
        )

    def reconcile(self, store: ProjectStore, video_job_id: str) -> dict[str, Any]:
        repository = self._repository(store)
        repository.assert_reconcile_allowed(
            video_job_id,
            adapter_id=self._adapter.adapter_id,
            adapter_version=self._adapter.adapter_version,
        )
        return self._job_service(store, repository=repository).reconcile(
            store.manifest.project_id, video_job_id
        )

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
        self, store: ProjectStore, *, repository: ProjectVideoRepository | None = None
    ) -> VideoJobService:
        return VideoJobService(
            repository or self._repository(store),
            store.artifacts,
            self._provider,
            adapter=self._adapter,
            probe=self._probe,
        )
