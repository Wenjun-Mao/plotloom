"""Durable bounded-generation plans, units, and sealed aggregates.

Revision ID: 0005_v2_generation_work_units
Revises: 0004_v2_project_creation_idempotency
"""

from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0005_v2_generation_work_units"
down_revision = "0004_v2_project_creation_idempotency"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing history has no exact-unit manifest.  Keep it readable, but it
    # must never be resumed or used as a repair source under the new contract.
    op.add_column(
        "v2_generation_runs",
        sa.Column("legacy_unsealed", sa.Boolean(), nullable=False, server_default=sa.true()),
    )
    # A running legacy attempt has no dispatch marker.  Do not fabricate one
    # during migration: terminate the process-local execution with an explicit
    # error before its parent run becomes non-terminal history.
    op.execute(
        """
        UPDATE v2_generation_attempts
        SET status = 'cancelled',
            error = 'Legacy generation attempt cancelled during work-unit migration',
            finished_at = CURRENT_TIMESTAMP
        WHERE status = 'running'
          AND run_id IN (
              SELECT id
              FROM v2_generation_runs
              WHERE status = 'cancel_requested'
          )
        """
    )
    op.execute(
        """
        UPDATE v2_generation_runs
        SET status = 'cancelled',
            error = 'Legacy generation run cancellation finalized during work-unit migration',
            finished_at = CURRENT_TIMESTAMP
        WHERE status = 'cancel_requested'
        """
    )
    op.execute(
        """
        UPDATE v2_generation_attempts
        SET status = 'failed',
            error = 'Legacy generation attempt stopped during work-unit migration; dispatch state is unknown',
            finished_at = CURRENT_TIMESTAMP
        WHERE status = 'running'
          AND run_id IN (
              SELECT id
              FROM v2_generation_runs
              WHERE status IN ('queued', 'running')
          )
        """
    )
    op.execute(
        """
        UPDATE v2_generation_runs
        SET status = 'failed',
            error = 'Legacy/unsealed generation run cannot resume after work-unit migration',
            finished_at = CURRENT_TIMESTAMP
        WHERE status IN ('queued', 'running')
        """
    )

    op.create_table(
        "v2_generation_plans",
        sa.Column(
            "run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("plan_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "v2_generation_stage_plans",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("generation_plan_hash", sa.String(length=64), nullable=False),
        sa.Column("dependency_hash", sa.String(length=64), nullable=False),
        sa.Column("stage_plan_hash", sa.String(length=64), nullable=False),
        sa.Column("plan", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("run_id", "stage"),
        sa.UniqueConstraint("run_id", "stage_plan_hash"),
    )
    op.create_index("ix_v2_generation_stage_plans_run_id", "v2_generation_stage_plans", ["run_id"])
    op.create_table(
        "v2_generation_work_units",
        sa.Column("id", sa.String(length=120), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "stage_plan_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_stage_plans.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("selector", sa.JSON(), nullable=False),
        sa.Column("generation_plan_hash", sa.String(length=64), nullable=False),
        sa.Column("dependency_hash", sa.String(length=64), nullable=False),
        sa.Column("unit_dependency_hash", sa.String(length=64), nullable=False),
        sa.Column("input_hash", sa.String(length=64), nullable=False),
        sa.Column("budget", sa.JSON(), nullable=False),
        sa.Column("estimated_input_tokens", sa.Integer(), nullable=False),
        sa.Column("context_window_tokens", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("stage_plan_id", "sequence"),
    )
    op.create_index("ix_v2_generation_work_units_run_id", "v2_generation_work_units", ["run_id"])
    op.create_index(
        "ix_v2_generation_work_units_stage_plan_id",
        "v2_generation_work_units",
        ["stage_plan_id"],
    )
    op.create_table(
        "v2_sealed_stage_aggregates",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column(
            "run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "stage_plan_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_stage_plans.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("manifest_hash", sa.String(length=64), nullable=False, unique=True),
        sa.Column("manifest", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("stage_plan_id"),
    )
    op.create_index("ix_v2_sealed_stage_aggregates_run_id", "v2_sealed_stage_aggregates", ["run_id"])

    # SQLite needs a batch rebuild to attach true foreign keys to pre-existing
    # attempt/artifact tables.  They turn accidental cross-run evidence links
    # into database-level failures as well as repository-level checks.
    with op.batch_alter_table(
        "v2_generation_attempts",
        naming_convention={"uq": "uq_%(table_name)s_%(column_0_N_name)s"},
    ) as batch:
        # The old run/stage sequence makes independent units in one stage
        # contend for a shared number.  Replace it with a unit-local sequence;
        # a partial unique index below preserves legacy create_attempt behavior.
        batch.drop_constraint(
            "uq_v2_generation_attempts_run_id_stage_attempt_number",
            type_="unique",
        )
        batch.add_column(sa.Column("work_unit_id", sa.String(length=120), nullable=True))
        batch.add_column(sa.Column("dispatched_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("response_persisted_at", sa.DateTime(timezone=True), nullable=True))
        batch.add_column(sa.Column("provider_request_id", sa.String(length=200), nullable=True))
        batch.add_column(
            sa.Column("outcome_unknown", sa.Boolean(), nullable=False, server_default=sa.false())
        )
        batch.create_foreign_key(
            "fk_v2_generation_attempts_work_unit_id",
            "v2_generation_work_units",
            ["work_unit_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index("ix_v2_generation_attempts_work_unit_id", ["work_unit_id"])
        batch.create_unique_constraint(
            "uq_v2_generation_attempts_work_unit_id_attempt_number",
            ["work_unit_id", "attempt_number"],
        )
    op.create_index(
        "uq_v2_generation_attempts_legacy_run_stage_attempt_number",
        "v2_generation_attempts",
        ["run_id", "stage", "attempt_number"],
        unique=True,
        sqlite_where=sa.text("work_unit_id IS NULL"),
    )
    with op.batch_alter_table("v2_artifacts") as batch:
        batch.add_column(sa.Column("work_unit_id", sa.String(length=120), nullable=True))
        batch.create_foreign_key(
            "fk_v2_artifacts_attempt_id",
            "v2_generation_attempts",
            ["attempt_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_foreign_key(
            "fk_v2_artifacts_work_unit_id",
            "v2_generation_work_units",
            ["work_unit_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index("ix_v2_artifacts_work_unit_id", ["work_unit_id"])
    # Do not apply this uniqueness rule to legacy evidence bags: historical
    # duplicate kinds remain readable but are never sealable.  Every new
    # work-unit producer attempt is protected at the database boundary.
    op.create_index(
        "uq_v2_artifacts_work_unit_attempt_kind",
        "v2_artifacts",
        ["attempt_id", "kind"],
        unique=True,
        sqlite_where=sa.text("work_unit_id IS NOT NULL"),
    )


def downgrade() -> None:
    op.drop_index(
        "uq_v2_artifacts_work_unit_attempt_kind",
        table_name="v2_artifacts",
    )
    with op.batch_alter_table("v2_artifacts") as batch:
        batch.drop_index("ix_v2_artifacts_work_unit_id")
        batch.drop_constraint("fk_v2_artifacts_work_unit_id", type_="foreignkey")
        batch.drop_constraint("fk_v2_artifacts_attempt_id", type_="foreignkey")
        batch.drop_column("work_unit_id")
    op.drop_index(
        "uq_v2_generation_attempts_legacy_run_stage_attempt_number",
        table_name="v2_generation_attempts",
    )
    with op.batch_alter_table("v2_generation_attempts") as batch:
        batch.drop_constraint(
            "uq_v2_generation_attempts_work_unit_id_attempt_number",
            type_="unique",
        )
        batch.create_unique_constraint(
            "uq_v2_generation_attempts_run_id_stage_attempt_number",
            ["run_id", "stage", "attempt_number"],
        )
        batch.drop_index("ix_v2_generation_attempts_work_unit_id")
        batch.drop_constraint("fk_v2_generation_attempts_work_unit_id", type_="foreignkey")
        batch.drop_column("outcome_unknown")
        batch.drop_column("provider_request_id")
        batch.drop_column("response_persisted_at")
        batch.drop_column("dispatched_at")
        batch.drop_column("work_unit_id")
    op.drop_index("ix_v2_sealed_stage_aggregates_run_id", table_name="v2_sealed_stage_aggregates")
    op.drop_table("v2_sealed_stage_aggregates")
    op.drop_index("ix_v2_generation_work_units_stage_plan_id", table_name="v2_generation_work_units")
    op.drop_index("ix_v2_generation_work_units_run_id", table_name="v2_generation_work_units")
    op.drop_table("v2_generation_work_units")
    op.drop_index("ix_v2_generation_stage_plans_run_id", table_name="v2_generation_stage_plans")
    op.drop_table("v2_generation_stage_plans")
    op.drop_table("v2_generation_plans")
    op.drop_column("v2_generation_runs", "legacy_unsealed")
