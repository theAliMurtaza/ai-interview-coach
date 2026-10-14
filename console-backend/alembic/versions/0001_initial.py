"""initial schema â€” users, interviews, questions, answers, evaluations

Revision ID: 0001
Revises:
Create Date: 2026-01-01 00:00:00

"""

from collections.abc import Sequence

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision: str = "0001"
down_revision: str | None = None
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    subscription_plan = pg.ENUM("free", "pro", name="subscription_plan")
    interview_role = pg.ENUM(
        "frontend",
        "backend",
        "fullstack",
        "mobile",
        "data-ai",
        "devops",
        "qa",
        name="interview_role",
    )
    interview_type = pg.ENUM(
        "technical", "behavioral", "system-design", "mixed", name="interview_type"
    )
    difficulty_level = pg.ENUM("internship", "junior", "mid", name="difficulty_level")
    interview_status = pg.ENUM(
        "pending", "in_progress", "completed", "abandoned", name="interview_status"
    )

    bind = op.get_bind()
    subscription_plan.create(bind, checkfirst=True)
    interview_role.create(bind, checkfirst=True)
    interview_type.create(bind, checkfirst=True)
    difficulty_level.create(bind, checkfirst=True)
    interview_status.create(bind, checkfirst=True)

    for enum_type in (
        subscription_plan,
        interview_role,
        interview_type,
        difficulty_level,
        interview_status,
    ):
        enum_type.create_type = False

    op.create_table(
        "users",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("email", sa.String(255), nullable=False, unique=True),
        sa.Column("hashed_password", sa.String(255), nullable=True),
        sa.Column("full_name", sa.String(255), nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.true()),
        sa.Column("is_verified", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("oauth_provider", sa.String(50), nullable=True),
        sa.Column("oauth_sub", sa.String(255), nullable=True),
        sa.Column("plan", subscription_plan, nullable=False, server_default="free"),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_users_email", "users", ["email"], unique=True)

    op.create_table(
        "refresh_tokens",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("token", sa.String(512), nullable=False, unique=True),
        sa.Column("revoked", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )
    op.create_index("ix_refresh_tokens_token", "refresh_tokens", ["token"], unique=True)

    op.create_table(
        "interviews",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column("user_id", pg.UUID(as_uuid=True), sa.ForeignKey("users.id", ondelete="CASCADE")),
        sa.Column("role", interview_role, nullable=False),
        sa.Column("interview_type", interview_type, nullable=False),
        sa.Column("difficulty", difficulty_level, nullable=False),
        sa.Column("question_count", sa.Integer, nullable=False, server_default="6"),
        sa.Column("status", interview_status, nullable=False, server_default="pending"),
        sa.Column("overall_score", sa.Float, nullable=True),
        sa.Column("communication_score", sa.Float, nullable=True),
        sa.Column("technical_score", sa.Float, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "questions",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "interview_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("interviews.id", ondelete="CASCADE"),
        ),
        sa.Column("order_index", sa.Integer, nullable=False),
        sa.Column("text", sa.Text, nullable=False),
        sa.Column("expected_concepts", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("follow_up_hint", sa.Text, nullable=True),
        sa.Column("is_follow_up", sa.Boolean, nullable=False, server_default=sa.false()),
        sa.Column(
            "parent_question_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("questions.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "answers",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "question_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("questions.id", ondelete="CASCADE"),
            unique=True,
        ),
        sa.Column("transcript", sa.Text, nullable=False),
        sa.Column("duration_seconds", sa.Float, nullable=False),
        sa.Column("word_count", sa.Integer, nullable=False, server_default="0"),
        sa.Column("audio_file_url", sa.String(1024), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )

    op.create_table(
        "evaluations",
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "answer_id",
            pg.UUID(as_uuid=True),
            sa.ForeignKey("answers.id", ondelete="CASCADE"),
            unique=True,
        ),
        sa.Column("overall_score", sa.Float, nullable=False),
        sa.Column("communication_score", sa.Float, nullable=False),
        sa.Column("technical_score", sa.Float, nullable=True),
        sa.Column("star_score", sa.Float, nullable=True),
        sa.Column("wpm", sa.Integer, nullable=False),
        sa.Column("filler_count", sa.Integer, nullable=False),
        sa.Column("filler_breakdown", sa.JSON, nullable=False, server_default="{}"),
        sa.Column("concepts_hit", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("concepts_missed", sa.JSON, nullable=False, server_default="[]"),
        sa.Column("feedback", sa.Text, nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.func.now()),
    )


def downgrade() -> None:
    op.drop_table("evaluations")
    op.drop_table("answers")
    op.drop_table("questions")
    op.drop_table("interviews")
    op.drop_table("refresh_tokens")
    op.drop_table("users")

    bind = op.get_bind()
    pg.ENUM(name="interview_status").drop(bind, checkfirst=True)
    pg.ENUM(name="difficulty_level").drop(bind, checkfirst=True)
    pg.ENUM(name="interview_type").drop(bind, checkfirst=True)
    pg.ENUM(name="interview_role").drop(bind, checkfirst=True)
    pg.ENUM(name="subscription_plan").drop(bind, checkfirst=True)
