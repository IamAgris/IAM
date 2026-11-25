"""Generate the initial Alembic migration offline from Base.metadata.

Uses SQLAlchemy's PostgreSQL DDL compiler directly — no DBAPI driver needed.
This avoids asyncpg (whose C extension is blocked by some Windows App Control
policies) and produces Alembic-compatible upgrade()/downgrade() SQL.
"""

import os
from sqlalchemy.schema import CreateTable, CreateIndex
from sqlalchemy.dialects import postgresql

from app.core.database import Base
import app.models  # noqa: F401 — registers all models on Base.metadata

OUT = os.path.join(os.path.dirname(__file__), "app", "db", "migrations", "versions", "0001_initial.py")
dialect = postgresql.dialect()


def compile_ddl():
    lines = []
    for table in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
        lines.append(f"    # --- {table.name} ---")
        lines.append("    op.execute(r'''")
        lines.append(str(CreateTable(table).compile(dialect=dialect)).strip() + ";")
        lines.append("    ''')")
        lines.append("")
    return "\n".join(lines)


def compile_indexes():
    lines = []
    for table in sorted(Base.metadata.tables.values(), key=lambda t: t.name):
        for index in table.indexes:
            lines.append("    op.execute(r'''")
            lines.append(str(CreateIndex(index).compile(dialect=dialect)).strip() + ";")
            lines.append("    ''')")
    return "\n".join(lines) if lines else "    pass"


dialect_rt = "postgresql+asyncpg://aura:aura@localhost/aura_db"

content = f'''"""initial schema

Revision ID: 0001_initial
Revises: None
Create Date: 2026-11-24

Generated offline from SQLAlchemy Base.metadata (see generate_migration.py).
"""
from alembic import op

revision = "0001_initial"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.execute("CREATE EXTENSION IF NOT EXISTS vector")
{compile_ddl()}

    # Indexes
{compile_indexes()}


def downgrade() -> None:
    for name in reversed([{', '.join(repr(t) for t in sorted(Base.metadata.tables.keys()))}]):
        op.execute(f'DROP TABLE IF EXISTS {{name}} CASCADE')
'''

with open(OUT, "w", encoding="utf-8") as f:
    f.write(content)

print(f"Wrote {OUT}")
print(f"Tables: {len(Base.metadata.tables)}")
