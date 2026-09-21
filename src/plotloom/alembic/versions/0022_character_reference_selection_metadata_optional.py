"""Allow creator appearance selections without attribution fields."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0022_character_reference_selection_metadata_optional"
down_revision = "0021_character_delivery_publication_phase"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("v2_character_reference_decisions") as batch:
        batch.alter_column("reviewer", existing_type=sa.String(160), nullable=True)
        batch.alter_column("notes", existing_type=sa.Text(), nullable=True)


def downgrade() -> None:
    with op.batch_alter_table("v2_character_reference_decisions") as batch:
        batch.alter_column("reviewer", existing_type=sa.String(160), nullable=False)
        batch.alter_column("notes", existing_type=sa.Text(), nullable=False)
