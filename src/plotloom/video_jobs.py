"""Execution/ingestion orchestration for the separate P2 video lifecycle."""
from __future__ import annotations

from hashlib import sha256
from typing import Any, Callable

from .artifacts import ArtifactStore
from .persistence import SQLiteRepository
from .video_ingestion import ObservedVideo, assert_public_https_url, probe_video
from .video_provider import (
    AtlasWanAdapter,
    RemotePredictionFailed,
    VideoProviderError,
    VideoProviderPort,
    WanDispatchDiagnostic,
    WanDispatchError,
)


class VideoJobService:
    """Never retries POST; recovery only polls known prediction IDs."""

    def __init__(self, repository: SQLiteRepository, artifacts: ArtifactStore, provider: VideoProviderPort, *, probe: Callable[[bytes], ObservedVideo] = probe_video) -> None:
        self.repository, self.artifacts, self.provider, self.probe = repository, artifacts, provider, probe
        self.adapter = AtlasWanAdapter()

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

    def submit(self, project_id: str, video_job_id: str) -> dict[str, Any]:
        preflight = getattr(self.provider, "preflight", None)
        if callable(preflight):
            try:
                preflight()
            except Exception:
                # This happens before the durable dispatch boundary, so the
                # reservation is safely released and no remote POST occurs.
                return self.repository.cancel_video_job(project_id, video_job_id)
        job = self.repository.claim_video_dispatch(project_id, video_job_id)
        try:
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
            uploaded = self.provider.upload(image, mime_type=keyframe["mimeType"])
            try:
                payload = self.adapter.compile(
                    prompt=self._prompt(job["snapshot"]), image_url=uploaded,
                    duration=job["requestedSeconds"], resolution=job["snapshot"]["request"]["resolution"], audio=True,
                )
            except VideoProviderError as error:
                raise WanDispatchError(WanDispatchDiagnostic("request_compile", "local_precondition_failed")) from error
            submitted = self.provider.submit(payload)
            try:
                prediction = self.adapter.prediction_id(submitted)
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
            output = self.adapter.completed_output(self.provider.poll(job["providerPredictionId"]))
            if output is None:
                return job
            # A cancel intent retains known-ID reconciliation evidence but
            # never downloads, ingests, or adopts a candidate.
            if job.get("cancelRequestedAt"):
                return job
            assert_public_https_url(output)
            content = self.provider.download(output)
            observed = self.probe(content)
            if observed.audio_codec is None:
                raise ValueError("audio_track_missing")
            uri = self.artifacts.put(content)
            return self.repository.record_video_output(
                project_id, video_job_id, uri=uri, digest=sha256(content).hexdigest(),
                observed={"durationSeconds": observed.duration_seconds, "width": observed.width, "height": observed.height,
                    "videoCodec": observed.video_codec, "audioCodec": observed.audio_codec},
            )
        except RemotePredictionFailed:
            return self.repository.record_video_remote_failed(project_id, video_job_id, "remote_prediction_failed")
        except Exception as error:
            # A known prediction is still recoverable; this never regenerates.
            # Never persist provider body, URL, or exception text: those can
            # contain signed URLs and credentials.  Stable code is enough for
            # the operator to retry retrieval or inspect local safe evidence.
            code = "audio_track_missing" if str(error) == "audio_track_missing" else "retrieval_or_probe_failed"
            return self.repository.record_video_retrieve_needed(project_id, video_job_id, code)
