"""Named text profiles, deterministic graph topologies, and correction lineage.

Revision ID: 0006_v2_model_profiles
Revises: 0005_v2_generation_work_units
"""

from __future__ import annotations

from datetime import datetime, timezone
import json
import re
from typing import Any

from alembic import op
import sqlalchemy as sa


revision = "0006_v2_model_profiles"
down_revision = "0005_v2_generation_work_units"
branch_labels = None
depends_on = None


_SECRET_NAMES = frozenset(
    {
        "apikey",
        "key",
        "accesstoken",
        "refreshtoken",
        "token",
        "secret",
        "password",
        "authorization",
        "credential",
        "credentials",
    }
)


def _is_secret_name(name: object) -> bool:
    normalized = re.sub(r"[^a-z0-9]", "", str(name).lower())
    return (
        normalized in _SECRET_NAMES
        or normalized.startswith("authorization")
        or normalized.endswith(
            ("apikey", "token", "secret", "password", "credential", "credentials")
        )
    )


def _without_secret_fields(value: Any) -> Any:
    """Remove legacy credential-shaped fields without importing runtime code."""

    if isinstance(value, dict):
        return {
            key: _without_secret_fields(child)
            for key, child in value.items()
            if not _is_secret_name(key)
        }
    if isinstance(value, list):
        return [_without_secret_fields(child) for child in value]
    return value


def upgrade() -> None:
    op.create_table(
        "v2_text_provider_profiles",
        sa.Column("id", sa.String(length=63), primary_key=True),
        sa.Column("display_name", sa.String(length=120), nullable=False),
        sa.Column("settings", sa.JSON(), nullable=False),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )

    bind = op.get_bind()
    now = datetime.now(timezone.utc)
    legacy = bind.execute(
        sa.text(
            "SELECT settings, revision, updated_at "
            "FROM v2_provider_settings WHERE id = 1"
        )
    ).mappings().first()
    legacy_settings: dict[str, Any] = {}
    if legacy is not None:
        candidate = legacy["settings"]
        if isinstance(candidate, str):
            try:
                candidate = json.loads(candidate)
            except json.JSONDecodeError:
                candidate = {}
        if isinstance(candidate, dict):
            legacy_settings = _without_secret_fields(candidate)
        # Remove persisted legacy credentials from their original row as well
        # as from the new named-profile seed. Keeping a dormant copy would
        # violate the server-side secret boundary even if no current model
        # reads it.
        bind.execute(
            sa.text("UPDATE v2_provider_settings SET settings = :settings WHERE id = 1"),
            {
                "settings": json.dumps(
                    legacy_settings,
                    ensure_ascii=False,
                    separators=(",", ":"),
                )
            },
        )
    bind.execute(
        sa.text(
            "INSERT INTO v2_text_provider_profiles "
            "(id, display_name, settings, revision, created_at, updated_at) "
            "VALUES (:id, :display_name, :settings, :revision, :created_at, :updated_at)"
        ),
        {
            "id": "default",
            "display_name": "Default",
            # Runtime bootstrap resolves this legacy/public seed with the
            # process environment exactly once.  Secrets are never copied.
            "settings": json.dumps(
                legacy_settings,
                ensure_ascii=False,
                separators=(",", ":"),
            ),
            "revision": int(legacy["revision"]) if legacy is not None else 0,
            "created_at": now,
            "updated_at": legacy["updated_at"] if legacy is not None else now,
        },
    )

    op.create_table(
        "v2_provider_profile_selection",
        sa.Column("id", sa.Integer(), primary_key=True),
        sa.Column(
            "active_profile_id",
            sa.String(length=63),
            sa.ForeignKey("v2_text_provider_profiles.id", ondelete="RESTRICT"),
            nullable=False,
        ),
        sa.Column("revision", sa.Integer(), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
    )
    bind.execute(
        sa.text(
            "INSERT INTO v2_provider_profile_selection "
            "(id, active_profile_id, revision, updated_at) "
            "VALUES (1, 'default', 0, :updated_at)"
        ),
        {"updated_at": now},
    )

    op.create_table(
        "v2_generation_story_graph_topologies",
        sa.Column(
            "run_id",
            sa.String(length=36),
            sa.ForeignKey("v2_generation_runs.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("generation_plan_hash", sa.String(length=64), nullable=False),
        sa.Column("topology_hash", sa.String(length=64), nullable=False),
        sa.Column("topology", sa.JSON(), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
    )
    op.create_index(
        "ix_v2_generation_story_graph_topologies_hash",
        "v2_generation_story_graph_topologies",
        ["topology_hash"],
    )

    with op.batch_alter_table("v2_generation_attempts") as batch:
        batch.add_column(
            sa.Column(
                "attempt_kind",
                sa.String(length=16),
                nullable=False,
                server_default="primary",
            )
        )
        batch.add_column(sa.Column("source_attempt_id", sa.String(length=36), nullable=True))
        batch.add_column(sa.Column("outcome_code", sa.String(length=100), nullable=True))
        batch.create_foreign_key(
            "fk_v2_generation_attempts_source_attempt_id",
            "v2_generation_attempts",
            ["source_attempt_id"],
            ["id"],
            ondelete="RESTRICT",
        )
        batch.create_index(
            "ix_v2_generation_attempts_source_attempt_id",
            ["source_attempt_id"],
        )

    # Runs created before this migration have no frozen topology or V2 profile
    # execution policy.  Rewriting their plan/hash would corrupt evidence, so
    # terminate only non-terminal work and require an explicit fresh run.
    op.execute(
        """
        UPDATE v2_generation_attempts
        SET status = 'failed',
            outcome_code = 'migration.execution_contract_changed',
            error = 'Generation attempt stopped during model-profile migration; submit a new run',
            finished_at = CURRENT_TIMESTAMP
        WHERE status = 'running'
        """
    )
    op.execute(
        """
        UPDATE v2_generation_runs
        SET status = 'failed',
            error = 'Generation run predates the frozen model-profile/topology contract; submit a new run',
            finished_at = CURRENT_TIMESTAMP
        WHERE status IN ('queued', 'running', 'cancel_requested')
        """
    )


def downgrade() -> None:
    with op.batch_alter_table("v2_generation_attempts") as batch:
        batch.drop_index("ix_v2_generation_attempts_source_attempt_id")
        batch.drop_constraint(
            "fk_v2_generation_attempts_source_attempt_id",
            type_="foreignkey",
        )
        batch.drop_column("outcome_code")
        batch.drop_column("source_attempt_id")
        batch.drop_column("attempt_kind")

    op.drop_index(
        "ix_v2_generation_story_graph_topologies_hash",
        table_name="v2_generation_story_graph_topologies",
    )
    op.drop_table("v2_generation_story_graph_topologies")
    op.drop_table("v2_provider_profile_selection")
    op.drop_table("v2_text_provider_profiles")
