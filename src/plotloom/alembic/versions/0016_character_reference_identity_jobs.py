"""Persist P1.5 character-reference decisions, proposals, and visual reviews."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0016_character_reference_identity_jobs"
down_revision = "0015_agent_operated_image_jobs"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_character_reference_states",
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("character_id", sa.String(128), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("active_decision_id", sa.String(36), nullable=True),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "v2_character_reference_decisions",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("character_id", sa.String(128), nullable=False),
        sa.Column("reference_revision", sa.Integer(), nullable=False),
        sa.Column("character_context", sa.JSON(), nullable=False),
        sa.Column("character_context_hash", sa.String(64), nullable=False),
        sa.Column("primary_asset_id", sa.String(36), sa.ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("complementary_asset_ids", sa.JSON(), nullable=False),
        sa.Column("asset_hashes", sa.JSON(), nullable=False),
        sa.Column("reviewer", sa.String(160), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("revoked_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("revoked_by", sa.String(160), nullable=True),
        sa.Column("revocation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "character_id", "reference_revision", name="uq_v2_character_reference_revision"),
    )
    op.create_index("ix_v2_character_reference_decisions_project_character", "v2_character_reference_decisions", ["project_id", "character_id", "reference_revision"])
    op.create_table(
        "v2_character_reference_proposals",
        sa.Column("id", sa.String(67), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("character_id", sa.String(128), nullable=False),
        sa.Column("parent_candidate_asset_id", sa.String(36), sa.ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=True),
        sa.Column("request", sa.JSON(), nullable=False),
        sa.Column("request_hash", sa.String(64), nullable=False, unique=True),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("exported_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancelled_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancellation_reason", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_character_reference_proposals_project_created", "v2_character_reference_proposals", ["project_id", "created_at"])
    op.create_table(
        "v2_character_reference_proposal_deliveries",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(67), sa.ForeignKey("v2_character_reference_proposals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("delivery_id", sa.String(128), nullable=True),
        sa.Column("manifest", sa.JSON(), nullable=True),
        sa.Column("manifest_hash", sa.String(64), nullable=True),
        sa.Column("state", sa.String(24), nullable=False),
        sa.Column("diagnostic_code", sa.String(80), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("proposal_id", "delivery_id", name="uq_v2_character_proposal_delivery_identity"),
    )
    op.create_index("uq_v2_character_proposal_final_delivery", "v2_character_reference_proposal_deliveries", ["proposal_id"], unique=True, sqlite_where=sa.text("delivery_id IS NOT NULL"))
    op.create_table(
        "v2_character_reference_proposal_candidates",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("proposal_id", sa.String(67), sa.ForeignKey("v2_character_reference_proposals.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("delivery_id", sa.String(36), sa.ForeignKey("v2_character_reference_proposal_deliveries.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("output_filename", sa.String(180), nullable=False),
        sa.Column("output_hash", sa.String(64), nullable=False),
        sa.Column("role", sa.String(24), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("delivery_id", "asset_id", name="uq_v2_character_proposal_candidate_asset"),
    )
    op.create_table(
        "v2_same_person_review_states",
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "v2_same_person_reviews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("binding_id", sa.String(36), sa.ForeignKey("v2_reviewed_shot_bindings.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("review_revision", sa.Integer(), nullable=False),
        sa.Column("reference_bindings", sa.JSON(), nullable=False),
        sa.Column("comparisons", sa.JSON(), nullable=False),
        sa.Column("reviewer", sa.String(160), nullable=False),
        sa.Column("notes", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_same_person_reviews_project_binding_revision", "v2_same_person_reviews", ["project_id", "binding_id", "review_revision"])


def downgrade() -> None:
    op.drop_index("ix_v2_same_person_reviews_project_binding_revision", table_name="v2_same_person_reviews")
    op.drop_table("v2_same_person_reviews")
    op.drop_table("v2_same_person_review_states")
    op.drop_table("v2_character_reference_proposal_candidates")
    op.drop_index("uq_v2_character_proposal_final_delivery", table_name="v2_character_reference_proposal_deliveries")
    op.drop_table("v2_character_reference_proposal_deliveries")
    op.drop_index("ix_v2_character_reference_proposals_project_created", table_name="v2_character_reference_proposals")
    op.drop_table("v2_character_reference_proposals")
    op.drop_index("ix_v2_character_reference_decisions_project_character", table_name="v2_character_reference_decisions")
    op.drop_table("v2_character_reference_decisions")
    op.drop_table("v2_character_reference_states")
