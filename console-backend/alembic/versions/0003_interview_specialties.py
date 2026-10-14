"""Save the selected resume and specialty snapshot for each interview."""

import sqlalchemy as sa

from alembic import op

revision = "0003"
down_revision = "0002"
branch_labels = None
depends_on = None


def upgrade():
    op.add_column("interviews", sa.Column("resume_id", sa.Uuid(), nullable=True))
    op.add_column(
        "interviews", sa.Column("specialties", sa.JSON(), nullable=False, server_default="[]")
    )
    op.create_foreign_key(
        "fk_interviews_resume_id_resumes",
        "interviews",
        "resumes",
        ["resume_id"],
        ["id"],
        ondelete="SET NULL",
    )


def downgrade():
    op.drop_constraint("fk_interviews_resume_id_resumes", "interviews", type_="foreignkey")
    op.drop_column("interviews", "specialties")
    op.drop_column("interviews", "resume_id")
