"""Preserve original runs while admitting explicit material successors."""
import sqlalchemy as sa
from alembic import op

revision = "0030_autopilot_continuation"
down_revision = "0029_codex_exec_pool_states"
branch_labels = None
depends_on = None


def upgrade():
    from plotloom.persistence.schema import AutopilotInheritanceRow
    connection = op.get_bind()
    columns = {column["name"] for column in sa.inspect(connection).get_columns("v2_autopilot_runs")}
    if "predecessor_run_id" not in columns:
        table = sa.Table("v2_autopilot_runs", sa.MetaData(), autoload_with=connection)
        project_unique = next(constraint for constraint in table.constraints
            if isinstance(constraint, sa.UniqueConstraint) and list(constraint.columns.keys()) == ["project_id"])
        project_unique.name = "uq_autopilot_single_run"
        with op.batch_alter_table("v2_autopilot_runs", copy_from=table) as batch:
            batch.drop_constraint(project_unique.name, type_="unique")
            batch.add_column(sa.Column("predecessor_run_id", sa.String(36), nullable=True))
            batch.create_foreign_key("fk_autopilot_predecessor", "v2_autopilot_runs", ["predecessor_run_id"], ["id"], ondelete="RESTRICT")
            batch.create_unique_constraint("uq_autopilot_predecessor", ["predecessor_run_id"])
        op.create_index("ix_v2_autopilot_root", "v2_autopilot_runs", ["project_id"], unique=True,
            sqlite_where=sa.text("predecessor_run_id IS NULL"))
    AutopilotInheritanceRow.__table__.create(connection, checkfirst=True)


def downgrade():
    raise RuntimeError("retained material lineage cannot be discarded")
