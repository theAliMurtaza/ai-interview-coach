"""Complete feature schema and constraints.
Revision ID: 0002
Revises: 0001
"""

import sqlalchemy as sa
from pgvector.sqlalchemy import Vector
from sqlalchemy.dialects import postgresql as pg

from alembic import op

revision = "0002"
down_revision = "0001"
branch_labels = None
depends_on = None


def base():
    return [
        sa.Column("id", pg.UUID(as_uuid=True), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    ]


def owner():
    return sa.Column(
        "user_id",
        pg.UUID(as_uuid=True),
        sa.ForeignKey("users.id", ondelete="CASCADE"),
        nullable=False,
    )


def json_column(name):
    return sa.Column(name, sa.JSON(), nullable=False)


def upgrade():
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
    op.create_table(
        "resumes",
        *base(),
        owner(),
        sa.Column("filename", sa.String(255), nullable=False),
        sa.Column("file_url", sa.String(1024)),
        sa.Column("raw_text", sa.Text(), nullable=False),
        *[
            json_column(n)
            for n in ["skills", "projects", "experience", "education", "certifications"]
        ],
    )
    op.create_table(
        "jobs",
        *base(),
        owner(),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("company", sa.String(255)),
        sa.Column("raw_text", sa.Text(), nullable=False),
        *[json_column(n) for n in ["required_skills", "preferred_skills", "responsibilities"]],
    )
    op.create_table(
        "learning_plans",
        *base(),
        owner(),
        sa.Column("title", sa.String(255), nullable=False),
        sa.Column("duration_days", sa.Integer(), nullable=False),
        *[
            json_column(n)
            for n in ["focus_topics", "daily_tasks", "milestones", "based_on_interview_ids"]
        ],
    )
    op.create_table(
        "user_topic_performances",
        *base(),
        owner(),
        sa.Column("topic", sa.String(100), nullable=False),
        sa.Column("attempts", sa.Integer(), nullable=False),
        sa.Column("avg_score", sa.Float(), nullable=False),
        sa.Column(
            "last_practiced_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.func.now(),
        ),
        sa.Column("trend", sa.String(50), nullable=False),
        sa.UniqueConstraint("user_id", "topic", name="uq_user_topic"),
    )
    op.create_table(
        "knowledge_chunks",
        *base(),
        sa.Column("topic", sa.String(100), nullable=False),
        sa.Column("source", sa.String(255), nullable=False),
        sa.Column("content", sa.Text(), nullable=False),
        json_column("chunk_metadata"),
        sa.Column("embedding", Vector(1536)),
        sa.Column("embedding_model", sa.String(100)),
    )
    plan = pg.ENUM("free", "pro", name="subscription_plan", create_type=False)
    status = pg.ENUM(
        "active",
        "canceled",
        "past_due",
        "unpaid",
        "trialing",
        "incomplete",
        "incomplete_expired",
        "paused",
        name="subscription_status",
    )
    status.create(op.get_bind(), checkfirst=True)
    status.create_type = False
    op.create_table(
        "subscriptions",
        *base(),
        owner(),
        sa.Column("stripe_customer_id", sa.String(255), nullable=False),
        sa.Column("stripe_subscription_id", sa.String(255), nullable=False),
        sa.Column("plan", plan, nullable=False),
        sa.Column("status", status, nullable=False),
        sa.Column("stripe_created_at", sa.Integer(), nullable=False),
        sa.Column("current_period_end", sa.DateTime(timezone=True)),
    )
    op.create_table(
        "webhook_events",
        sa.Column("id", sa.String(255), primary_key=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
        sa.Column(
            "updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()
        ),
    )
    for table in ["resumes", "jobs", "learning_plans", "user_topic_performances", "subscriptions"]:
        op.create_index(f"ix_{table}_user_id", table, ["user_id"], unique=table == "subscriptions")
    op.create_index("ix_knowledge_chunks_topic", "knowledge_chunks", ["topic"])
    op.create_index("ix_user_topic_performances_topic", "user_topic_performances", ["topic"])
    op.create_index("ix_subscriptions_stripe_customer_id", "subscriptions", ["stripe_customer_id"])
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
        unique=True,
    )
    op.create_unique_constraint("uq_oauth_identity", "users", ["oauth_provider", "oauth_sub"])
    op.create_index(
        "ix_knowledge_embedding_hnsw",
        "knowledge_chunks",
        ["embedding"],
        postgresql_using="hnsw",
        postgresql_ops={"embedding": "vector_cosine_ops"},
    )
    # Migration 0001 redundantly created these unique constraints AND unique indexes.
    op.drop_constraint("users_email_key", "users", type_="unique")
    op.drop_constraint("refresh_tokens_token_key", "refresh_tokens", type_="unique")
    # Existing plaintext refresh tokens are intentionally revoked at this security boundary.
    op.execute("UPDATE refresh_tokens SET revoked = true")
    for table, column in [
        ("interviews", "user_id"),
        ("questions", "interview_id"),
        ("refresh_tokens", "user_id"),
    ]:
        op.create_index(f"ix_{table}_{column}", table, [column])
    op.create_unique_constraint("uq_question_parent", "questions", ["parent_question_id"])
    for table in ["users", "refresh_tokens", "interviews", "questions", "answers", "evaluations"]:
        for column in ["created_at", "updated_at"]:
            op.alter_column(table, column, nullable=False)
    for table, column in [
        ("refresh_tokens", "user_id"),
        ("interviews", "user_id"),
        ("questions", "interview_id"),
        ("answers", "question_id"),
        ("evaluations", "answer_id"),
    ]:
        op.alter_column(table, column, nullable=False)


def downgrade():
    op.create_unique_constraint("users_email_key", "users", ["email"])
    op.create_unique_constraint("refresh_tokens_token_key", "refresh_tokens", ["token"])
    op.drop_constraint("uq_oauth_identity", "users", type_="unique")
    op.drop_constraint("uq_question_parent", "questions", type_="unique")
    for table, column in [
        ("interviews", "user_id"),
        ("questions", "interview_id"),
        ("refresh_tokens", "user_id"),
    ]:
        op.drop_index(f"ix_{table}_{column}", table_name=table)
    for table in [
        "webhook_events",
        "subscriptions",
        "knowledge_chunks",
        "user_topic_performances",
        "learning_plans",
        "jobs",
        "resumes",
    ]:
        op.drop_table(table)
    pg.ENUM(name="subscription_status").drop(op.get_bind(), checkfirst=True)
    for table in ["users", "refresh_tokens", "interviews", "questions", "answers", "evaluations"]:
        for column in ["created_at", "updated_at"]:
            op.alter_column(table, column, nullable=True)
    for table, column in [
        ("refresh_tokens", "user_id"),
        ("interviews", "user_id"),
        ("questions", "interview_id"),
        ("answers", "question_id"),
        ("evaluations", "answer_id"),
    ]:
        op.alter_column(table, column, nullable=True)
