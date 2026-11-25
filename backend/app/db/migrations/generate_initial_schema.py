"""Regenerate the base schema files from ORM metadata in dependency order.

Run from backend/:  python -m app.db.migrations.generate_initial_schema

Writes:
    app/db/migrations/001_initial_schema.sql
    app/db/migrations/versions/0001_initial.py

The hand-written versions of these files had forward foreign-key references and
drifted from the models. Keep this generator as the single source for 0001.
"""

from pathlib import Path

from sqlalchemy.dialects import postgresql
from sqlalchemy.schema import CreateIndex, CreateTable

import app.models  # noqa: F401  (register every table on Base.metadata)
from app.core.database import Base

HERE = Path(__file__).resolve().parent
DIALECT = postgresql.dialect()


def ddl_statements() -> list:
    statements = ["CREATE EXTENSION IF NOT EXISTS vector;"]
    for table in Base.metadata.sorted_tables:
        statements.append(str(CreateTable(table).compile(dialect=DIALECT)).strip().rstrip(";") + ";")
        for index in table.indexes:
            statements.append(
                str(CreateIndex(index).compile(dialect=DIALECT)).strip().rstrip(";") + ";"
            )
    return statements


def write_sql(statements: list) -> None:
    body = "\n\n".join(statements)
    (HERE / "001_initial_schema.sql").write_text(
        "-- =============================================================================\n"
        "-- Project AURA - Initial Database Schema (Phase 0)\n"
        "-- Generated from ORM metadata by app.db.migrations.generate_initial_schema.\n"
        "-- Tables are emitted in foreign-key dependency order.\n"
        "-- =============================================================================\n\n"
        + body
        + "\n",
        encoding="utf-8",
    )


def write_alembic(statements: list) -> None:
    upgrade_body = "\n".join(
        f"    op.execute(r'''\n{statement}\n    ''')" for statement in statements
    )
    drop_tables = "\n".join(
        f'    op.execute("DROP TABLE IF EXISTS {table.name} CASCADE")'
        for table in reversed(Base.metadata.sorted_tables)
    )
    content = (
        '"""Initial schema — generated from ORM metadata in dependency order."""\n\n'
        "from alembic import op\n\n"
        'revision = "0001_initial"\n'
        "down_revision = None\n"
        "branch_labels = None\n"
        "depends_on = None\n\n\n"
        "def upgrade():\n"
        + upgrade_body
        + "\n\n\n"
        "def downgrade():\n"
        + drop_tables
        + "\n"
    )
    (HERE / "versions" / "0001_initial.py").write_text(content, encoding="utf-8")


def main() -> None:
    statements = ddl_statements()
    write_sql(statements)
    write_alembic(statements)
    print(f"Wrote {len(statements)} DDL statements for {len(Base.metadata.sorted_tables)} tables")


if __name__ == "__main__":
    main()
