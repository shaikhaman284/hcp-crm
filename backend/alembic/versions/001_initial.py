"""Initial migration: create hcps and hcp_interactions tables

Revision ID: 001_initial
Revises:
Create Date: 2024-01-01 00:00:00.000000

"""
from typing import Sequence, Union
from alembic import op
from sqlalchemy import text

revision: str = "001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None

# asyncpg requires each statement to be executed individually (no multi-statement strings).
# We also use explicit pg_type checks instead of CREATE TYPE IF NOT EXISTS
# (asyncpg does not support that syntax via prepared statements).

STATEMENTS_UPGRADE = [
    # ENUM: interaction_type_enum — only if missing
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'interaction_type_enum') THEN
            CREATE TYPE interaction_type_enum AS ENUM
                ('Meeting', 'Call', 'Email', 'Conference', 'Visit');
        END IF;
    END $$
    """,
    # ENUM: sentiment_enum — only if missing
    """
    DO $$ BEGIN
        IF NOT EXISTS (SELECT 1 FROM pg_type WHERE typname = 'sentiment_enum') THEN
            CREATE TYPE sentiment_enum AS ENUM ('Positive', 'Neutral', 'Negative');
        END IF;
    END $$
    """,
    # hcps table
    """
    CREATE TABLE IF NOT EXISTS hcps (
        id             UUID PRIMARY KEY,
        name           VARCHAR(255) NOT NULL,
        specialization VARCHAR(255),
        hospital       VARCHAR(255),
        created_at     TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_hcps_name ON hcps (name)",
    # hcp_interactions table
    """
    CREATE TABLE IF NOT EXISTS hcp_interactions (
        id                  UUID PRIMARY KEY,
        hcp_name            VARCHAR(255) NOT NULL,
        interaction_type    interaction_type_enum NOT NULL DEFAULT 'Meeting',
        interaction_date    DATE,
        interaction_time    TIME,
        attendees           TEXT[],
        topics_discussed    TEXT,
        materials_shared    TEXT[],
        samples_distributed TEXT[],
        sentiment           sentiment_enum DEFAULT 'Neutral',
        outcomes            TEXT,
        follow_up_actions   TEXT,
        ai_summary          TEXT,
        created_at          TIMESTAMPTZ NOT NULL DEFAULT now(),
        updated_at          TIMESTAMPTZ NOT NULL DEFAULT now()
    )
    """,
    "CREATE INDEX IF NOT EXISTS ix_hcp_interactions_hcp_name ON hcp_interactions (hcp_name)",
]

STATEMENTS_DOWNGRADE = [
    "DROP INDEX IF EXISTS ix_hcp_interactions_hcp_name",
    "DROP INDEX IF EXISTS ix_hcps_name",
    "DROP TABLE IF EXISTS hcp_interactions",
    "DROP TABLE IF EXISTS hcps",
    "DROP TYPE IF EXISTS interaction_type_enum",
    "DROP TYPE IF EXISTS sentiment_enum",
]


def upgrade() -> None:
    conn = op.get_bind()
    for stmt in STATEMENTS_UPGRADE:
        conn.execute(text(stmt))


def downgrade() -> None:
    conn = op.get_bind()
    for stmt in STATEMENTS_DOWNGRADE:
        conn.execute(text(stmt))
