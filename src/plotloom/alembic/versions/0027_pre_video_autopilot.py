"""Typed pre-video run/decision provenance and exclusive image authority."""
from alembic import op
import sqlalchemy as sa

from plotloom.persistence.schema.project_autopilot import AutopilotRunRow, AutopilotCheckpointRow, AutopilotDecisionRow, AutopilotFrameRow, AutopilotHandoffRow

revision = "0027_pre_video_autopilot"
down_revision = "0026_shot_production_presentation"
branch_labels = None
depends_on = None


def upgrade():
    for owner in (AutopilotRunRow, AutopilotCheckpointRow, AutopilotDecisionRow, AutopilotFrameRow, AutopilotHandoffRow):
        owner.__table__.create(op.get_bind())
    with op.batch_alter_table("v2_production_units") as batch:
        batch.alter_column("approval_id", existing_type=sa.String(36), nullable=True)
        batch.add_column(sa.Column("machine_decision_id", sa.String(36), nullable=True))
        batch.create_foreign_key("fk_unit_machine_decision", "v2_autopilot_decisions", ["machine_decision_id", "project_id"], ["id", "project_id"], ondelete="RESTRICT")
        batch.create_check_constraint("ck_production_unit_authority", "(approval_id IS NOT NULL AND machine_decision_id IS NULL) OR (approval_id IS NULL AND machine_decision_id IS NOT NULL)")


def downgrade():
    if op.get_bind().exec_driver_sql("SELECT 1 FROM v2_autopilot_runs LIMIT 1").first():
        raise RuntimeError("cannot retire valued autopilot authority through schema downgrade")
    with op.batch_alter_table("v2_production_units") as batch:
        batch.drop_constraint("ck_production_unit_authority", type_="check")
        batch.drop_constraint("fk_unit_machine_decision", type_="foreignkey")
        batch.drop_column("machine_decision_id")
        batch.alter_column("approval_id", existing_type=sa.String(36), nullable=False)
    for owner in (AutopilotHandoffRow, AutopilotFrameRow, AutopilotDecisionRow, AutopilotCheckpointRow, AutopilotRunRow):
        owner.__table__.drop(op.get_bind())
