"""Focused F3A owner for source-bound, reviewable upstream art proposals."""
from __future__ import annotations

from hashlib import sha256
from typing import Any

from sqlalchemy import select

from ...art_contracts import (
    AcceptedArtRevision, ArtAcceptRequest, ArtBinding, ArtCandidate,
    ArtReopenRequest, ArtReviewState, ArtSaveRequest,
)
from ...creative_handoff_contracts import CreativeHandoffError, CreativeHandoffRequest
from ...creative_handoff_exchange import ValidatedCreativeDelivery, canonical_json
from ...domain import contains_secret_setting, contains_secret_value, new_id, utc_now
from ...exceptions import InvalidTransitionError, NotFoundError, RevisionConflictError
from ..schema.project_art import ArtCandidateRow, ArtHeadRow, ArtRevisionRow
from ..schema.project_cast import CastRevisionRow
from .access import ProjectPersistenceAccess
from .cast import ProjectCastPersistence


class ProjectArtPersistence:
    """One candidate/accepted art authority; it never creates media assets."""

    def __init__(self, access: ProjectPersistenceAccess, cast: ProjectCastPersistence) -> None:
        self._access, self._cast = access, cast

    def initialize(self, session: Any, project_id: str, *, created_at: Any) -> None:
        if session.get(ArtHeadRow, project_id) is None:
            session.add(ArtHeadRow(project_id=project_id, revision=0, candidate_job_id=None, status="missing", updated_at=created_at))

    @staticmethod
    def _candidate(row: ArtCandidateRow) -> ArtCandidate:
        return ArtCandidate(job_id=row.job_id, expected_art_revision=row.expected_art_revision, binding=row.binding, status=row.status, delivery_id=row.delivery_id, manifest_hash=row.manifest_hash, art=row.art, report_available=row.report_html is not None, created_at=row.created_at, delivered_at=row.delivered_at)

    @staticmethod
    def _accepted(row: ArtRevisionRow) -> AcceptedArtRevision:
        return AcceptedArtRevision(revision=row.revision, candidate_job_id=row.candidate_job_id, content_hash=row.content_hash, binding=row.binding, art=row.art, accepted_at=row.accepted_at)

    @staticmethod
    def _head(session: Any, project_id: str) -> ArtHeadRow:
        row = session.get(ArtHeadRow, project_id)
        if row is None:
            raise NotFoundError("project art review state is missing")
        return row

    def _context(self, session: Any, project_id: str) -> tuple[ArtBinding, dict[str, Any], dict[str, Any], dict[str, Any], dict[str, Any]]:
        """Extend the existing F2 source/map context with its accepted cast."""
        base, source, outline, mapping = self._cast._context(session, project_id)
        cast_head = self._cast._head(session, project_id)
        accepted = session.scalar(select(CastRevisionRow).where(CastRevisionRow.project_id == project_id, CastRevisionRow.revision == cast_head.revision)) if cast_head.revision else None
        if cast_head.status != "accepted" or accepted is None or self._cast._stale(session, project_id, base):
            raise InvalidTransitionError("a current accepted cast is required before preparing art")
        binding = ArtBinding(**base.model_dump(), cast_revision=accepted.revision, cast_content_hash=accepted.content_hash)
        return binding, source, outline, mapping, accepted.cast

    def _stale(self, session: Any, project_id: str, binding: ArtBinding) -> list[str]:
        try:
            current, *_ = self._context(session, project_id)
        except InvalidTransitionError as error:
            return [str(error)]
        fields = (
            ("source_revision", "source"), ("outline_revision", "accepted outline"),
            ("section_map_revision", "section map"), ("graph_revision", "installed graph"),
            ("cast_revision", "accepted cast"), ("source_content_hash", "source"),
            ("outline_content_hash", "accepted outline"), ("section_map_content_hash", "section map"),
            ("graph_content_hash", "installed graph"), ("cast_content_hash", "accepted cast"),
        )
        reasons = [f"{label} {'revision' if field.endswith('revision') else 'content'} changed" for field, label in fields if getattr(current, field) != getattr(binding, field)]
        return reasons + (["section context changed"] if current.section_ids != binding.section_ids else [])

    def get_state(self, project_id: str) -> ArtReviewState:
        with self._access.leases.read() as session:
            self._access.rows.project(session, project_id)
            head = self._head(session, project_id)
            candidate = session.get(ArtCandidateRow, head.candidate_job_id) if head.candidate_job_id else None
            accepted = session.scalar(select(ArtRevisionRow).where(ArtRevisionRow.project_id == project_id, ArtRevisionRow.revision == head.revision)) if head.revision else None
            binding = accepted.binding if accepted else candidate.binding if candidate else None
            stale = self._stale(session, project_id, ArtBinding.model_validate(binding)) if binding else []
            return ArtReviewState(candidate=self._candidate(candidate) if candidate else None, accepted_art=self._accepted(accepted) if accepted else None, status="stale" if stale and accepted else head.status, stale_reasons=stale)

    def prepare_candidate(self, project_id: str, job_id: str) -> tuple[ArtCandidate, CreativeHandoffRequest]:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head = self._head(session, project_id)
            if session.scalar(select(ArtCandidateRow.job_id).where(ArtCandidateRow.project_id == project_id, ArtCandidateRow.status == "prepared").limit(1)):
                raise InvalidTransitionError("cancel the prepared art specialist publication before changing review state")
            binding, source, outline, mapping, cast = self._context(session, project_id)
            request = CreativeHandoffRequest(job_id=job_id, project_id=project_id, section_id="shared-art", stage="art", expected_stage_revision=head.revision, source=source, input_artifacts={"outline.json": outline, "section-map.json": mapping, "cast.json": cast}, creative_brief="Create one upstream-shaped art.json candidate for the accepted source, outline, stable section context, and accepted cast. Use the section-map IDs as the thin explicit projection of upstream episode references; do not invent episodes, hooks, physical setting facts, or props from ambiguous state labels. Preserve reviewable stable scene and prop IDs. Cinematic realism is inherited author direction, while the upstream realistic preset is semi-realistic painterly: record that unresolved render-style qualification for F3B rather than silently changing the cast or style. This is a candidate only, not image generation, an asset selection, or project canon.")
            request.assert_secret_free()
            now = utc_now()
            row = ArtCandidateRow(job_id=job_id, project_id=project_id, expected_art_revision=head.revision, binding=binding.model_dump(mode="json", by_alias=True), request=request.model_dump(mode="json", by_alias=True), status="prepared", delivery_id=None, manifest_hash=None, art=None, report_html=None, created_at=now, delivered_at=None)
            session.add(row)
            head.candidate_job_id, head.status, head.updated_at = job_id, "prepared", now
            return self._candidate(row), request

    def admit_delivery(self, project_id: str, delivery: ValidatedCreativeDelivery) -> ArtCandidate:
        request = delivery.request
        if request.stage != "art" or request.project_id != project_id:
            raise CreativeHandoffError("delivery_identity_mismatch", "delivery does not belong to this art proposal")
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head, row = self._head(session, project_id), session.get(ArtCandidateRow, request.job_id)
            if row is None or row.project_id != project_id or head.candidate_job_id != request.job_id or row.request != request.model_dump(mode="json", by_alias=True):
                raise CreativeHandoffError("delivery_stale", "delivery is not the current prepared art proposal")
            if row.status == "cancelled":
                raise CreativeHandoffError("delivery_cancelled", "art candidate was cancelled")
            if row.status == "ready":
                if row.manifest_hash != delivery.manifest_hash:
                    raise CreativeHandoffError("delivery_conflict", "different delivery already occupies art candidate")
                return self._candidate(row)
            if row.status != "prepared" or row.expected_art_revision != head.revision or self._stale(session, project_id, ArtBinding.model_validate(row.binding)):
                raise CreativeHandoffError("delivery_stale", "art candidate context is stale")
            _validate_art(delivery.candidate)
            row.status, row.delivery_id, row.manifest_hash, row.art, row.report_html, row.delivered_at = "ready", delivery.manifest.delivery_id, delivery.manifest_hash, delivery.candidate, delivery.report.decode("utf-8"), utc_now()
            head.status, head.updated_at = "candidate_ready", row.delivered_at
            return self._candidate(row)

    def accept_candidate(self, project_id: str, request: ArtAcceptRequest) -> ArtReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head, row = self._head(session, project_id), session.get(ArtCandidateRow, request.job_id)
            if head.revision != request.expected_art_revision:
                raise RevisionConflictError("art", request.expected_art_revision, head.revision)
            if row is None or row.project_id != project_id or head.candidate_job_id != request.job_id or row.status != "ready" or row.art is None:
                raise InvalidTransitionError("art candidate is not ready for explicit acceptance")
            binding = ArtBinding.model_validate(row.binding)
            if binding != request.binding or self._stale(session, project_id, binding):
                raise CreativeHandoffError("delivery_stale", "art candidate context changed before acceptance")
            art = request.art or row.art
            _validate_art(art)
            if _art_ids(art) != _art_ids(row.art):
                raise ValueError("accepted art cannot change frozen scene or prop IDs")
            now = utc_now()
            head.revision += 1
            head.candidate_job_id, head.status, head.updated_at, row.status = None, "accepted", now, "accepted"
            self._save(session, project_id, head.revision, row.job_id, binding, art, now)
        return self.get_state(project_id)

    def reopen(self, project_id: str, request: ArtReopenRequest) -> ArtReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head = self._head(session, project_id)
            if head.revision != request.expected_art_revision:
                raise RevisionConflictError("art", request.expected_art_revision, head.revision)
            if not head.revision:
                raise InvalidTransitionError("no accepted art exists to reopen")
            if head.candidate_job_id:
                raise InvalidTransitionError("cancel the current art specialist publication before reopening accepted art")
            head.status, head.updated_at = "reopened", utc_now()
        return self.get_state(project_id)

    def save_reopened(self, project_id: str, request: ArtSaveRequest) -> ArtReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head = self._head(session, project_id)
            if head.revision != request.expected_art_revision:
                raise RevisionConflictError("art", request.expected_art_revision, head.revision)
            if head.status != "reopened":
                raise InvalidTransitionError("reopen accepted art before saving author edits")
            previous = session.scalar(select(ArtRevisionRow).where(ArtRevisionRow.project_id == project_id, ArtRevisionRow.revision == head.revision))
            if previous is None:
                raise NotFoundError("accepted art revision is missing")
            binding = ArtBinding.model_validate(previous.binding)
            if binding != request.binding or self._stale(session, project_id, binding):
                raise CreativeHandoffError("delivery_stale", "accepted art context changed before saving edits")
            _validate_art(request.art)
            if _art_ids(request.art) != _art_ids(previous.art):
                raise ValueError("reopened art cannot change stable scene or prop IDs")
            now = utc_now()
            head.revision, head.status, head.updated_at = head.revision + 1, "accepted", now
            self._save(session, project_id, head.revision, previous.candidate_job_id, binding, request.art, now)
        return self.get_state(project_id)

    def cancel_candidate(self, project_id: str, job_id: str) -> ArtReviewState:
        with self._access.leases.lifecycle_write() as session:
            self._access.guards.active(self._access.rows.project(session, project_id))
            head, row = self._head(session, project_id), session.get(ArtCandidateRow, job_id)
            if row is None or row.project_id != project_id:
                raise NotFoundError("project art candidate is unavailable")
            if row.status == "accepted":
                raise InvalidTransitionError("accepted art candidate cannot be cancelled")
            row.status = "cancelled"
            if head.candidate_job_id == job_id:
                head.candidate_job_id, head.status, head.updated_at = None, "accepted" if head.revision else "missing", utc_now()
        return self.get_state(project_id)

    def candidate_report(self, project_id: str, job_id: str) -> str:
        with self._access.leases.read() as session:
            row = session.get(ArtCandidateRow, job_id)
            if row is None or row.project_id != project_id or row.status not in {"ready", "accepted"} or row.report_html is None:
                raise NotFoundError("ready art report is unavailable")
            return row.report_html

    def candidate_request(self, project_id: str, job_id: str) -> CreativeHandoffRequest:
        with self._access.leases.read() as session:
            row = session.get(ArtCandidateRow, job_id)
            if row is None or row.project_id != project_id or row.status == "cancelled":
                raise NotFoundError("project art candidate is unavailable")
            return CreativeHandoffRequest.model_validate(row.request)

    @staticmethod
    def _save(session: Any, project_id: str, revision: int, candidate_job_id: str, binding: ArtBinding, art: dict[str, Any], accepted_at: Any) -> None:
        session.add(ArtRevisionRow(id=new_id(), project_id=project_id, revision=revision, candidate_job_id=candidate_job_id, content_hash=sha256(canonical_json(art)).hexdigest(), binding=binding.model_dump(mode="json", by_alias=True), art=art, accepted_at=accepted_at))


def _art_ids(art: dict[str, Any]) -> tuple[tuple[str, ...], tuple[str, ...]]:
    scenes, props = art.get("scenes"), art.get("props", [])
    if not isinstance(scenes, list) or not scenes or not isinstance(props, list):
        raise ValueError("upstream art must contain scenes and an optional props list")
    scene_ids = [item.get("id") for item in scenes if isinstance(item, dict)]
    prop_ids = [item.get("id") for item in props if isinstance(item, dict)]
    if len(scene_ids) != len(scenes) or len(prop_ids) != len(props) or any(not isinstance(item, str) or not item.strip() for item in scene_ids + prop_ids) or len(set(scene_ids)) != len(scene_ids) or len(set(prop_ids)) != len(prop_ids):
        raise ValueError("every art scene and prop needs a unique stable ID")
    return tuple(scene_ids), tuple(prop_ids)


def _validate_art(art: dict[str, Any]) -> None:
    if contains_secret_setting(art) or contains_secret_value(art):
        raise ValueError("art must not contain credentials")
    if not isinstance(art.get("source"), str) or not isinstance(art.get("style"), str):
        raise ValueError("upstream art must retain source and style")
    _art_ids(art)
