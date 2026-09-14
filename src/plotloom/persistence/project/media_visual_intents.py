"""Visual-intent history persistence for managed project assets."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ...domain import StageName, new_id, utc_now
from ...exceptions import NotFoundError
from ..schema import ManagedAssetRow, VisualIntentRow
from .access import ProjectPersistenceAccess
from .drafts import ProjectDraftPersistence


class VisualIntentPersistence:
    """Own role-scoped visual-intent history and draft consumption."""

    def __init__(self, access: ProjectPersistenceAccess, drafts: ProjectDraftPersistence) -> None:
        self._access = access
        self._drafts = drafts

    def create_visual_intent(
        self,
        project_id: str,
        asset_id: str,
        intent: dict[str, Any],
        *,
        consumed_draft: tuple[str, int, dict[str, Any]] | None = None,
    ) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            asset = session.get(ManagedAssetRow, asset_id)
            if asset is None or asset.project_id != project_id:
                raise NotFoundError(f"managed asset not found: {asset_id}")
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
            latest: dict[tuple[str, str | None], VisualIntentRow] = {}
            for row in rows:
                latest.setdefault((row.asset_id, row.intent.get("role")), row)
            return [
                {"id": row.id, "assetId": row.asset_id, "revision": row.revision, "intent": row.intent}
                for row in latest.values()
            ]
