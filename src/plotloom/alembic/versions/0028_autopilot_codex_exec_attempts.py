"""Persist one immutable Codex Exec attempt per autopilot job."""
from alembic import op
import sqlalchemy as sa

from plotloom.persistence.schema.project_autopilot import AutopilotExecAttemptRow

revision = "0028_autopilot_codex_exec_attempts"
down_revision = "0027_pre_video_autopilot"
branch_labels = None
depends_on = None


def upgrade():
    checks = sa.inspect(op.get_bind()).get_check_constraints("v2_autopilot_checkpoints")
    if not any("'failed'" in check["sqltext"] for check in checks):
        with op.batch_alter_table("v2_autopilot_checkpoints") as batch:
            for check in checks:
                if check.get("name") and "state IN" in check["sqltext"]:
                    batch.drop_constraint(check["name"], type_="check")
            batch.create_check_constraint(
                "ck_v2_autopilot_checkpoints_state",
                "state IN ('prepared','sent','outcome_unknown','failed','delivered','adopted')",
            )
    AutopilotExecAttemptRow.__table__.create(op.get_bind())


def downgrade():
    connection = op.get_bind()
    if connection.exec_driver_sql("SELECT 1 FROM v2_autopilot_exec_attempts LIMIT 1").first():
        raise RuntimeError("cannot retire retained Codex Exec attempt and budget evidence")
    if connection.exec_driver_sql(
        "SELECT 1 FROM v2_autopilot_checkpoints WHERE state='failed' LIMIT 1"
    ).first():
        raise RuntimeError("cannot retire retained failed checkpoint evidence")
    AutopilotExecAttemptRow.__table__.drop(connection)
    with op.batch_alter_table("v2_autopilot_checkpoints") as batch:
        batch.drop_constraint("ck_v2_autopilot_checkpoints_state", type_="check")
        batch.create_check_constraint(
            "ck_v2_autopilot_checkpoints_state",
            "state IN ('prepared','sent','outcome_unknown','delivered','adopted')",
        )
