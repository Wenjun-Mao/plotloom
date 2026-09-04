"""Persist immutable exact work-unit repair scopes and reuse bindings.

Revision ID: 0009_v2_work_unit_repair_scopes
Revises: 0008_v2_project_lifecycle
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0009_v2_work_unit_repair_scopes"
down_revision = "0008_v2_project_lifecycle"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # ``repair_source`` remains the legacy, stage-level repair record.  An
    # additive foreign-key-shaped identity lets readers dispatch exact child
    # runs without guessing from JSON or fabricating legacy evidence.
    with op.batch_alter_table("v2_generation_runs") as batch:
        batch.add_column(sa.Column("work_unit_repair_scope_id", sa.String(length=36), nullable=True))
        batch.create_index(
            "ix_v2_generation_runs_work_unit_repair_scope_id",
            ["work_unit_repair_scope_id"],
        )

    op.create_table(
        "v2_generation_work_unit_repair_scopes",
        sa.Column(
            "child_run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "parent_run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "target_work_unit_id",
            sa.String(length=120),
            sa.ForeignKey("v2_generation_work_units.id", ondelete="RESTRICT"),
            nullable=False,
            unique=True,
        ),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("scope_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("scope", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_v2_generation_work_unit_repair_scopes_parent_run_id",
        "v2_generation_work_unit_repair_scopes",
        ["parent_run_id"],
    )

    op.create_table(
        "v2_generation_fragment_reuse_bindings",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "child_run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "child_stage_plan_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_stage_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "child_work_unit_id",
            sa.String(length=120),
            sa.ForeignKey("v2_generation_work_units.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column(
            "source_run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_work_unit_id",
            sa.String(length=120),
            sa.ForeignKey("v2_generation_work_units.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_stage_plan_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_stage_plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "source_candidate_artifact_id",
            sa.String(length=36),
            sa.ForeignKey("v2_artifacts.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("binding_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("binding", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_v2_generation_fragment_reuse_bindings_child_run_id",
        "v2_generation_fragment_reuse_bindings",
        ["child_run_id"],
    )
    op.create_index(
        "ix_v2_generation_fragment_reuse_bindings_child_stage_plan_id",
        "v2_generation_fragment_reuse_bindings",
        ["child_stage_plan_id"],
    )

    op.create_table(
        "v2_generation_work_unit_repair_idempotency",
        sa.Column("idempotency_key", sa.String(length=255), primary_key=True),
        sa.Column("request_fingerprint", sa.String(length=64), nullable=False),
        sa.Column(
            "parent_run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "target_work_unit_id",
            sa.String(length=120),
            sa.ForeignKey("v2_generation_work_units.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column(
            "child_run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )


def downgrade() -> None:
    op.drop_table("v2_generation_work_unit_repair_idempotency")
    op.drop_index(
        "ix_v2_generation_fragment_reuse_bindings_child_stage_plan_id",
        table_name="v2_generation_fragment_reuse_bindings",
    )
    op.drop_index(
        "ix_v2_generation_fragment_reuse_bindings_child_run_id",
        table_name="v2_generation_fragment_reuse_bindings",
    )
    op.drop_table("v2_generation_fragment_reuse_bindings")
    op.drop_index(
        "ix_v2_generation_work_unit_repair_scopes_parent_run_id",
        table_name="v2_generation_work_unit_repair_scopes",
    )
    op.drop_table("v2_generation_work_unit_repair_scopes")
    with op.batch_alter_table("v2_generation_runs") as batch:
        batch.drop_index("ix_v2_generation_runs_work_unit_repair_scope_id")
        batch.drop_column("work_unit_repair_scope_id")
