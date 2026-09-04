"""Persist project lifecycle state and duplicate idempotency bindings.

Revision ID: 0008_v2_project_lifecycle
Revises: 0007_v2_run_failure_codes
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0008_v2_project_lifecycle"
down_revision = "0007_v2_run_failure_codes"
branch_labels = None
depends_on = None


def upgrade() -> None:
    with op.batch_alter_table("v2_projects") as batch:
        batch.add_column(
            sa.Column("lifecycle_revision", sa.Integer(), nullable=False, server_default="1")
        )
        batch.add_column(
            sa.Column(
                "lifecycle_status",
                sa.String(length=16),
                nullable=False,
                server_default="active",
            )
        )
        batch.add_column(sa.Column("archived_at", sa.DateTime(timezone=True), nullable=True))
    # Keep the application-owned defaults in the ORM.  Removing server
    # defaults avoids silently masking an incomplete insert in another client.
    with op.batch_alter_table("v2_projects") as batch:
        batch.alter_column("lifecycle_revision", server_default=None)
        batch.alter_column("lifecycle_status", server_default=None)
    op.create_index(
        "ix_v2_projects_lifecycle_status_created_at_id",
        "v2_projects",
        ["lifecycle_status", "created_at", "id"],
    )
    op.create_table(
        "v2_project_duplicate_idempotency",
        sa.Column("idempotency_key", sa.String(length=255), primary_key=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "project_id",
            sa.String(length=36),
            sa.ForeignKey("v2_projects.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("copied_through", sa.String(length=32), nullable=True),
        sa.Column("omitted_stages", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("v2_project_duplicate_idempotency")
    op.drop_index("ix_v2_projects_lifecycle_status_created_at_id", table_name="v2_projects")
    with op.batch_alter_table("v2_projects") as batch:
        batch.drop_column("archived_at")
        batch.drop_column("lifecycle_status")
        batch.drop_column("lifecycle_revision")
