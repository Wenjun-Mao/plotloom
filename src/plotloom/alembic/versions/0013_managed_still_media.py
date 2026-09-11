"""Add non-generative imported-media and immutable still-preview records."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0013_managed_still_media"
down_revision = "0012_text_profile_adapter_selection"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_managed_assets",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("original_uri", sa.Text(), nullable=False),
        sa.Column("original_hash", sa.String(64), nullable=False),
        sa.Column("display_uri", sa.Text(), nullable=False),
        sa.Column("display_hash", sa.String(64), nullable=False),
        sa.Column("mime_type", sa.String(32), nullable=False),
        sa.Column("byte_size", sa.Integer(), nullable=False),
        sa.Column("width", sa.Integer(), nullable=False),
        sa.Column("height", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_managed_assets_project_id_created_at", "v2_managed_assets", ["project_id", "created_at"])
    op.create_table(
        "v2_managed_asset_provenance",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("declaration", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_managed_asset_provenance_asset_id", "v2_managed_asset_provenance", ["asset_id"])
    op.create_table(
        "v2_visual_intents",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("intent", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_visual_intents_project_id_asset_id", "v2_visual_intents", ["project_id", "asset_id"])
    op.create_table(
        "v2_visual_selection_states",
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "v2_reviewed_shot_bindings",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("storyboard_entity_revision_id", sa.String(36), sa.ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approval_id", sa.String(36), sa.ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("shot_id", sa.String(100), nullable=False),
        sa.Column("scene_id", sa.String(100), nullable=False),
        sa.Column("storyboard_revision", sa.Integer(), nullable=False),
        sa.Column("selection_revision", sa.Integer(), nullable=False),
        sa.Column("compatibility_note", sa.Text(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_reviewed_shot_bindings_project_shot_revision", "v2_reviewed_shot_bindings", ["project_id", "shot_id", "selection_revision"])
    op.create_table(
        "v2_still_previews",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("storyboard_entity_revision_id", sa.String(36), sa.ForeignKey("v2_entity_revisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("approval_id", sa.String(36), sa.ForeignKey("v2_approval_decisions.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("scene_id", sa.String(100), nullable=False),
        sa.Column("selection_revision", sa.Integer(), nullable=False),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("manifest_hash", sa.String(64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_still_previews_project_id_created_at", "v2_still_previews", ["project_id", "created_at"])


def downgrade() -> None:
    for table, index in (
        ("v2_still_previews", "ix_v2_still_previews_project_id_created_at"),
        ("v2_reviewed_shot_bindings", "ix_v2_reviewed_shot_bindings_project_shot_revision"),
        ("v2_visual_intents", "ix_v2_visual_intents_project_id_asset_id"),
        ("v2_managed_asset_provenance", "ix_v2_managed_asset_provenance_asset_id"),
        ("v2_managed_assets", "ix_v2_managed_assets_project_id_created_at"),
    ):
        op.drop_index(index, table_name=table)
    op.drop_table("v2_still_previews")
    op.drop_table("v2_reviewed_shot_bindings")
    op.drop_table("v2_visual_selection_states")
    op.drop_table("v2_visual_intents")
    op.drop_table("v2_managed_asset_provenance")
    op.drop_table("v2_managed_assets")
