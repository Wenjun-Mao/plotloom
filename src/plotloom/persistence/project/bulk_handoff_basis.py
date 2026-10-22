"""Shared historical receipt authority, never recursive current eligibility."""
from dataclasses import dataclass

from sqlalchemy import select

from ...autopilot_contracts import OperationScope
from ...exceptions import InvalidTransitionError
from ..schema import AutopilotHandoffRow


@dataclass(frozen=True)
class BulkHandoffWrite:
    receipt_id: str
    bundle_hash: str
    shot_id: str

    def require(self, access):
        authority = access.authority()
        if authority is None or authority.scope != OperationScope.HANDOFF:
            raise InvalidTransitionError("bulk human judgments require exact handoff authority")


def receipt_basis(session, project_id, binding_id, review_id=None):
    """Validate only historical receipt/native links; never call admission."""
    from ...project_storage.handoff_validation import assert_handoff
    for row in session.scalars(select(AutopilotHandoffRow).where(AutopilotHandoffRow.project_id == project_id)):
        if row.receipt.get("version") not in {"pre-video.handoff.v2", "pre-video.handoff.v3", "pre-video.handoff.v4"}:
            continue
        facts = row.receipt.get("bindings", [])
        if not any(item.get("bindingId") == binding_id and (review_id is None or item.get("samePersonReviewId") == review_id) for item in facts):
            continue
        try:
            receipt = assert_handoff(session.connection().connection.driver_connection, row.id, row.run_id,
                project_id, row.approval_id, row.receipt, row.receipt_hash)
        except (ValueError, TypeError, KeyError):
            return None
        return {"version": getattr(receipt.observation, "basis", "detailed-observations.v2"), "receiptId": row.id, "bundleHash": receipt.bundle_hash}
    return None


def binding_has_basis(session, binding):
    return (binding.id in session.info.get("pending_bulk_bindings", {}) or
        receipt_basis(session, binding.project_id, binding.id) is not None)


def review_has_basis(session, review):
    pending = session.info.get("pending_bulk_bindings", {}).get(review.binding_id)
    if pending is not None:
        return all(item.get("confirmation") == {"version": "whole-pack-material.v1", "receiptId": pending.receipt_id,
            "bundleHash": pending.bundle_hash, "shotId": pending.shot_id} for item in review.comparisons)
    return receipt_basis(session, review.project_id, review.binding_id, review.id) is not None
