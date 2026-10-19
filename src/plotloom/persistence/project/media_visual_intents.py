"""Visual-intent history persistence for managed project assets."""

from __future__ import annotations

from typing import Any
from copy import deepcopy

from sqlalchemy import select

from ...domain import StageName, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError
from ..schema import ManagedAssetRow, VisualIntentRow
from .access import ProjectPersistenceAccess
from .drafts import ProjectDraftPersistence


class VisualIntentPersistence:
    """Own role-scoped visual-intent history and draft consumption."""

    def __init__(self, access: ProjectPersistenceAccess, drafts: ProjectDraftPersistence, admission, currentness) -> None:
        self._access = access
        self._drafts = drafts
        self._admission = admission
        self._currentness = currentness

    def create_visual_intent(
        self,
        project_id: str,
        asset_id: str,
        intent: dict[str, Any],
        *,
        target_shot_id: str | None = None,
        retained_target_binding_id: str | None = None,
        consumed_draft: tuple[str, int, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        from .autopilot_authority import require_human_command
        require_human_command(self._access)
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            asset = session.get(ManagedAssetRow, asset_id)
            if asset is None or asset.project_id != project_id:
                raise NotFoundError(f"managed asset not found: {asset_id}")
            if intent.get("attribution") is not None:
                if intent.get("role") != "shot_keyframe":
                    raise InvalidTransitionError("QA scope permits only the granted shot keyframes")
                from ...delegated_qa import require_qa_write
                require_qa_write(session, project_id, intent["attribution"], asset_id=asset_id, shot_id=target_shot_id)
            if consumed_draft is not None:
                entity_id, draft_revision, draft_payload = consumed_draft
                self._drafts._consume_exact_authoring_draft_in_session(
                    session,
                    project,
                    editor_scope="visual_intent",
                    entity_id=entity_id,
                    expected_draft_revision=draft_revision,
                    canonical_base_revision=self._access.rows.stage(
                        session, project_id, StageName.STORYBOARD
                    ).revision,
                    canonical_payload=draft_payload,
                )
            intent = dict(intent)
            if "sourceEndorsement" in intent:
                from ...autopilot_contracts import OperationScope
                from .handoff_intent_context import assert_source_intent
                authority = self._access.authority()
                if authority is None or authority.scope != OperationScope.HANDOFF:
                    raise InvalidTransitionError("saved source endorsement requires exact human handoff authority")
                assert_source_intent(session.connection().connection.driver_connection, project_id, intent)
            if "targetUse" in intent:
                raise ValueError("target use evidence is owned by trusted code")
            source_binding_id = intent.pop("sourceBindingId", None)
            retained_visual_intent_id = intent.pop("retainedVisualIntentId", None)
            if retained_visual_intent_id is not None:
                from .image_reviewed_use import retain_target_use
                if retained_target_binding_id is not None or intent.get("role") != "shot_keyframe":
                    raise ValueError("retained target intent requires one explicit target-use editing path")
                try:
                    intent["targetUse"] = retain_target_use(session, project_id, asset_id, target_shot_id,
                        retained_visual_intent_id, source_binding_id, self._admission, self._currentness)
                except (ValueError, TypeError, KeyError) as error:
                    raise InvalidTransitionError(str(error)) from error
            if retained_target_binding_id is not None:
                from ..schema import ReviewedShotBindingRow
                binding = session.get(ReviewedShotBindingRow, retained_target_binding_id)
                if (source_binding_id is not None or binding is None or binding.project_id != project_id
                        or binding.asset_id != asset_id or binding.shot_id != target_shot_id
                        or not self._admission.reviewed_binding_admission_eligible_in_session(session, project_id, binding)):
                    raise ValueError("retained target use requires the exact current displayed binding")
                retained = session.get(VisualIntentRow, binding.visual_intent_id)
                if retained is None or retained.intent.get("targetUse") is None:
                    raise ValueError("displayed binding has no explicit target use")
                intent["targetUse"] = deepcopy(retained.intent["targetUse"])
            if source_binding_id is not None and retained_visual_intent_id is None:
                from .image_reviewed_use import freeze_reviewed_source, freeze_target_context
                if intent.get("role") != "shot_keyframe" or target_shot_id is None:
                    raise ValueError("cross-shot use requires an explicit target shot keyframe")
                board = self._currentness._canonical._load_stage_payload(session, project_id, StageName.STORYBOARD)
                if target_shot_id not in {shot.id for shot in board.shots}:
                    raise ValueError("cross-shot intent requires a current target shot")
                source, source_asset = freeze_reviewed_source(session, project_id, source_binding_id,
                    target_shot_id, self._admission, self._currentness)
                if source_asset.id != asset_id:
                    raise ValueError("cross-shot intent must retain exact source pixels")
                intent["targetUse"] = {"kind": "cross_shot_initial_keyframe", "targetShotId": target_shot_id,
                    "source": source.model_dump(mode="json", by_alias=True),
                    "targetContext": freeze_target_context(session, project_id, target_shot_id,
                        source_binding_id, self._admission, self._currentness).model_dump(mode="json", by_alias=True)}
            previous = session.scalar(
                select(VisualIntentRow.revision)
                .where(VisualIntentRow.project_id == project_id, VisualIntentRow.asset_id == asset_id)
                .order_by(VisualIntentRow.revision.desc()).limit(1)
            ) or 0
            row = VisualIntentRow(
                id=new_id(), project_id=project_id, asset_id=asset_id,
                revision=previous + 1, intent=intent, created_at=utc_now(),
            )
            session.add(row)
            session.flush()
            return {"id": row.id, "assetId": asset_id, "revision": row.revision, "intent": row.intent}

    def list_visual_intents(self, project_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            rows = session.scalars(
                select(VisualIntentRow)
                .where(VisualIntentRow.project_id == project_id)
                .order_by(VisualIntentRow.asset_id, VisualIntentRow.revision.desc())
            ).all()
            # A single imported still can legitimately serve more than one
            # authoring role.  Currentness is role-scoped, so do not hide the
            # latest location reference behind a later shot-keyframe revision.
            from ...cross_shot_image_contracts import intent_stream
            latest: dict[tuple, VisualIntentRow] = {}
            for row in rows:
                latest.setdefault((row.asset_id, *intent_stream(row.intent)), row)
            result = []
            for row in latest.values():
                item = {"id": row.id, "assetId": row.asset_id, "revision": row.revision, "intent": row.intent}
                use = row.intent.get("targetUse")
                if use is not None:
                    from .image_reviewed_use import retain_target_use
                    try:
                        retain_target_use(session, project_id, row.asset_id, use["targetShotId"], row.id,
                            use["source"]["bindingId"], self._admission, self._currentness)
                        item["targetUseCurrent"] = True
                    except (ValueError, TypeError, KeyError, InvalidTransitionError, NotFoundError):
                        item["targetUseCurrent"] = False
                result.append(item)
            return result
