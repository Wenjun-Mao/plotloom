"""Typed project-side video lifecycle port for project-folder storage."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from ..domain import utc_now
from ..exceptions import InvalidTransitionError, NotFoundError
from ..persistence.schema import ProjectVideoDispatchRow, VideoJobRow
from ..video_provider import VideoBackendBinding, VideoProductionContract
from .application_store import ApplicationStore
from .project_handle import ProjectStore


class ProjectVideoRepository:
    """Bind video operations to one open project and application lease owner.

    The established media capability remains the owner of frozen request,
    currentness, review, and ingest contracts. This adapter owns only the
    explicit cross-database dispatch order instead of extending the retained
    repository facade.
    """

    def __init__(self, store: ProjectStore, application: ApplicationStore) -> None:
        self.store = store
        self._repository = store.repository
        self._application = application
        # Direct project-folder work gets the ledger-free lifecycle owner.
        # The retained Wan port remains separately composed for its legacy
        # same-transaction accounting contract.
        self._video = self._repository._media.direct_video

    @property
    def project_id(self) -> str:
        return self.store.manifest.project_id

    @staticmethod
    def dispatch_identity(video_job_id: str) -> str:
        """Stable opaque identity survives a crash before project claim write."""

        return "project-video-" + sha256(video_job_id.encode("utf-8")).hexdigest()

    def prepare_video_job(self, project_id: str, **kwargs: Any) -> dict[str, Any]:
        self._assert_project(project_id)
        self.store.require_recovery_acknowledged()
        self._assert_direct_h3_preparation(kwargs)
        return self._video.prepare_video_job(project_id, **kwargs)

    def claim_video_dispatch(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        self._assert_project(project_id)
        job = self._job(video_job_id)
        if job.state != "prepared":
            raise InvalidTransitionError(
                "video job cannot be submitted again; reconcile its existing attempt"
            )
        provider = self._frozen_direct_h3_provider(job)
        request = job.snapshot.get("request") if isinstance(job.snapshot, dict) else {}
        resource = str(provider["adapterId"])
        identity = self.dispatch_identity(video_job_id)
        # This commits in the application file first. If the process stops
        # before the project transaction, the deterministic identity makes a
        # subsequent attempt idempotent and the reservation remains cautious.
        self._application.reserve_video_dispatch(
            dispatch_identity=identity,
            resource=resource,
            reserved_units=0,
            requires_accounting=False,
        )
        with self._repository._lifecycle_write() as session:
            current = session.get(VideoJobRow, video_job_id)
            if current is None or current.project_id != project_id:
                raise NotFoundError("video job not found")
            if current.state != "prepared":
                raise InvalidTransitionError(
                    "video job cannot be submitted again; reconcile its existing attempt"
                )
            if not self._repository._media.video_currentness.video_job_current_in_session(
                session, current
            ):
                raise InvalidTransitionError(
                    "video job frozen inputs are stale; prepare a new attempt"
                )
            session.add(
                ProjectVideoDispatchRow(
                    video_job_id=video_job_id,
                    dispatch_identity=identity,
                    claimed_at=utc_now(),
                )
            )
            now = utc_now()
            current.state = "dispatching"
            current.dispatched_at = now
            current.updated_at = now
            response = self._repository._media.video_currentness.video_job_dict(
                current, current=True
            )
        # The project claim is now durable. A failure recording this
        # application event occurs before any transport call and intentionally
        # leaves the reservation conservative.
        self._application.record_video_dispatch_claim(identity)
        return response

    def cancel_video_job(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        self._assert_project(project_id)
        result = self._video.cancel_video_job(project_id, video_job_id)
        if result["state"] == "cancelled":
            self._application.release_video_before_dispatch(
                self.dispatch_identity(video_job_id)
            )
        return result

    def record_video_submission(
        self, project_id: str, video_job_id: str, prediction_id: str
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        return self._video.record_video_submission(project_id, video_job_id, prediction_id)

    def record_video_outcome_unknown(
        self, project_id: str, video_job_id: str, message: str
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        return self._video.record_video_outcome_unknown(project_id, video_job_id, message)

    def record_video_output(
        self, project_id: str, video_job_id: str, **kwargs: Any
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        return self._video.record_video_output(project_id, video_job_id, **kwargs)

    def record_video_retrieve_needed(
        self, project_id: str, video_job_id: str, message: str
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        return self._video.record_video_retrieve_needed(project_id, video_job_id, message)

    def record_video_remote_failed(
        self, project_id: str, video_job_id: str, code: str
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        return self._video.record_video_remote_failed(project_id, video_job_id, code)

    def get_managed_asset_storage(self, project_id: str, asset_id: str) -> dict[str, Any]:
        self._assert_project(project_id)
        return self._repository.get_managed_asset_storage(project_id, asset_id)

    def list_video_jobs(self, project_id: str) -> list[dict[str, Any]]:
        self._assert_project(project_id)
        return self._video.list_video_jobs(project_id)

    def get_video_output_storage(
        self, project_id: str, video_job_id: str
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        return self._video.get_video_output_storage(project_id, video_job_id)

    def review_video_job(self, project_id: str, video_job_id: str, **kwargs: Any) -> dict[str, Any]:
        self._assert_project(project_id)
        return self._video.review_video_job(project_id, video_job_id, **kwargs)

    def recovery_provider_state(self, video_job_id: str) -> str | None:
        control = self.store.recovery_control()
        if control is None:
            return None
        for operation in control.operations:
            if operation.kind == "video_job" and operation.operation_id == video_job_id:
                return operation.provider_state
        return None

    def assert_reconcile_allowed(
        self, video_job_id: str, *, backend_binding: VideoBackendBinding
    ) -> None:
        provider_state = self.recovery_provider_state(video_job_id)
        if provider_state is not None and provider_state != "known":
            raise InvalidTransitionError(
                "restored video submission is unknown; it cannot be replayed or reconciled"
            )
        self.assert_backend_binding(video_job_id, backend_binding=backend_binding)

    def assert_submit_allowed(
        self, video_job_id: str, *, backend_binding: VideoBackendBinding
    ) -> None:
        if self.recovery_provider_state(video_job_id) is not None:
            raise InvalidTransitionError(
                "restored video jobs cannot submit or replay a historical request"
            )
        self.assert_backend_binding(video_job_id, backend_binding=backend_binding)

    def assert_backend_binding(
        self, video_job_id: str, *, backend_binding: VideoBackendBinding
    ) -> None:
        """Refuse transport use unless this exact configured instance was frozen."""

        job = self._job(video_job_id)
        provider = self._frozen_direct_h3_provider(job)
        if not backend_binding.matches_snapshot(provider):
            raise InvalidTransitionError(
                "video job requires its exact frozen configured backend instance"
            )

    @staticmethod
    def _assert_direct_h3_preparation(kwargs: dict[str, Any]) -> None:
        """Admit only the direct H3, local-capacity contract before persistence.

        The project-folder surface is intentionally not a second Wan dispatch
        path.  Rejecting an absent, paid, or future policy here prevents an
        adapter-shaped object from turning an unknown contract into a free
        reservation or from touching the retained pilot ledger.
        """

        contract = kwargs.get("production_contract")
        binding = kwargs.get("backend_binding")
        if not isinstance(contract, VideoProductionContract):
            raise InvalidTransitionError("project-folder video needs a versioned production contract")
        if contract.adapter_id != "minimax_h3_gateway":
            raise InvalidTransitionError("project-folder video accepts only the H3 adapter contract")
        if contract.cost_policy != "local_capacity_v1":
            raise InvalidTransitionError("project-folder H3 requires the local-capacity cost policy")
        if not isinstance(binding, VideoBackendBinding):
            raise InvalidTransitionError("project-folder video needs a configured backend binding")
        if (
            binding.adapter_id != contract.adapter_id
            or binding.adapter_version != contract.adapter_version
        ):
            raise InvalidTransitionError("configured backend binding does not match the H3 adapter")

    @staticmethod
    def _frozen_direct_h3_provider(job: VideoJobRow) -> dict[str, Any]:
        provider = job.snapshot.get("provider") if isinstance(job.snapshot, dict) else None
        if (
            not isinstance(provider, dict)
            or provider.get("adapterId") != "minimax_h3_gateway"
            or not isinstance(provider.get("adapterVersion"), str)
            or provider.get("costPolicy") != "local_capacity_v1"
            or not isinstance(provider.get("backendBinding"), dict)
        ):
            raise InvalidTransitionError(
                "video job has no exact supported direct H3 dispatch contract"
            )
        return provider

    def _job(self, video_job_id: str) -> VideoJobRow:
        with self._repository._read() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != self.project_id:
                raise NotFoundError("video job not found")
            return job

    def _assert_project(self, project_id: str) -> None:
        if project_id != self.project_id:
            raise NotFoundError("video job does not belong to this project")
