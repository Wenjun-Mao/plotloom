"""Current-format batch evidence admission; no dispatch or inferred approval."""
import json

from ..exceptions import InvalidTransitionError
from ..persistence.codec import stable_hash
from ..provider_budgets import budget_within_authority, exceeds_budget
from ..video_backends.minimax_h3.directions import (
    direction_sources,
    validate_direction_fields,
)
from ..video_batch_contracts import BatchDirectionsTarget, BatchSetup
from .format import ProjectStorageCorruptionError

STATES = {"setup", "drafting", "checking", "translation_rejected", "ready", "running", "paused", "cancelled", "blocked", "stale", "awaiting_review", "approved", "retired"}


def assert_video_batch_contracts(connection):
    if not connection.execute("SELECT 1 FROM sqlite_master WHERE type='table' AND name='v2_video_batches'").fetchone():
        return
    try:
        for identifier, project_id, revision, state, raw, digest, execution_raw in connection.execute("SELECT id,project_id,revision,state,manifest,manifest_hash,execution FROM v2_video_batches"):
            manifest, execution = json.loads(raw), json.loads(execution_raw)
            if (revision < 1 or state not in STATES or manifest.get("version") not in {"video-batch.manifest.v1", "video-batch.manifest.v2"}
                    or manifest.get("projectId") != project_id or stable_hash(manifest) != digest):
                raise ValueError("batch identity or current format changed")
            if not {"maxJobs", "maxRequestedSeconds"}.issubset(manifest["setup"]):
                raise ValueError("frozen batch setup requires explicit maxJobs and maxRequestedSeconds; null means unlimited")
            setup = BatchSetup.model_validate(manifest["setup"])
            if "wholeTakePlayback" in manifest and manifest["wholeTakePlayback"] is not (
                    setup.single_request is None or setup.single_request.playback_intent in (None, "whole_take")):
                raise ValueError("batch playback policy differs from its frozen setup")
            from ..video_batch_replacement import assert_rejected_history
            assert_rejected_history(lambda sql, params: connection.execute(sql, params).fetchall(), project_id, manifest)
            ids = [target["shotId"] for target in manifest["targets"]] + [fact["shotId"] for fact in manifest["kept"]]
            blocker_ids = [item["shotId"] for item in manifest["blockers"] if item["shotId"]]
            if len(ids) != len(set(ids)) or sorted(set(ids + blocker_ids)) != manifest["scopeShotIds"]:
                raise ValueError("batch unique all-route scope changed")
            planned = [target for target in manifest["targets"] if target["mode"] in {"generate", "prepared"}]
            if manifest["newJobs"] != len(planned) or manifest["requestedSeconds"] != sum(target["requestedSeconds"] for target in planned):
                raise ValueError("batch workload counts changed")
            for target in manifest["targets"]:
                if target["mode"] not in {"generate", "prepared", "observe", "reuse"}:
                    raise ValueError("batch work mode is invalid")
                args, request = target["args"], target["snapshot"]["request"]
                if (target["requestedSeconds"] != args["requested_seconds"] or target["requestedSeconds"] != request["durationSeconds"]
                        or target["requestedFrames"] != request["frameCount"] or args["seed"] != request["seed"]
                        or target["authoredDurationUnits"] != target["snapshot"]["sourceTiming"]["durationUnits"]):
                    raise ValueError("batch frozen workload differs from its native request")
                source = direction_sources(target["snapshot"])
                if source["sourceHash"] != target["sourceHash"] or source["sources"] != target["sources"] or target["snapshot"]["shot"]["id"] != target["shotId"]:
                    raise ValueError("batch source binding changed")
                if target["directions"] is not None:
                    BatchDirectionsTarget.model_validate({key: target["directions"][key] for key in ("sourceHash", "fields")} | {"shotId": target["shotId"]})
                    validate_direction_fields(target["snapshot"], target["directions"])
                    if not isinstance(target["compiledPrompt"], str) or not target["compiledPrompt"].strip():
                        raise ValueError("batch compiled prompt is missing")
            if execution.get("authorizedManifestHash") is not None and (execution["authorizedManifestHash"] != digest or manifest["blockers"]
                    or exceeds_budget(manifest["newJobs"], setup.max_jobs) or exceeds_budget(manifest["requestedSeconds"], setup.max_requested_seconds)):
                raise ValueError("batch authorization or limits changed")
            if manifest.get("version") == "video-batch.manifest.v2":
                from ..production_brief_contract import assert_frozen_brief
                for target in manifest["targets"]:
                    if "languageContract" in target["snapshot"]:
                        assert_frozen_brief(target["snapshot"], target.get("productionBrief"))
                for target in manifest["targets"]:
                    reference = (target.get("directions") or {}).get("fidelityCheck")
                    required = target["mode"] in {"generate", "prepared"} and (state == "ready" or execution.get("authorizedManifestHash"))
                    if required and not reference:
                        raise ValueError("new ready target lacks independent fidelity evidence")
                    if reference:
                        from ..video_fidelity_contracts import FidelityReference
                        from ..video_fidelity import validate_retained_fidelity
                        parsed = FidelityReference.model_validate(reference)
                        owner = connection.execute("SELECT project_id,execution,manifest FROM v2_video_batches WHERE id=?", (parsed.batch_id,)).fetchone()
                        if owner is None or owner[0] != project_id:
                            raise ValueError("fidelity evidence owner changed")
                        check = validate_retained_fidelity(json.loads(owner[1]).get("fidelity"), project_id,
                            parsed.batch_id, target, parsed, manifest=json.loads(owner[2]), require_pass=bool(required))
                        if target.get("fidelity") not in (None, check):
                            raise ValueError("displayed fidelity verdict changed")
                if execution.get("authorizedManifestHash"):
                    from ..video_batch_operator import retained_production_actor
                    retained_production_actor(project_id, execution)
                if execution.get("authorizedManifestHash") and execution.get("intentReviewVersion") != "production-intent.v2":
                    raise ValueError("new batch lacks production-intent authorization")
            if execution.get("reviewAttribution"):
                from ..delegated_qa import require_scope
                from ..delegated_qa_video import assert_snapshot
                scope = require_scope(project_id, execution["reviewAttribution"])
                if (not execution.get("authorizedManifestHash") or not budget_within_authority(setup.max_jobs, scope.max_submissions)
                        or not budget_within_authority(setup.max_requested_seconds, scope.max_requested_seconds) or setup.profile_id != scope.profile_id
                        or not set(manifest["scopeShotIds"]).issubset({item.shot_id for item in scope.materials})):
                    raise ValueError("QA batch scope changed")
                for target in manifest["targets"]:
                    assert_snapshot(scope, target["snapshot"])
            if type(execution.get("controlRevision")) is not int or execution["controlRevision"] < 1:
                raise ValueError("batch command authority revision is invalid")
            if not set(execution["jobs"]).issubset(ids) or not set(execution["segments"]).issubset(execution["jobs"]):
                raise ValueError("batch execution links changed")
            from .video_retry_evidence import assert_video_retry_evidence
            assert_video_retry_evidence(connection, project_id, manifest, execution)
            for shot_id, job_id in execution["jobs"].items():
                job = connection.execute("SELECT project_id,snapshot FROM v2_video_jobs WHERE id=?", (job_id,)).fetchone()
                snapshot = json.loads(job[1]) if job is not None else None
                shot = snapshot.get("shot") if isinstance(snapshot, dict) else None
                if job is None or job[0] != project_id or not isinstance(shot, dict) or shot.get("id") != shot_id:
                    raise ValueError("batch job lineage changed")
                package = snapshot.get("reviewedDirections") or {}
                if not isinstance(package, dict):
                    raise ValueError("generation authorization package changed")
                basis = package.get("reviewBasis") or {}
                if not isinstance(basis, dict):
                    raise ValueError("generation authorization basis changed")
                if basis.get("version") == "production-intent.v2":
                    origin = connection.execute("SELECT project_id,execution FROM v2_video_batches WHERE id=?", (basis.get("batchId"),)).fetchone()
                    if origin is None or origin[0] != project_id:
                        raise ValueError("generation authorization owner changed")
                    from ..video_batch_operator import assert_authorization_operator
                    assert_authorization_operator(project_id, json.loads(origin[1]), package.get("intentAuthorization"))
        from .video_batch_evidence import retained_batch_drafts
        retained_batch_drafts(connection)
        from .video_batch_successor_evidence import validate_successor_links
        validate_successor_links(connection)
        for identifier, batch_id, raw, digest in connection.execute("SELECT id,batch_id,receipt,receipt_hash FROM v2_video_batch_receipts"):
            receipt = json.loads(raw)
            batch = connection.execute("SELECT project_id,manifest,manifest_hash,execution FROM v2_video_batches WHERE id=?", (batch_id,)).fetchone()
            if (batch is None or receipt.get("id") != identifier or receipt.get("batchId") != batch_id or receipt.get("projectId") != batch[0]
                    or stable_hash(receipt) != digest or receipt.get("version") not in {"whole-pack-video-native-audio.v1", "source-bound-selections.v1"}
                    or (receipt.get("version") == "whole-pack-video-native-audio.v1" and receipt.get("confirmation") != {"clips": True, "nativeAudio": True, "intent": True, "windows": True})
                    or receipt.get("manifestHash") != batch[2]):
                raise ValueError("video pack human confirmation changed")
            from ..delegated_qa_video import assert_receipt_actor
            assert_receipt_actor(batch[0], receipt, json.loads(batch[3]).get("reviewAttribution"),
                historical=receipt.get("version") == "whole-pack-video-native-audio.v1")
            manifest = json.loads(batch[1])
            if receipt["kept"] != manifest["kept"] or [fact["shotId"] for fact in receipt["selections"]] != [target["shotId"] for target in manifest["targets"]]:
                raise ValueError("video pack confirmation is incomplete")
            for fact in receipt["selections"]:
                row = connection.execute("SELECT project_id,shot_id,video_job_id,derivative_hash FROM v2_video_segments WHERE id=?", (fact["segmentId"],)).fetchone()
                if row != (batch[0], fact["shotId"], fact["jobId"], fact["derivativeHash"]):
                    raise ValueError("video pack confirmation has no native segment proof")
    except (ValueError, TypeError, KeyError, InvalidTransitionError) as error:
        raise ProjectStorageCorruptionError("project video batch contract is unsupported or corrupt; no evidence was rewritten") from error
