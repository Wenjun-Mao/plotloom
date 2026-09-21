"""Record whether a rejected character delivery crossed final publication."""
from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0021_character_delivery_publication_phase"
down_revision = "0020_f3b_art_reference_studies"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing rows intentionally remain NULL: the historical schema did not
    # record whether completion.json was present, so migration cannot safely
    # rewrite them as either transient or final failures.
    with op.batch_alter_table("v2_character_reference_proposal_deliveries") as batch:
        batch.add_column(sa.Column("publication_phase", sa.String(24), nullable=True))


def downgrade() -> None:
    with op.batch_alter_table("v2_character_reference_proposal_deliveries") as batch:
        batch.drop_column("publication_phase")
