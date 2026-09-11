"""Persist trusted adapter selection outside historical settings JSON."""
from __future__ import annotations
from alembic import op
import sqlalchemy as sa

revision = "0012_text_profile_adapter_selection"
down_revision = "0011_text_profile_availability"
branch_labels = None
depends_on = None

def upgrade() -> None:
    op.add_column("v2_text_provider_profiles", sa.Column("adapter_id", sa.String(120), nullable=False, server_default="openai_compatible"))
    op.add_column("v2_text_provider_profiles", sa.Column("adapter_version", sa.String(40), nullable=False, server_default="1"))

def downgrade() -> None:
    with op.batch_alter_table("v2_text_provider_profiles") as batch:
        batch.drop_column("adapter_version")
        batch.drop_column("adapter_id")
