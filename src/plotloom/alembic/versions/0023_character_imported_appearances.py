"""Bind imported appearance assets to an accepted cast subject."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa

revision = "0023_character_imported_appearances"
down_revision = "0022_character_reference_selection_metadata_optional"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_character_imported_appearances",
        sa.Column("id", sa.String(36), primary_key=True),
        sa.Column("project_id", sa.String(36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("character_id", sa.String(128), nullable=False),
        sa.Column("asset_id", sa.String(36), sa.ForeignKey("v2_managed_assets.id", ondelete="RESTRICT"), nullable=False),
        sa.Column("character_context", sa.JSON(), nullable=False),
        sa.Column("character_context_hash", sa.String(64), nullable=False),
        sa.Column("label", sa.String(160), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "character_id", "asset_id", name="uq_v2_character_imported_appearance"),
    )
    op.create_index("ix_v2_character_imported_appearances_project_character", "v2_character_imported_appearances", ["project_id", "character_id", "created_at"])


def downgrade() -> None:
    op.drop_index("ix_v2_character_imported_appearances_project_character", table_name="v2_character_imported_appearances")
    op.drop_table("v2_character_imported_appearances")
