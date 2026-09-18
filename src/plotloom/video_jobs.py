"""Execution/ingestion orchestration for the separate P2 video lifecycle."""
from __future__ import annotations

from hashlib import sha256
from typing import TYPE_CHECKING, Any, Callable

from .artifacts import ArtifactStore
from .video_ingestion import ObservedVideo, probe_video
from .video_provider import (
    AtlasWanAdapter,
    RemoteOutcomeUnknown,
    RemotePredictionFailed,
    VideoAdapterPort,
    VideoBackendBinding,
    VideoOutputContractError,
    VideoProviderError,
    VideoProviderPort,
    WanDispatchDiagnostic,
    WanDispatchError,
)

if TYPE_CHECKING:
    from .project_storage.project_video import ProjectVideoRepository as VideoJobRepository


class VideoJobService:
    """Never retries POST; recovery only polls known prediction IDs."""

    def __init__(
        self,
        repository: "VideoJobRepository",
        artifacts: ArtifactStore,
        provider: VideoProviderPort,
        *,
        adapter: VideoAdapterPort | None = None,
        backend_binding: VideoBackendBinding | None = None,
        claim_before_provider_calls: bool = False,
        verify_backend_binding: Callable[[str], None] | None = None,
        probe: Callable[[bytes], ObservedVideo] = probe_video,
    ) -> None:
        self.repository, self.artifacts, self.provider, self.probe = repository, artifacts, provider, probe
        self.adapter = adapter or AtlasWanAdapter()
        self.backend_binding = backend_binding
        self.claim_before_provider_calls = claim_before_provider_calls
        self.verify_backend_binding = verify_backend_binding

    def prepare(
        self,
        project_id: str,
        *,
        approval_id: str,
        shot_id: str,
        storyboard_revision: int,
        expected_selection_revision: int,
        idempotency_key: str,
        requested_seconds: int | None,
        resolution: str | None,
        audio: bool | None,
        aspect_policy: str | None,
        allow_letterbox: bool,
        allow_center_crop: bool,
        seed: int | None,
        profile_id: str | None,
    ) -> dict[str, Any]:
        """Freeze the adapter-owned request before any durable dispatch claim."""

        contract = self.adapter.production_contract(
            requested_seconds=requested_seconds,
            resolution=resolution,
            audio=audio,
            aspect_policy=aspect_policy,
            allow_letterbox=allow_letterbox,
            allow_center_crop=allow_center_crop,
            seed=seed,
            profile_id=profile_id,
        )
        if contract is not None:
            return self.repository.prepare_video_job(
                project_id,
                approval_id=approval_id,
                shot_id=shot_id,
                storyboard_revision=storyboard_revision,
                expected_selection_revision=expected_selection_revision,
                idempotency_key=idempotency_key,
                production_contract=contract,
                backend_binding=self.backend_binding,
            )

        # Adapters that return no production contract retain their historical
        # snapshot projection. Atlas's adapter has already rejected fields it
        # does not support before this compatibility path is reached.
        return self.repository.prepare_video_job(
            project_id,
            approval_id=approval_id,
            shot_id=shot_id,
            storyboard_revision=storyboard_revision,
            expected_selection_revision=expected_selection_revision,
            idempotency_key=idempotency_key,
            requested_seconds=5 if requested_seconds is None else requested_seconds,
            resolution="720p" if resolution is None else resolution,
            audio=True if audio is None else audio,
            backend_binding=self.backend_binding,
        )

    def public_capability(self) -> dict[str, Any]:
        """Secret-free capability projection used by the workbench."""

        return self.adapter.public_capability()

    @staticmethod
    def _prompt(snapshot: dict[str, Any]) -> str:
        shot = snapshot["shot"]
        cues = snapshot["resolvedContext"].get("dialogueCues", [])
        cue_text = "\n".join(
            f"Dialogue ({cue.get('language')}; speaker={cue.get('speakerId') or cue.get('voiceOver')}; "
            f"delivery={cue.get('delivery')}; performance={cue.get('performanceNotes')}): {cue.get('text')}"
            for cue in cues
        )
        audio = snapshot["shot"].get("audioPlan", {}).get("events", [])
        audio_text = "\n".join(
            f"Sound ({event.get('kind')}, {event.get('startOffsetUnits')}ms for {event.get('durationUnits')}ms): {event.get('description')}"
            for event in audio
        )
        # This is an exact frozen compiler projection, not a browser prompt.
        return "\n".join(filter(None, [str(shot.get("visualIntent", "")), f"Action: {shot.get('action', '')}", f"Motion: {shot.get('motionIntent', '')}", cue_text, audio_text]))

    @staticmethod
    def _profile_id(snapshot: dict[str, Any]) -> str | None:
        """Read only the frozen profile, never a current browser selection."""

        request = snapshot.get("request")
        if isinstance(request, dict) and isinstance(request.get("profileId"), str):
            return request["profileId"]
        return None

    @staticmethod
    def _frozen_h3_output(snapshot: dict[str, Any]) -> tuple[int | None, int | None, int | None, int | None]:
        """Read the prepared output contract, never profile defaults after restart."""

        request = snapshot.get("request")
        if not isinstance(request, dict):
            return None, None, None, None
        duration, frame_count, fps, seed = (
            request.get("durationSeconds"), request.get("frameCount"), request.get("fps"), request.get("seed")
        )
        if all(isinstance(value, int) for value in (duration, frame_count, fps, seed)):
            return duration, frame_count, fps, seed
        return None, None, None, None

    @staticmethod
    def _frozen_h3_profile(snapshot: dict[str, Any]) -> tuple[int | None, int | None, int | None]:
        request = snapshot.get("request")
        if not isinstance(request, dict):
            return None, None, None
        version, width, height = (
            request.get("profileVersion"), request.get("width"), request.get("height")
        )
        if all(isinstance(value, int) for value in (version, width, height)):
            return version, width, height
        return None, None, None

    def submit(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        preflight = getattr(self.provider, "preflight", None)
        if callable(preflight) and not self.claim_before_provider_calls:
            try:
                preflight()
            except Exception:
                # This happens before the durable dispatch boundary, so the
                # reservation is safely released and no remote POST occurs.
                return self.repository.cancel_video_job(project_id, video_job_id)
        job = self.repository.claim_video_dispatch(project_id, video_job_id)
        try:
            if callable(preflight) and self.claim_before_provider_calls:
                # The project-folder dispatch protocol has made its
                # application reservation, project claim, and application
                # claim event durable before *any* transport operation.  A
                # failed health check therefore remains conservative rather
                # than pretending the transport was never contacted.
                self._assert_current_backend(video_job_id)
                preflight()
            try:
                keyframe = job["snapshot"]["keyframe"]
                stored = self.repository.get_managed_asset_storage(project_id, keyframe["assetId"])
                image = self.artifacts.get(stored["originalUri"])
                if sha256(image).hexdigest() != keyframe["originalHash"]:
                    # Treat a store/hash mismatch as preflight. Dispatch cannot
                    # start, but the durable claim remains conservative because
                    # the caller cannot prove where a failure happened.
                    raise WanDispatchError(WanDispatchDiagnostic("keyframe_read", "local_precondition_failed"))
            except WanDispatchError:
                raise
            except Exception as error:
                raise WanDispatchError(WanDispatchDiagnostic("keyframe_read", "local_precondition_failed")) from error
            self._assert_current_backend(video_job_id)
            compile_image = getattr(self.adapter, "compile_image", None)
            submit_image = getattr(self.provider, "submit_image", None)
            if callable(compile_image) and callable(submit_image):
                try:
                    duration, _frame_count, _fps, _seed = self._frozen_h3_output(job["snapshot"])
                    profile_version, width, height = self._frozen_h3_profile(job["snapshot"])
                    # A direct-image provider owns temporary frame admission;
                    # no public asset identifier or idempotency state crosses
                    # the boundary.  This is a capability contract, not a
                    # provider-name special case.
                    payload = compile_image(
                        prompt=self._prompt(job["snapshot"]), duration=duration,
                        resolution=job["snapshot"]["request"]["resolution"],
                        audio=job["snapshot"]["request"]["audio"],
                        aspect_policy=job["snapshot"]["request"].get("aspectPolicy"),
                        seed=job["snapshot"]["request"].get("seed"),
                        profile_id=self._profile_id(job["snapshot"]),
                        profile_version=profile_version, width=width, height=height,
                        fps=_fps, frame_count=_frame_count,
                    )
                except VideoProviderError as error:
                    raise WanDispatchError(WanDispatchDiagnostic("request_compile", "local_precondition_failed")) from error
                self._assert_current_backend(video_job_id)
                submitted = submit_image(image, mime_type=keyframe["mimeType"], payload=payload)
            else:
                try:
                    uploaded = self.provider.upload(image, mime_type=keyframe["mimeType"])
                    duration, _frame_count, _fps, _seed = self._frozen_h3_output(job["snapshot"])
                    # Historical Atlas snapshots have no H3 output fields;
                    # their retained row duration is still their contract.
                    compile_duration = duration if duration is not None else job["requestedSeconds"]
                    payload = self.adapter.compile(
                        prompt=self._prompt(job["snapshot"]), uploaded_asset=uploaded,
                        duration=compile_duration, resolution=job["snapshot"]["request"]["resolution"],
                        audio=job["snapshot"]["request"]["audio"],
                        aspect_policy=job["snapshot"]["request"].get("aspectPolicy"),
                        seed=job["snapshot"]["request"].get("seed"),
                        profile_id=self._profile_id(job["snapshot"]),
                    )
                except VideoProviderError as error:
                    raise WanDispatchError(WanDispatchDiagnostic("request_compile", "local_precondition_failed")) from error
                self._assert_current_backend(video_job_id)
                submitted = self.provider.submit(payload, idempotency_key=video_job_id)
            try:
                duration, frame_count, _fps, seed = self._frozen_h3_output(job["snapshot"])
                profile_version, width, height = self._frozen_h3_profile(job["snapshot"])
                prediction = self.adapter.prediction_id(
                    submitted,
                    expected_profile_id=self._profile_id(job["snapshot"]),
                    expected_aspect_policy=job["snapshot"]["request"].get("aspectPolicy"),
                    expected_duration_seconds=duration,
                    expected_frame_count=frame_count,
                    expected_seed=seed,
                    expected_profile_version=profile_version,
                    expected_width=width,
                    expected_height=height,
                    expected_fps=_fps,
                )
            except VideoProviderError as error:
                raise WanDispatchError(WanDispatchDiagnostic("submit_response_parse", "invalid_envelope")) from error
        except WanDispatchError as error:
            # The state stays outcome_unknown because a claimed remote POST is
            # not safely replayable. The code only identifies the local phase.
            return self.repository.record_video_outcome_unknown(project_id, video_job_id, error.diagnostic.outcome_error)
        except Exception:
            # It is unsafe to infer that the remote POST did not begin.
            return self.repository.record_video_outcome_unknown(project_id, video_job_id, "dispatch_outcome_unknown")
        return self.repository.record_video_submission(project_id, video_job_id, prediction)

    def reconcile(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        jobs = {item["id"]: item for item in self.repository.list_video_jobs(project_id)}
        job = jobs.get(video_job_id)
        if job is None:
            raise ValueError("video job not found")
        if job["state"] not in {"submitted", "retrieve_needed"} or not job["providerPredictionId"]:
            return job
        try:
            profile_id = self._profile_id(job["snapshot"])
            duration, frame_count, fps, seed = self._frozen_h3_output(job["snapshot"])
            profile_version, width, height = self._frozen_h3_profile(job["snapshot"])
            output = self.adapter.completed_output(
                self._poll_current_backend(video_job_id, job["providerPredictionId"]),
                expected_profile_id=profile_id,
                expected_aspect_policy=job["snapshot"]["request"].get("aspectPolicy"),
                expected_duration_seconds=duration,
                expected_frame_count=frame_count,
                expected_seed=seed,
                expected_profile_version=profile_version,
                expected_width=width,
                expected_height=height,
                expected_fps=fps,
            )
            if output is None:
                return job
            # A cancel intent retains known-ID reconciliation evidence but
            # never downloads, ingests, or adopts a candidate.
            if job.get("cancelRequestedAt"):
                return job
            self.adapter.validate_output_reference(output)
            self._assert_current_backend(video_job_id)
            content = self.provider.download(output)
            observed = self.probe(content)
            if observed.audio_codec is None:
                raise ValueError("audio_track_missing")
            self.adapter.validate_observed_output(
                observed, profile_id=profile_id, requested_seconds=duration,
                expected_frame_count=frame_count, expected_fps=fps,
                expected_profile_version=profile_version, expected_width=width,
                expected_height=height,
            )
            uri = self.artifacts.put(content)
            return self.repository.record_video_output(
                project_id, video_job_id, uri=uri, digest=sha256(content).hexdigest(),
                observed={"durationSeconds": observed.duration_seconds, "width": observed.width, "height": observed.height,
                    "videoCodec": observed.video_codec, "audioCodec": observed.audio_codec,
                    "frameRate": observed.frame_rate, "frameCount": observed.frame_count},
            )
        except RemotePredictionFailed:
            return self.repository.record_video_remote_failed(project_id, video_job_id, "remote_prediction_failed")
        except RemoteOutcomeUnknown:
            return self.repository.record_video_outcome_unknown(project_id, video_job_id, "remote_outcome_unknown")
        except Exception as error:
            # A known prediction is still recoverable; this never regenerates.
            # Never persist provider body, URL, or exception text: those can
            # contain signed URLs and credentials.  Stable code is enough for
            # the operator to retry retrieval or inspect local safe evidence.
            code = (
                "audio_track_missing" if str(error) == "audio_track_missing"
                else error.code if isinstance(error, VideoOutputContractError)
                else "retrieval_or_probe_failed"
            )
            return self.repository.record_video_retrieve_needed(project_id, video_job_id, code)

    def _poll_current_backend(self, video_job_id: str, prediction_id: str) -> dict[str, Any]:
        """Poll first, then give adapter-owned profile parsing the payload."""

        self._assert_current_backend(video_job_id)
        return self.provider.poll(prediction_id)

    def _assert_current_backend(self, video_job_id: str) -> None:
        if self.verify_backend_binding is not None:
            self.verify_backend_binding(video_job_id)
