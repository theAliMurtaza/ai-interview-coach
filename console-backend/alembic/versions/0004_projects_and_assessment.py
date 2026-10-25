"""Preserve resume project context and detailed answer assessments."""

import sqlalchemy as sa

from alembic import op

revision = "0004"
down_revision = "0003"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column(
        "interviews", sa.Column("resume_projects", sa.JSON(), nullable=False, server_default="[]")
    )
    op.add_column(
        "evaluations", sa.Column("assessment", sa.JSON(), nullable=False, server_default="{}")
    )


def downgrade():
    op.drop_column("evaluations", "assessment")
    op.drop_column("interviews", "resume_projects")
