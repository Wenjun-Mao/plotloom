"""Typed project-side video lifecycle port for project-folder storage."""

from __future__ import annotations

from hashlib import sha256
from typing import Any

from ..domain import utc_now
from ..exceptions import InvalidTransitionError, NotFoundError
from ..persistence.schema import ProjectVideoDispatchRow, VideoJobRow
from ..video_provider import VideoBackendBinding, VideoProductionContract
from ..video_segments import derive_playback_segment
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
        self._video = store.media.direct_video
        self._video_currentness = store.media.video_currentness
        self._dispatch = self._repository.video_dispatch

    @property
    def project_id(self) -> str:
        return self.store.manifest.project_id

    @staticmethod
    def dispatch_identity(video_job_id: str) -> str:
        """Stable opaque identity survives a crash before project claim write."""

        return "project-video-" + sha256(video_job_id.encode("utf-8")).hexdigest()

    def prepare_video_job(
        self,
        project_id: str,
        *,
        approval_id: str,
        shot_id: str,
        storyboard_revision: int,
        expected_selection_revision: int,
        idempotency_key: str,
        requested_seconds: int = 5,
        resolution: str = "720p",
        audio: bool = True,
        playback_intent: str = "source_exact",
        production_contract: VideoProductionContract | None = None,
        backend_binding: VideoBackendBinding | None = None,
        comparison_baseline_job_id: str | None = None,
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        self.store.require_recovery_acknowledged()
        values = {
            "production_contract": production_contract,
            "backend_binding": backend_binding,
        }
        self._assert_direct_h3_preparation(values)
        return self._video.prepare_video_job(
            project_id,
            approval_id=approval_id,
            shot_id=shot_id,
            storyboard_revision=storyboard_revision,
            expected_selection_revision=expected_selection_revision,
            idempotency_key=idempotency_key,
            requested_seconds=requested_seconds,
            resolution=resolution,
            audio=audio,
            playback_intent=playback_intent,
            production_contract=production_contract,
            backend_binding=backend_binding,
            comparison_baseline_job_id=comparison_baseline_job_id,
        )

    def claim_video_dispatch(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        self._assert_project(project_id)
        job = self._job(video_job_id)
        if job.state != "prepared":
            raise InvalidTransitionError(
                "video job cannot be submitted again; reconcile its existing attempt"
            )
        provider = self._frozen_direct_h3_provider(job)
        request = job.snapshot.get("request") if isinstance(job.snapshot, dict) else {}
        requested_seconds = request.get("durationSeconds") if isinstance(request, dict) else None
        if not isinstance(requested_seconds, int) or requested_seconds < 1:
            raise InvalidTransitionError("video job has no valid frozen requested duration")
        resource = str(provider["adapterId"])
        identity = self.dispatch_identity(video_job_id)
        # This commits in the application file first. If the process stops
        # before the project transaction, the deterministic identity makes a
        # subsequent attempt idempotent and the reservation remains cautious.
        self._application.reserve_video_dispatch(
            dispatch_identity=identity,
            resource=resource,
            reserved_units=requested_seconds,
            requires_accounting=False,
        )
        with self._dispatch.lifecycle_write() as session:
            current = session.get(VideoJobRow, video_job_id)
            if current is None or current.project_id != project_id:
                raise NotFoundError("video job not found")
            if current.state != "prepared":
                raise InvalidTransitionError(
                    "video job cannot be submitted again; reconcile its existing attempt"
                )
            if not self._video_currentness.video_job_current_in_session(
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
            response = self._video_currentness.video_job_dict(
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
        self,
        project_id: str,
        video_job_id: str,
        *,
        uri: str,
        digest: str,
        observed: dict[str, Any],
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        return self._video.record_video_output(
            project_id, video_job_id, uri=uri, digest=digest, observed=observed
        )

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
        return self.store.media.get_managed_asset_storage(project_id, asset_id)

    def list_video_jobs(self, project_id: str) -> list[dict[str, Any]]:
        self._assert_project(project_id)
        return self._video.list_video_jobs(project_id)

    def get_video_output_storage(
        self, project_id: str, video_job_id: str
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        return self._video.get_video_output_storage(project_id, video_job_id)

    def prepare_video_segment(
        self, project_id: str, video_job_id: str, *, in_frame: int,
        out_frame: int, expected_selection_revision: int,
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        self.store.require_recovery_acknowledged()
        candidate = self.store.media.video_segments.candidate_storage(
            project_id, video_job_id,
            expected_selection_revision=expected_selection_revision,
        )
        original = self.store.artifacts.get(candidate["uri"])
        if sha256(original).hexdigest() != candidate["hash"]:
            raise InvalidTransitionError("original video take hash changed")
        derived = derive_playback_segment(
            original, in_frame=in_frame, out_frame=out_frame,
            authored_duration_units=candidate["durationUnits"],
        )
        uri = self.store.artifacts.put(derived.content, expected_hash=derived.digest)
        return self.store.media.video_segments.save_proposal(
            project_id, video_job_id,
            expected_selection_revision=expected_selection_revision,
            original_hash=candidate["hash"], derivative_uri=uri, derived=derived,
        )

    def select_video_segment(
        self, project_id: str, segment_id: str, *, reviewer: str,
        note: str, expected_selection_revision: int,
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        self.store.require_recovery_acknowledged()
        storage = self.store.media.video_segments.proposal_storage(project_id, segment_id)
        content = self.store.artifacts.get(storage["uri"])
        if sha256(content).hexdigest() != storage["hash"]:
            raise InvalidTransitionError("reviewed segment bytes changed")
        return self.store.media.video_segments.select(
            project_id, segment_id, reviewer=reviewer, note=note,
            expected_selection_revision=expected_selection_revision,
            expected_derivative_hash=storage["hash"],
        )

    def get_video_segment_preview_storage(self, project_id: str, segment_id: str) -> dict[str, Any]:
        self._assert_project(project_id)
        return self.store.media.video_segments.proposal_storage(project_id, segment_id)

    def get_selected_playback_storage(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        self._assert_project(project_id)
        return self.store.media.video_segments.selected_storage(project_id, video_job_id)

    def review_video_job(
        self, project_id: str, video_job_id: str, *, reviewer: str, decision: str, note: str,
        expected_selection_revision: int,
    ) -> dict[str, Any]:
        self._assert_project(project_id)
        return self._video.review_video_job(
            project_id, video_job_id, reviewer=reviewer, decision=decision,
            note=note, expected_selection_revision=expected_selection_revision,
        )

    def discard_video_candidates(
        self, project_id: str, *, shot_id: str, video_job_ids: list[str], expected_selection_revision: int,
    ) -> None:
        self._assert_project(project_id)
        pending = self._video.discard_video_candidates(
            project_id, shot_id=shot_id, video_job_ids=video_job_ids,
            expected_selection_revision=expected_selection_revision,
        )
        self._delete_pending_candidate_artifacts(project_id, pending)

    def _delete_pending_candidate_artifacts(self, project_id: str, pending: list[dict[str, str | None]]) -> None:
        """Complete a marked disposal only after shared-reference rechecks."""
        deleted_uris: set[str] = set()
        for item in pending:
            uri = item["uri"]
            if uri and uri not in deleted_uris and not self._video.video_output_has_retained_reference(project_id, uri):
                self.store.artifacts.delete(uri)
                deleted_uris.add(uri)
        self._video.finalize_video_candidate_disposal(project_id, [str(item["id"]) for item in pending]) if pending else None

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
        with self._dispatch.read() as session:
            job = session.get(VideoJobRow, video_job_id)
            if job is None or job.project_id != self.project_id:
                raise NotFoundError("video job not found")
            return job

    def _assert_project(self, project_id: str) -> None:
        if project_id != self.project_id:
            raise NotFoundError("video job does not belong to this project")
