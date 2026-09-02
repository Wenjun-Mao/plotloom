from __future__ import annotations

from alembic import op
import sqlalchemy as sa


revision = "0001_v2_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "v2_projects",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("brief", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_table(
        "v2_entity_revisions",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("parent_revision_id", sa.String(length=36), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("input_revisions", sa.JSON(), nullable=False),
        sa.Column("payload", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "stage", "revision"),
    )
    op.create_index("ix_v2_entity_revisions_project_id", "v2_entity_revisions", ["project_id"])
    op.create_table(
        "v2_stage_heads",
        sa.Column("id", sa.String(length=80), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("entity_revision_id", sa.String(length=36), nullable=True),
        sa.Column("content_hash", sa.String(length=64), nullable=True),
        sa.Column("input_revisions", sa.JSON(), nullable=False),
        sa.Column("stale_reasons", sa.JSON(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.UniqueConstraint("project_id", "stage"),
    )
    op.create_index("ix_v2_stage_heads_project_id", "v2_stage_heads", ["project_id"])
    op.create_table(
        "v2_generation_runs",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column(
            "parent_run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="RESTRICT"),
            nullable=True,
        ),
        sa.Column("repair_stage", sa.String(length=32), nullable=True),
        sa.Column("provider_snapshot", sa.JSON(), nullable=False),
        sa.Column("requested_stages", sa.JSON(), nullable=False),
        sa.Column("status", sa.String(length=32), nullable=False),
        sa.Column("canonical_snapshot", sa.JSON(), nullable=False),
        sa.Column("instructions", sa.Text(), nullable=True),
        sa.Column("result_revision_ids", sa.JSON(), nullable=False),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_v2_generation_runs_project_id", "v2_generation_runs", ["project_id"])
    op.create_index("ix_v2_generation_runs_parent_run_id", "v2_generation_runs", ["parent_run_id"])
    op.create_index("ix_v2_generation_runs_status", "v2_generation_runs", ["status"])
    op.create_table(
        "v2_generation_attempts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("stage", sa.String(length=32), nullable=False),
        sa.Column("attempt_number", sa.Integer(), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("model", sa.String(length=200), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.UniqueConstraint("run_id", "stage", "attempt_number"),
    )
    op.create_index("ix_v2_generation_attempts_run_id", "v2_generation_attempts", ["run_id"])
    op.create_table(
        "v2_artifacts",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("run_id", sa.String(length=36), sa.ForeignKey("v2_generation_runs.id", ondelete="CASCADE"), nullable=False),
        sa.Column("attempt_id", sa.String(length=36), nullable=True),
        sa.Column("stage", sa.String(length=32), nullable=True),
        sa.Column("kind", sa.String(length=32), nullable=False),
        sa.Column("media_type", sa.String(length=100), nullable=False),
        sa.Column("content", sa.JSON(), nullable=False),
        sa.Column("content_hash", sa.String(length=64), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_artifacts_run_id", "v2_artifacts", ["run_id"])
    op.create_table(
        "v2_media_tasks",
        sa.Column("id", sa.String(length=36), primary_key=True),
        sa.Column("project_id", sa.String(length=36), sa.ForeignKey("v2_projects.id", ondelete="CASCADE"), nullable=False),
        sa.Column("shot_id", sa.String(length=100), nullable=False),
        sa.Column("storyboard_revision", sa.Integer(), nullable=False),
        sa.Column("kind", sa.String(length=16), nullable=False),
        sa.Column("status", sa.String(length=16), nullable=False),
        sa.Column("derived_prompt", sa.Text(), nullable=False),
        sa.Column("prompt_components", sa.JSON(), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=True),
        sa.Column("public_settings", sa.JSON(), nullable=False),
        sa.Column("output_uri", sa.Text(), nullable=True),
        sa.Column("error", sa.Text(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index("ix_v2_media_tasks_project_id", "v2_media_tasks", ["project_id"])
    op.create_table(
        "v2_provider_settings",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )


def downgrade() -> None:
    op.drop_table("v2_provider_settings")
    op.drop_index("ix_v2_media_tasks_project_id", table_name="v2_media_tasks")
    op.drop_table("v2_media_tasks")
    op.drop_index("ix_v2_artifacts_run_id", table_name="v2_artifacts")
    op.drop_table("v2_artifacts")
    op.drop_index("ix_v2_generation_attempts_run_id", table_name="v2_generation_attempts")
    op.drop_table("v2_generation_attempts")
    op.drop_index("ix_v2_generation_runs_status", table_name="v2_generation_runs")
    op.drop_index("ix_v2_generation_runs_parent_run_id", table_name="v2_generation_runs")
    op.drop_index("ix_v2_generation_runs_project_id", table_name="v2_generation_runs")
    op.drop_table("v2_generation_runs")
    op.drop_index("ix_v2_stage_heads_project_id", table_name="v2_stage_heads")
    op.drop_table("v2_stage_heads")
    op.drop_index("ix_v2_entity_revisions_project_id", table_name="v2_entity_revisions")
    op.drop_table("v2_entity_revisions")
    op.drop_table("v2_projects")
