"""Durable, source-bound attempts for provisional F5 bridge intent."""
from __future__ import annotations

from typing import Any

from sqlalchemy import select

from ...domain import StageName, new_id, utc_now
from ...exceptions import InvalidTransitionError, RevisionConflictError
from ...production_bridge_contracts import ProductionBridgeConflict, ProductionBridgeIntentPackage
from ..schema.project_production_bridge import (
    ProductionBridgeIntentJobRow, ProductionBridgeRevisionRow,
)
from .access import ProjectPersistenceAccess
from .production_bridge import ProductionBridgePersistence


class ProductionBridgeIntentPersistence:
    """Jobs never write a canonical head; only a fresh review revision."""

    def __init__(self, access: ProjectPersistenceAccess, bridge: ProductionBridgePersistence) -> None:
        self._access = access
        self._bridge = bridge

    @staticmethod
    def _job(session: Any, project_id: str, job_id: str) -> ProductionBridgeIntentJobRow:
        job = session.get(ProductionBridgeIntentJobRow, job_id)
        if job is None or job.project_id != project_id:
            raise InvalidTransitionError("bridge inference job is unavailable")
        return job

    @staticmethod
    def _revision(session: Any, project_id: str, revision: int) -> ProductionBridgeRevisionRow:
        row = session.scalar(select(ProductionBridgeRevisionRow).where(
            ProductionBridgeRevisionRow.project_id == project_id,
            ProductionBridgeRevisionRow.revision == revision,
        ))
        if row is None:
            raise InvalidTransitionError("bridge proposal revision is unavailable")
        return row

    def source_context(
        self, project_id: str, *, expected_revision: int, expected_hash: str,
    ) -> tuple[dict[str, Any], list[dict[str, Any]]]:
        """Read a bounded exact source view without F5 H3 provider prompts."""

        with self._access.leases.read() as session:
            project = self._access.rows.project(session, project_id)
            head = self._bridge._head(session, project_id)
            if head.revision != expected_revision or head.status == "accepted":
                raise RevisionConflictError("production bridge", expected_revision, head.revision)
            row = self._revision(session, project_id, expected_revision)
            if row.content_hash != expected_hash or self._bridge._current(session, project_id, row.inputs):
                raise InvalidTransitionError("bridge source or proposal changed before inference")
            _inputs, _storyboard, script, _cast_art = self._bridge._context(session, project_id)
            graph = self._bridge._canonical._load_stage_payload(session, project_id, StageName.STORY_GRAPH)
            nodes = {node.id: node for node in getattr(graph, "nodes", [])}
            episodes = {item.get("ep"): item for item in script.get("episodes", []) if isinstance(item, dict)}
            targets = list(row.proposal["intentPackage"]["entries"])
            source_scenes: list[dict[str, Any]] = []
            for scene in row.proposal["scenes"]:
                section_id, episode, index = scene["sectionId"], scene["episode"], scene["sceneIndex"]
                f4_scenes = episodes.get(episode, {}).get("scenes", [])
                f4_scene = f4_scenes[index - 1] if 0 < index <= len(f4_scenes) else None
                node = nodes.get(section_id)
                cuts = [
                    {key: cut.get(key) for key in ("frame", "beats", "seconds", "cutIndex")}
                    for cut in row.proposal["cuts"]
                    if cut.get("sectionId") == section_id and cut.get("episode") == episode
                    and cut.get("sceneIndex") == index
                ]
                source_scenes.append({
                    "sceneId": scene["sceneId"], "sectionId": section_id,
                    "episode": episode, "sceneIndex": index,
                    "storyNode": node.model_dump(mode="json", by_alias=True) if node is not None else None,
                    "scriptScene": f4_scene, "cuts": cuts,
                })
            context = {"brief": project.brief, "scenes": source_scenes}
            prompt_targets = [{
                "id": item["id"], "targetKind": item["targetKind"],
                "sourceExcerpt": item["suggestedText"],
            } for item in targets]
            return context, prompt_targets

    def enqueue(
        self, project_id: str, *, expected_revision: int, expected_hash: str,
        profile_snapshot: dict[str, Any], prompt_trace: dict[str, Any],
        prompt_messages: list[dict[str, Any]], response_schema: dict[str, Any],
    ) -> str:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head = self._bridge._head(session, project_id)
            if head.revision != expected_revision or head.status == "accepted":
                raise RevisionConflictError("production bridge", expected_revision, head.revision)
            row = self._revision(session, project_id, expected_revision)
            if row.content_hash != expected_hash or self._bridge._current(session, project_id, row.inputs):
                raise InvalidTransitionError("bridge source or proposal changed before inference enqueue")
            active = session.scalar(select(ProductionBridgeIntentJobRow).where(
                ProductionBridgeIntentJobRow.project_id == project_id,
                ProductionBridgeIntentJobRow.status.in_(("queued", "dispatched")),
            ).limit(1))
            if active is not None:
                raise InvalidTransitionError("one bridge inference job is already active")
            now, job_id = utc_now(), new_id()
            session.add(ProductionBridgeIntentJobRow(
                id=job_id, project_id=project_id, status="queued",
                proposal_revision=expected_revision, proposal_content_hash=expected_hash,
                inputs=row.inputs, profile_snapshot=profile_snapshot,
                prompt_trace=prompt_trace, prompt_messages=prompt_messages,
                response_schema=response_schema,
                expected_entries=list(row.proposal["intentPackage"]["entries"]),
                created_at=now, updated_at=now,
            ))
            return job_id

    def load_job(self, project_id: str, job_id: str) -> dict[str, Any]:
        with self._access.leases.read() as session:
            job = self._job(session, project_id, job_id)
            return {
                "status": job.status, "profile": job.profile_snapshot,
                "messages": job.prompt_messages, "schema": job.response_schema,
                "expectedIds": [item["id"] for item in job.expected_entries],
                "promptHash": job.prompt_trace["rendered_hash"],
            }

    def expected_entries(self, project_id: str, job_id: str) -> list[dict[str, Any]]:
        with self._access.leases.read() as session:
            return list(self._job(session, project_id, job_id).expected_entries)

    def mark_dispatched(self, project_id: str, job_id: str) -> bool:
        """Commit intent immediately before the non-idempotent provider call."""

        with self._access.leases.lifecycle_write() as session:
            job = self._job(session, project_id, job_id)
            if job.status != "queued":
                return False
            head = self._bridge._head(session, project_id)
            if head.status == "accepted" or head.revision != job.proposal_revision:
                job.status, job.updated_at = "stale", utc_now()
                return False
            row = self._revision(session, project_id, job.proposal_revision)
            if row.content_hash != job.proposal_content_hash or self._bridge._current(session, project_id, job.inputs):
                job.status, job.updated_at = "stale", utc_now()
                return False
            job.status, job.dispatched_at, job.updated_at = "dispatched", utc_now(), utc_now()
            return True

    def finish_success(
        self, project_id: str, job_id: str, *, suggestions: dict[str, str],
        response_evidence: dict[str, Any], response_hash: str,
        provider_request_id: str | None, usage: dict[str, Any] | None,
    ) -> None:
        with self._access.leases.lifecycle_write() as session:
            job = self._job(session, project_id, job_id)
            if job.status not in {"dispatched", "cancelled"}:
                return
            job.response_evidence = response_evidence
            job.response_hash = response_hash
            job.provider_request_id = provider_request_id
            job.usage = usage
            job.candidate = {"entries": [{"id": key, "suggestedText": value} for key, value in suggestions.items()]}
            job.updated_at = utc_now()
            if job.status == "cancelled":
                return
            head = self._bridge._head(session, project_id)
            if head.status == "accepted" or head.revision != job.proposal_revision:
                job.status = "stale"
                return
            row = self._revision(session, project_id, job.proposal_revision)
            if row.content_hash != job.proposal_content_hash or self._bridge._current(session, project_id, job.inputs):
                job.status = "stale"
                return
            package = ProductionBridgeIntentPackage.model_validate(row.proposal["intentPackage"])
            if set(suggestions) != {entry.id for entry in package.entries}:
                job.status, job.error_code = "failed", "intent.target_mismatch"
                return
            provenance = {
                "jobId": job.id, "profileId": job.profile_snapshot["profileId"],
                "profileVersion": job.profile_snapshot["profileVersion"],
                "profileHash": job.profile_snapshot["profileHash"],
                "promptTrace": job.prompt_trace, "responseHash": response_hash,
                "providerRequestId": provider_request_id, "usage": usage,
            }
            updated = ProductionBridgeIntentPackage(
                method="model_inference.v1", provenance=provenance,
                entries=[entry.model_copy(update={
                    "method": "model_inference.v1", "suggested_text": suggestions[entry.id],
                    "text": suggestions[entry.id],
                }) for entry in package.entries],
            )
            payload = self._bridge._apply_intent_package(row.proposal["payload"], updated)
            conflicts = [ProductionBridgeConflict.model_validate(item) for item in row.conflicts
                         if item.get("code") not in {"dramatic_intent_required", "canonical_validation"}]
            conflicts.extend(self._bridge._validate_payload(session, project_id, payload))
            proposal = {**row.proposal, "payload": payload, "intentPackage": updated.model_dump(mode="json", by_alias=True)}
            digest, now = self._bridge._proposal_digest(row.inputs, proposal, conflicts), utc_now()
            head.revision += 1
            head.status, head.updated_at = "ready", now
            session.add(ProductionBridgeRevisionRow(
                id=new_id(), project_id=project_id, revision=head.revision,
                content_hash=digest, inputs=row.inputs, proposal=proposal,
                conflicts=[item.model_dump(mode="json") for item in conflicts],
                installable=not conflicts, prepared_at=now,
            ))
            job.status, job.result_proposal_revision, job.updated_at = "ready", head.revision, now

    def record_response(
        self, project_id: str, job_id: str, *, response_evidence: dict[str, Any],
        response_hash: str, provider_request_id: str | None, usage: dict[str, Any] | None,
    ) -> None:
        """Keep spent-attempt evidence even if local extraction or binding fails."""

        with self._access.leases.lifecycle_write() as session:
            job = self._job(session, project_id, job_id)
            if job.status not in {"dispatched", "cancelled"}:
                return
            job.response_evidence = response_evidence
            job.response_hash = response_hash
            job.provider_request_id = provider_request_id
            job.usage = usage
            job.updated_at = utc_now()

    def finish_failure(self, project_id: str, job_id: str, *, status: str, code: str, message: str) -> None:
        with self._access.leases.lifecycle_write() as session:
            job = self._job(session, project_id, job_id)
            if job.status not in {"queued", "dispatched"}:
                return
            job.status, job.error_code, job.error_message, job.updated_at = status, code, message[:500], utc_now()

    def cancel(self, project_id: str, job_id: str) -> None:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            job = self._job(session, project_id, job_id)
            if job.status in {"queued", "dispatched"}:
                job.status, job.updated_at = "cancelled", utc_now()

    def reconcile_dispatched(self, project_id: str) -> None:
        """After process loss, never auto-retry a possibly billed attempt."""

        with self._access.leases.lifecycle_write() as session:
            for job in session.scalars(select(ProductionBridgeIntentJobRow).where(
                ProductionBridgeIntentJobRow.project_id == project_id,
                ProductionBridgeIntentJobRow.status == "dispatched",
            )):
                job.status, job.error_code, job.updated_at = "outcome_unknown", "provider.outcome_unknown", utc_now()
