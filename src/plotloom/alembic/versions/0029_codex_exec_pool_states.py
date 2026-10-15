"""Preserve exact attempts while allowing honest queue and validation states."""
import sqlalchemy as sa
from alembic import op

revision = "0029_codex_exec_pool_states"
down_revision = "0028_autopilot_codex_exec_attempts"
branch_labels = None
depends_on = None

TABLE = "v2_autopilot_exec_attempts"
STATE_CONSTRAINT = "ck_v2_autopilot_exec_attempts_state"
CURRENT_STATES = "state IN ('reserved','queued','spawn_intent','running','validating','outcome_unknown','cancel_requested','completed','failed','settled')"
SERIAL_STATES = "state IN ('reserved','spawn_intent','running','outcome_unknown','cancel_requested','completed','failed','settled')"


def _replace_states(expression):
    connection = op.get_bind()
    table = sa.Table(TABLE, sa.MetaData(), autoload_with=connection)
    state_check = next(check for check in table.constraints
        if isinstance(check, sa.CheckConstraint) and str(check.sqltext).startswith("state IN"))
    if str(state_check.sqltext) == expression and state_check.name == STATE_CONSTRAINT:
        return
    # The serial layout had an unnamed check. Name only that reflected check
    # so batch recreation can replace it without dropping unrelated guards.
    state_check.name = STATE_CONSTRAINT
    with op.batch_alter_table(TABLE, copy_from=table) as batch:
        batch.drop_constraint(STATE_CONSTRAINT, type_="check")
        batch.create_check_constraint(STATE_CONSTRAINT, expression)


def upgrade():
    # 0028 creates the current metadata table on a fresh database; preserve its
    # already-current check, while upgrading existing retained serial rows.
    _replace_states(CURRENT_STATES)


def downgrade():
    if op.get_bind().exec_driver_sql(
        f"SELECT 1 FROM {TABLE} WHERE state IN ('queued','validating') LIMIT 1"
    ).first():
        raise RuntimeError("cannot retire retained queued or validating attempt evidence")
    _replace_states(SERIAL_STATES)
