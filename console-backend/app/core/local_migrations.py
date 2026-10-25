"""Additive upgrades for the standalone SQLite development launcher."""

from sqlalchemy import inspect, text


def upgrade_local_database(connection):
    columns = {column["name"] for column in inspect(connection).get_columns("interviews")}
    if "resume_id" not in columns:
        connection.execute(
            text(
                "ALTER TABLE interviews ADD COLUMN resume_id CHAR(32) REFERENCES resumes(id) ON"
                " DELETE SET NULL"
            )
        )
    if "specialties" not in columns:
        connection.execute(
            text("ALTER TABLE interviews ADD COLUMN specialties JSON NOT NULL DEFAULT '[]'")
        )
    if "resume_projects" not in columns:
        connection.execute(
            text("ALTER TABLE interviews ADD COLUMN resume_projects JSON NOT NULL DEFAULT '[]'")
        )
    inspector = inspect(connection)
    if inspector.has_table("evaluations") and "assessment" not in {
        column["name"] for column in inspector.get_columns("evaluations")
    }:
        connection.execute(
            text("ALTER TABLE evaluations ADD COLUMN assessment JSON NOT NULL DEFAULT '{}'")
        )
