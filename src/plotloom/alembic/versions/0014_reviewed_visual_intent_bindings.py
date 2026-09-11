"""Bind reviewed keyframes to immutable visual-intent revisions."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0014_reviewed_visual_intent_bindings"
down_revision = "0013_managed_still_media"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Nullable preserves readable pre-correction history. New reviewed bindings
    # require both values in repository code and all new previews freeze them.
    with op.batch_alter_table("v2_reviewed_shot_bindings") as batch:
        batch.add_column(sa.Column("visual_intent_id", sa.String(36), nullable=True))
        batch.add_column(sa.Column("visual_intent_revision", sa.Integer(), nullable=True))
        batch.create_foreign_key(
            "fk_v2_reviewed_shot_bindings_visual_intent_id",
            "v2_visual_intents", ["visual_intent_id"], ["id"], ondelete="RESTRICT",
        )
        batch.create_index(
            "ix_v2_reviewed_shot_bindings_visual_intent_id",
            ["visual_intent_id"],
        )


def downgrade() -> None:
    with op.batch_alter_table("v2_reviewed_shot_bindings") as batch:
        batch.drop_index("ix_v2_reviewed_shot_bindings_visual_intent_id")
        batch.drop_constraint("fk_v2_reviewed_shot_bindings_visual_intent_id", type_="foreignkey")
        batch.drop_column("visual_intent_revision")
        batch.drop_column("visual_intent_id")
