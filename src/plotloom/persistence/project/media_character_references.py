"""Character-reference decision persistence and currentness."""

from __future__ import annotations

from datetime import datetime
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from ...domain import StageName, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ..codec import _stored_utc, stable_hash
from ..schema import (
    CharacterReferenceDecisionRow,
    CharacterReferenceStateRow,
    ManagedAssetRow,
)
from .access import ProjectPersistenceAccess
from .canonical import ProjectCanonicalPersistence


class CharacterReferencePersistence:
    """Own selected character-reference facts and their session currentness."""

    def __init__(self, access: ProjectPersistenceAccess, canonical: ProjectCanonicalPersistence) -> None:
        self._access = access
        self._canonical = canonical

    @staticmethod
    def character_reference_context(character: Any) -> dict[str, Any]:
        """Freeze only identity-relevant canonical facts; display-name edits do not transfer identity."""

        payload = character.model_dump(mode="json", by_alias=True)
        return {
            "characterId": payload["id"],
            "description": payload["description"],
            "visualAnchors": payload["visualAnchors"],
            "traits": payload["traits"],
            "continuityRules": payload["continuityRules"],
            "allowedStates": payload["allowedStates"],
        }

    @staticmethod
    def _character_reference_state_in_session(
        session: Session, project_id: str, character_id: str, now: datetime
    ) -> CharacterReferenceStateRow:
        state = session.get(CharacterReferenceStateRow, (project_id, character_id))
        if state is None:
            state = CharacterReferenceStateRow(
                project_id=project_id, character_id=character_id, revision=0,
                active_decision_id=None, updated_at=now,
            )
            session.add(state)
            session.flush()
        return state

    @staticmethod
    def _reference_decision_dict(row: CharacterReferenceDecisionRow, *, current: bool) -> dict[str, Any]:
        return {
            "id": row.id, "projectId": row.project_id, "characterId": row.character_id,
            "referenceRevision": row.reference_revision, "characterContext": row.character_context,
            "characterContextHash": row.character_context_hash, "primaryAssetId": row.primary_asset_id,
            "complementaryAssetIds": list(row.complementary_asset_ids), "assetHashes": list(row.asset_hashes),
            "reviewer": row.reviewer, "notes": row.notes, "current": current,
            "revokedAt": _stored_utc(row.revoked_at).isoformat() if row.revoked_at else None,
            "revokedBy": row.revoked_by, "revocationReason": row.revocation_reason,
            "createdAt": _stored_utc(row.created_at).isoformat(),
        }

    def current_character_reference_in_session(
        self, session: Session, project_id: str, character: Any
    ) -> CharacterReferenceDecisionRow | None:
        state = session.get(CharacterReferenceStateRow, (project_id, character.id))
        if state is None or state.active_decision_id is None:
            return None
        decision = session.get(CharacterReferenceDecisionRow, state.active_decision_id)
        if decision is None or decision.project_id != project_id or decision.character_id != character.id:
            return None
        if decision.revoked_at is not None:
            return None
        context = self.character_reference_context(character)
        if decision.character_context_hash != stable_hash(context):
            return None
        asset_ids = [decision.primary_asset_id, *list(decision.complementary_asset_ids)]
        assets = [session.get(ManagedAssetRow, asset_id) for asset_id in asset_ids]
        if any(asset is None or asset.project_id != project_id for asset in assets):
            return None
        by_id = {item["assetId"]: item["originalHash"] for item in decision.asset_hashes}
        if any(asset is None or by_id.get(asset.id) != asset.original_hash for asset in assets):
            return None
        return decision

    def create_character_reference_decision(
        self,
        project_id: str,
        *,
        character_id: str,
        primary_asset_id: str,
        complementary_asset_ids: list[str],
        expected_reference_revision: int,
        reviewer: str,
        notes: str,
    ) -> dict[str, Any]:
        """Select, never infer, a compact stable-identity reference set."""

        with self._access.leases.lifecycle_write() as session:
            project = self._access.rows.project(session, project_id)
            self._access.guards.active(project)
            bible = self._canonical._load_stage_payload(session, project_id, StageName.STORY_BIBLE)
            character = next((item for item in bible.characters if item.id == character_id), None)
            if character is None:
                raise InvalidTransitionError("character reference must name a current canonical character")
            now = utc_now()
            state = self._character_reference_state_in_session(session, project_id, character_id, now)
            if state.revision != expected_reference_revision:
                raise RevisionConflictError("character-reference", expected_reference_revision, state.revision)
            asset_ids = [primary_asset_id, *complementary_asset_ids]
            if len(asset_ids) > 3 or len(asset_ids) != len(set(asset_ids)):
                raise InvalidTransitionError("character reference requires one primary and at most two distinct complementary assets")
            assets = [session.get(ManagedAssetRow, asset_id) for asset_id in asset_ids]
            if any(asset is None or asset.project_id != project_id for asset in assets):
                raise NotFoundError("character reference asset not found in this project")
            context = self.character_reference_context(character)
            state.revision += 1
            state.updated_at = now
            decision = CharacterReferenceDecisionRow(
                id=new_id(), project_id=project_id, character_id=character_id,
                reference_revision=state.revision, character_context=context,
                character_context_hash=stable_hash(context), primary_asset_id=primary_asset_id,
                complementary_asset_ids=complementary_asset_ids,
                asset_hashes=[{"assetId": asset.id, "originalHash": asset.original_hash} for asset in assets if asset is not None],
                reviewer=reviewer.strip(), notes=notes.strip(), revoked_at=None, revoked_by=None,
                revocation_reason=None, created_at=now,
            )
            session.add(decision)
            session.flush()
            state.active_decision_id = decision.id
            session.flush()
            return self._reference_decision_dict(decision, current=True) | {"stateRevision": state.revision}

    def revoke_character_reference_decision(
        self,
        project_id: str,
        *,
        character_id: str,
        expected_reference_revision: int,
        reviewer: str,
        reason: str,
    ) -> dict[str, Any]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            now = utc_now()
            state = self._character_reference_state_in_session(session, project_id, character_id, now)
            if state.revision != expected_reference_revision:
                raise RevisionConflictError("character-reference", expected_reference_revision, state.revision)
            if state.active_decision_id is None:
                raise InvalidTransitionError("character has no active reference decision to revoke")
            decision = session.get(CharacterReferenceDecisionRow, state.active_decision_id)
            if decision is None or decision.project_id != project_id:
                raise InvalidTransitionError("active character reference decision is unavailable")
            decision.revoked_at = now
            decision.revoked_by = reviewer.strip()
            decision.revocation_reason = reason.strip()
            state.revision += 1
            state.active_decision_id = None
            state.updated_at = now
            session.flush()
            return self._reference_decision_dict(decision, current=False) | {"stateRevision": state.revision}

    def list_character_reference_decisions(self, project_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            # The visual workbench is available from project creation, while a
            # Story Bible is an authored prerequisite for selecting a reference
            # (not for inspecting an empty history). Preserve hard failures for
            # a corrupt installed stage, but represent an uninstalled Story
            # Bible as an empty current-character set.
            bible_head = self._access.rows.stage(session, project_id, StageName.STORY_BIBLE)
            if bible_head.entity_revision_id is None:
                characters: dict[str, Any] = {}
            else:
                bible = self._canonical._load_stage_payload(
                    session, project_id, StageName.STORY_BIBLE
                )
                characters = {item.id: item for item in bible.characters}
            rows = session.scalars(
                select(CharacterReferenceDecisionRow)
                .where(CharacterReferenceDecisionRow.project_id == project_id)
                .order_by(CharacterReferenceDecisionRow.created_at.desc(), CharacterReferenceDecisionRow.id.desc())
            ).all()
            states = session.scalars(
                select(CharacterReferenceStateRow).where(CharacterReferenceStateRow.project_id == project_id)
            ).all()
            state_by_character = {item.character_id: item for item in states}
            return {
                "states": [{
                    "characterId": character_id, "revision": state.revision,
                    "activeDecisionId": state.active_decision_id,
                    "current": self.current_character_reference_in_session(session, project_id, characters[character_id]) is not None
                    if character_id in characters else False,
                } for character_id, state in sorted(state_by_character.items())],
                "decisions": [self._reference_decision_dict(
                    row,
                    current=(
                        row.revoked_at is None
                        and row.character_id in characters
                        and state_by_character.get(row.character_id) is not None
                        and state_by_character[row.character_id].active_decision_id == row.id
                        and self.current_character_reference_in_session(session, project_id, characters[row.character_id]) is not None
                    ),
                ) for row in rows],
            }
