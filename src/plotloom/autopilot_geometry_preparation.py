"""Idempotent local geometry checkpoints, with no native dispatch identity."""
from hashlib import sha256
from sqlalchemy import select
from .autopilot_contracts import CheckpointEvidence, CommandAuthority, OperationScope, ProvisionalFrame
from .geometry_preparation_contracts import GeometryAsset, GeometryPreparation, GeometrySource
from .geometry_preparation import geometry_runtime, prepare_geometry
from .exceptions import InvalidTransitionError
from .managed_media import publish_import
from .persistence.codec import stable_hash
from .persistence.schema import (AutopilotCheckpointRow, AutopilotDecisionRow, AutopilotFrameRow,
    ImageJobRow, ImageJobCandidateRow, ImageJobDeliveryRow, ProductionUnitRow, ManagedAssetRow)
from .persistence.project.image_source_lineage import current_source_in_session


def prepare_first_frame_geometry(store, view, claim, subject, inventory, original):
    key = subject.operation_key + ":geometry"
    repository = store.repository
    with repository.autopilot_command(CommandAuthority(view.id, claim, OperationScope.GEOMETRY)):
        with repository._read() as session:
            retained = session.scalar(select(AutopilotCheckpointRow).where(AutopilotCheckpointRow.run_id == view.id,
                AutopilotCheckpointRow.operation_key == key))
            if retained is None:
                policy = view.policy.geometry_preparation
                if policy is None or policy.runtime != geometry_runtime():
                    raise InvalidTransitionError("geometry runtime differs from frozen policy")
                source_asset_id = original["evidence"]["result"]["assetId"]
                source = current_source_in_session(session, view.project_id, source_asset_id, repository._media.image_currentness, shot_id=subject.id)
                if source is None or source.kind != "native_output":
                    raise InvalidTransitionError("geometry requires one exact raw native output")
                raw = session.get(ManagedAssetRow, source_asset_id)
                job = session.get(ImageJobRow, source.job_id)
                candidate = session.get(ImageJobCandidateRow, source.candidate_id)
                delivery = session.get(ImageJobDeliveryRow, candidate.delivery_id)
                selection = session.scalar(select(AutopilotDecisionRow).where(AutopilotDecisionRow.checkpoint_id == original["id"],
                    AutopilotDecisionRow.scope == OperationScope.SELECT.value))
                if selection is None:
                    raise InvalidTransitionError("geometry requires its source's exact provisional decision")
                content = store.artifacts.get(raw.original_uri)
                if sha256(content).hexdigest() != raw.original_hash:
                    raise InvalidTransitionError("geometry raw content does not match its exact source hash")
                output, observed, recipe = prepare_geometry(content, width=view.policy.image_width, height=view.policy.image_height)
                if (raw.original_hash, raw.width, raw.height) != (source.source_hash, recipe.oriented_height if recipe.exif_orientation >= 5 else recipe.oriented_width,
                        recipe.oriented_width if recipe.exif_orientation >= 5 else recipe.oriented_height):
                    raise InvalidTransitionError("geometry raw source bytes changed")
                preparation_id = stable_hash({"runId": view.id, "operationKey": key})
                asset = repository._media.assets.record_managed_import(view.project_id, original_hash=observed.content_hash,
                    display_hash=observed.display_hash, mime_type=observed.mime_type, byte_size=observed.byte_size,
                    width=observed.width, height=observed.height,
                    declaration={"origin": "plotloom_geometry_preparation", "preparationId": preparation_id},
                    publish=lambda: publish_import(store.artifacts, output, observed))
                native = GeometrySource(asset=GeometryAsset(asset_id=raw.id, original_hash=raw.original_hash, width=raw.width, height=raw.height),
                    checkpoint_id=original["id"], decision_id=selection.id, candidate_id=candidate.id, job_id=job.id,
                    request_hash=job.request_hash, delivery_row_id=delivery.id, delivery_id=delivery.delivery_id,
                    manifest_hash=delivery.manifest_hash, execution_pin=original["evidence"]["executionPin"])
                payload = {"preparationId": preparation_id, "projectId": view.project_id, "runId": view.id,
                    "policyHash": stable_hash(view.policy.model_dump(mode="json", by_alias=True)), "claim": claim, "shotId": subject.id,
                    "source": native.model_dump(mode="json", by_alias=True), "recipe": recipe.model_dump(mode="json", by_alias=True),
                    "recipeHash": stable_hash(recipe.model_dump(mode="json", by_alias=True)), "runtime": policy.runtime.model_dump(mode="json", by_alias=True),
                    "output": GeometryAsset(asset_id=asset["id"], original_hash=asset["originalHash"], width=asset["width"], height=asset["height"]).model_dump(mode="json", by_alias=True),
                    "version": "geometry-preparation.v1"}
                record = GeometryPreparation.model_validate(payload | {"preparationHash": stable_hash(payload)})
                retained = repository.autopilot.checkpoint(key, state="adopted", evidence=CheckpointEvidence(owner="geometry-preparation", subject_id=subject.id,
                    geometry_preparation=record))
                repository.autopilot.decide(retained, subject={"preparationHash": record.preparation_hash},
                    rationale="冻结的确定性居中裁剪与缩放；保留原图，不构成视觉改善或人类身份审阅。")
            record = CheckpointEvidence.model_validate(retained.evidence).geometry_preparation
    select_geometry_frame(store, view, claim, subject, inventory, record)


def select_geometry_frame(store, view, claim, subject, inventory, record):
    repository = store.repository
    with repository.autopilot_command(CommandAuthority(view.id, claim, OperationScope.SELECT)):
        with repository._read() as session:
            source = current_source_in_session(session, view.project_id, record.output.asset_id, repository._media.image_currentness, shot_id=subject.id)
            if source is None or source.geometry != record:
                raise InvalidTransitionError("geometry source lineage changed before selection")
            existing = session.scalar(select(AutopilotFrameRow).where(AutopilotFrameRow.run_id == view.id, AutopilotFrameRow.shot_id == subject.id))
            if existing:
                if ProvisionalFrame.model_validate(existing.frame).geometry_preparation != record:
                    raise InvalidTransitionError("geometry cannot replace an existing provisional frame")
                return
            checkpoint = session.scalar(select(AutopilotCheckpointRow).where(AutopilotCheckpointRow.run_id == view.id,
                AutopilotCheckpointRow.operation_key == subject.operation_key + ":geometry"))
            decision = repository.autopilot.decide(checkpoint, subject={"preparationHash": record.preparation_hash},
                selected_assets=[{"assetId": record.output.asset_id, "originalHash": record.output.original_hash}],
                rationale="暂选确定性处理的新字节；完整素材仍待真实人工审阅。")
            job = session.get(ImageJobRow, source.job_id)
            unit = session.get(ProductionUnitRow, job.production_unit_id)
            repository.autopilot.select_frame(ProvisionalFrame(shot_id=subject.id, scene_id=subject.scene_id,
                job_id=job.id, request_hash=job.request_hash, asset_id=record.output.asset_id, original_hash=record.output.original_hash,
                width=record.output.width, height=record.output.height, geometry_preparation=record,
                storyboard_revision=inventory.storyboard_revision, storyboard_hash=inventory.storyboard_hash,
                character_identity=unit.snapshot["characterIdentity"]), decision_id=decision)
            repository.autopilot.progress("first-frames")
