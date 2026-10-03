"""Append source-bound per-shot production presentation decisions."""
from alembic import op

from plotloom.persistence.schema.project_shot_presentation import ShotPresentationRow

revision = "0026_shot_production_presentation"
down_revision = "0025_reviewed_video_segments"
branch_labels = None
depends_on = None


def upgrade():
    ShotPresentationRow.__table__.create(op.get_bind())


def downgrade():
    ShotPresentationRow.__table__.drop(op.get_bind())
