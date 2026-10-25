"""Durable bounded batch orchestration over existing video job owners."""
from contextlib import closing
from hashlib import sha256

from .exceptions import InvalidTransitionError
from .project_storage.delegated_qa_grants import qa_command
from .project_storage.project_video import ProjectVideoRepository
from .project_storage.proof_scope import scoped_proofs
from .project_storage.video_batch_grants import VideoBatchGrants
from .video_batch_directions import advance_directions, prepare_directions
from .video_batch_inventory import inventory, source_binding, validate_manifest
from .video_batch_review import confirm_pack, review_projection


class VideoBatchService:
    def __init__(self, storage, registry, video):
        self.storage, self.registry, self.video = storage, registry, video
        self.grants = VideoBatchGrants(storage.application)

    def require_video(self):
        if self.video is None:
            raise InvalidTransitionError("请先配置已验证的 H3 视频后端。")
        return self.video

    @scoped_proofs
    def setup(self, project_id, request):
        with closing(self.storage.projects.open(project_id)) as store:
            owner = store.repository.video_batches
            current = owner.current(project_id)
            if current and current["state"] not in {"approved", "cancelled", "retired"}:
                return current
            if current and current["execution"].get("draft") and current["execution"]["draft"]["attempt"]["state"] not in {"completed", "failed", "settled"}:
                raise InvalidTransitionError("the original directions attempt is unsettled; no replacement may be prepared")
            manifest = inventory(store, self.require_video(), request)
            current = owner.create(project_id, manifest)
            if not manifest["blockers"] and all(target["directions"] is not None for target in manifest["targets"]):
                current = owner.change(project_id, current["id"], mutate=lambda row: setattr(row, "state", "ready"))
            return current

    @scoped_proofs
    def draft(self, project_id, revision):
        with closing(self.storage.projects.open(project_id)) as store:
            view = store.repository.video_batches.current(project_id)
            if view is None:
                raise InvalidTransitionError("请先准备批次清单。")
            if view["state"] != "setup":
                return view
            if view["revision"] != revision:
                raise InvalidTransitionError("batch revision changed before drafting")
            validate_manifest(store, self.require_video(), view["manifest"], compiled=False)
            return prepare_directions(store, self.registry, self.grants, view)

    @scoped_proofs
    def replace_rejected(self, project_id, request):
        from .delegated_qa_video import assert_manifest_actor
        from .video_batch_replacement import replacement_inventory
        with closing(self.storage.projects.open(project_id)) as store, qa_command(store, self.storage.application, request.attribution):
            # Freeze predecessor CAS, retained history and successor in one native
            # command, before any fresh English endorsement or dispatch authority.
            with store.repository.manual_command():
                owner = store.repository.video_batches
                manifest = replacement_inventory(store, self.require_video(), owner.current(project_id), request)
                assert_manifest_actor(store, manifest, request.attribution)
                validate_manifest(store, self.require_video(), manifest, compiled=False)
                return owner.create(project_id, manifest)

    @scoped_proofs
    def edit_directions(self, project_id, revision, draft):
        from .creative_handoff_contracts import CreativeHandoffRequest
        from .video_directions_contract import bind_draft
        with closing(self.storage.projects.open(project_id)) as store:
            owner = store.repository.video_batches
            view = owner.current(project_id)
            if not view or view["state"] not in {"setup", "ready"} or view["execution"].get("authorizedManifestHash"):
                raise InvalidTransitionError("only an unstarted manifest can edit English directions")
            request = CreativeHandoffRequest(job_id="ch_" + "0" * 32, project_id=project_id,
                section_id=view["id"], stage="video-directions", expected_stage_revision=revision,
                source={"batchId": view["id"]}, input_artifacts={"video-targets.json": {"targets": [item for item in view["manifest"]["targets"] if item["mode"] == "generate"]}},
                creative_brief="Creator edits the exact displayed English draft.")
            rendered = bind_draft(request, draft.model_dump(mode="json", by_alias=True))
            def save(row):
                row.manifest = row.manifest | {"targets": [target | rendered.get(target["shotId"], {}) for target in row.manifest["targets"]]}
                row.state = "ready"
            return owner.change(project_id, view["id"], expected_revision=revision, mutate=save)

    @scoped_proofs
    def start(self, project_id, request):
        with closing(self.storage.projects.open(project_id)) as store, qa_command(store, self.storage.application, request.attribution):
            owner = store.repository.video_batches
            view = owner.current(project_id)
            if view is None:
                raise InvalidTransitionError("batch setup is missing")
            from .delegated_qa_video import assert_manifest_actor
            actor = assert_manifest_actor(store, view["manifest"], request.attribution)
            if view["execution"].get("authorizedManifestHash") == request.manifest_hash:
                if view["execution"].get("reviewAttribution") != actor:
                    raise InvalidTransitionError("retained English endorsement attribution differs")
                return view
            if view["state"] != "ready" or view["manifestHash"] != request.manifest_hash:
                raise InvalidTransitionError("review the current complete English manifest first")
            validate_manifest(store, self.require_video(), view["manifest"], links=view["execution"]["jobs"])
            self.grants.authorize(store, view["id"], view["manifestHash"])
            def authorize(row):
                if row.state != "ready":
                    raise InvalidTransitionError("batch is not ready")
                validate_manifest(store, self.require_video(), row.manifest)
                row.state = "running"
                row.execution = row.execution | {"authorizedManifestHash": row.manifest_hash,
                    **({"reviewAttribution": actor} if actor else {}),
                    "jobs": {target["shotId"]: target["jobId"] for target in row.manifest["targets"] if target["jobId"]},
                    "segments": {}, "error": None}
            with store.repository.manual_command():
                return owner.change(project_id, view["id"], expected_revision=request.expected_revision, control=True, mutate=authorize)

    @scoped_proofs
    def control(self, project_id, request):
        with closing(self.storage.projects.open(project_id)) as store:
            owner = store.repository.video_batches
            view = owner.current(project_id)
            if view is None:
                raise InvalidTransitionError("batch not found")
            if request.action == "resume":
                if view["execution"].get("authorizedManifestHash"):
                    self.grants.require(store, view["id"], view["manifestHash"])
                    validate_manifest(store, self.require_video(), view["manifest"], links=view["execution"]["jobs"])
                elif not view["execution"].get("draft"):
                    raise InvalidTransitionError("batch was not started")
            def change(row):
                if row.state in {"approved", "retired"}:
                    raise InvalidTransitionError("completed batch cannot be controlled")
                resumed = "running" if row.execution.get("authorizedManifestHash") else "ready" if all(target["directions"] is not None for target in row.manifest["targets"]) else "drafting"
                row.state = {"pause": "paused", "cancel": "cancelled", "resume": resumed}[request.action]
                row.execution = row.execution | {"error": None}
            with store.repository.manual_command():
                current = owner.current(project_id)
                if current["id"] != request.batch_id or current["controlRevision"] != request.expected_control_revision:
                    raise InvalidTransitionError("batch control revision changed")
                data = current["execution"].get("draft")
                if data and request.action in {"pause", "cancel"}:
                    from .codex_exec_contracts import CodexExecAttempt
                    attempt = CodexExecAttempt.model_validate(data["attempt"])
                    if attempt.state not in {"completed", "failed", "settled"}:
                        status = (self.registry.codex_exec_suspend if request.action == "pause" else self.registry.codex_exec_cancel)(attempt)
                        if request.action == "pause" and status.state in {"queued", "spawn_intent"} and status.dispatch_enabled is not False:
                            raise InvalidTransitionError("native directions pause has not fenced its exact unstarted attempt")
                return owner.change(project_id, view["id"], expected_revision=current["revision"], control=True, mutate=change)

    @scoped_proofs
    def current(self, project_id):
        with closing(self.storage.projects.read_open(project_id)) as store:
            view = store.repository.video_batches.current(project_id)
            if not view:
                return None
            if view["execution"].get("authorizedManifestHash"):
                states_by_id = store.repository.video_batches.job_states(project_id, list(view["execution"]["jobs"].values()))
                states = [states_by_id.get(identifier, "missing") for identifier in view["execution"]["jobs"].values()]
                view["progress"] = {"total": len(view["manifest"]["targets"]), "ready": len(view["execution"]["segments"]),
                    "failed": sum(state == "failed" for state in states),
                    "blocked": sum(state in {"outcome_unknown", "dispatching", "missing"} for state in states)}
            return view

    @scoped_proofs
    def review(self, project_id):
        with closing(self.storage.projects.read_open(project_id)) as store:
            view = store.repository.video_batches.current(project_id)
            if not view:
                raise InvalidTransitionError("batch not found")
            return review_projection(store, self.storage.application, view)

    @scoped_proofs
    def confirm(self, project_id, request):
        with closing(self.storage.projects.open(project_id)) as store, qa_command(store, self.storage.application, request.attribution):
            store.require_recovery_acknowledged()
            view = store.repository.video_batches.current(project_id)
            if not view:
                raise InvalidTransitionError("batch not found")
            return confirm_pack(store, self.storage.application, view, request)

    @scoped_proofs
    def step(self, project_id):
        with closing(self.storage.projects.open(project_id)) as store:
            owner = store.repository.video_batches
            # Observation belongs to retained predictions, not the latest dispatch grant.
            for identifier in owner.known_prediction_ids(project_id):
                self.require_video().reconcile(store, identifier)
                return
            view = owner.current(project_id)
            if not view or view["state"] in {"setup", "ready", "approved", "retired"}:
                return
            try:
                if view["execution"].get("draft") and not view["execution"].get("authorizedManifestHash"):
                    advance_directions(store, self.registry, self.grants, view, allow_admission=view["state"] == "drafting")
                    return
                self._advance_video(store, view)
            except InvalidTransitionError as error:
                # Fixed contract errors are safe product diagnostics, never raw provider output.
                message = str(error)
                current = owner.current(project_id)
                if current["revision"] == view["revision"] and current["state"] == view["state"]:
                    owner.change(project_id, view["id"], expected_revision=view["revision"], mutate=lambda row: self._block(row, message))

    @staticmethod
    def _block(row, message):
        row.state = "blocked"
        row.execution = row.execution | {"error": message}

    def _advance_video(self, store, view):
        video, project_id = self.require_video(), view["projectId"]
        owner = store.repository.video_batches
        # Observe existing predictions even while paused/cancelled/stale.
        jobs = {job["id"]: job for job in video.jobs(store)}
        for identifier in view["execution"]["jobs"].values():
            job = jobs.get(identifier)
            if job and job["state"] in {"submitted", "retrieve_needed"}:
                video.reconcile(store, identifier)
                return
        if view["state"] != "running":
            return
        self.grants.require(store, view["id"], view["manifestHash"])
        if source_binding(store) != view["manifest"]["sourceBinding"]:
            owner.change(project_id, view["id"], expected_revision=view["revision"], mutate=lambda row: setattr(row, "state", "stale"))
            return
        if video._configured_backend_binding().snapshot() != view["manifest"]["backend"]:
            raise InvalidTransitionError("frozen H3 backend configuration changed")
        repository = ProjectVideoRepository(store, self.storage.application)
        for target in view["manifest"]["targets"]:
            shot_id = target["shotId"]
            identifier = view["execution"]["jobs"].get(shot_id)
            job = jobs.get(identifier)
            if job is None:
                if identifier:
                    raise InvalidTransitionError("batch job disappeared; no replacement will be created")
                with store.repository.manual_command():
                    current = owner.current(project_id)
                    if current["state"] != "running":
                        return
                    from .video_batch_work_inventory import assert_work_inventory
                    with store.repository._read() as session:
                        assert_work_inventory(session, project_id, current["manifest"], current["execution"]["jobs"])
                    basis = {"version": "whole-batch-english.v1", "batchId": view["id"], "manifestHash": view["manifestHash"], "shotId": shot_id}
                    if view["execution"].get("reviewAttribution"):
                        basis["attribution"] = view["execution"]["reviewAttribution"]
                    directions = target["directions"] | {"reviewBasis": basis,
                        "promptSha256": sha256(target["compiledPrompt"].encode()).hexdigest()}
                    args = target["args"] | {"idempotency_key": f"batch-{view['id']}-{shot_id}"}
                    job = video.prepare(store, **args, reviewed_directions=directions)
                    owner.change(project_id, view["id"], mutate=lambda row: setattr(row, "execution", row.execution | {"jobs": row.execution["jobs"] | {shot_id: job["id"]}}))
                return
            if not job["current"]:
                raise InvalidTransitionError(f"{shot_id}: video source is stale")
            if job["state"] == "prepared":
                # Revalidate the entire authorization before the first call, then exact source at each claim.
                validate_manifest(store, video, view["manifest"], links=view["execution"]["jobs"])
                video.submit(store, identifier)
                return
            if job["state"] in {"failed", "cancelled", "outcome_unknown", "dispatching"}:
                raise InvalidTransitionError(f"{shot_id}: retained {job['state']} outcome blocks new attempts; inspect the original job")
            if job["state"] == "ingested" and shot_id not in view["execution"]["segments"]:
                if job["reviews"] and job["reviews"][-1]["decision"] == "reject":
                    raise InvalidTransitionError(f"{shot_id}: latest review rejected this take")
                frames = target["authoredDurationUnits"] * 24 // 1000
                eligible = [segment for segment in job["segments"] if segment["current"]]
                proposal = eligible[-1] if eligible else repository.prepare_video_segment(project_id, identifier,
                    in_frame=0, out_frame=frames, expected_selection_revision=target["selectionRevision"])
                owner.change(project_id, view["id"], mutate=lambda row: setattr(row, "execution", row.execution | {"segments": row.execution["segments"] | {shot_id: proposal["id"]}}))
                return
        owner.change(project_id, view["id"], expected_revision=view["revision"], mutate=lambda row: setattr(row, "state", "awaiting_review"))
