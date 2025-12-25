"""Change castle_level from Integer to String.

Revision ID: 20251222113909
Revises: 83898d25754c
Create Date: 2025-12-22 11:39:09.000000

"""

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision = "20251222113909"
down_revision = "83898d25754c"
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Add a new temporary string column
    op.add_column(
        "player_lookup_logs",
        sa.Column("castle_level_str", sa.String(255), nullable=True),
    )

    # Copy data from integer column to string column
    op.execute(
        "UPDATE player_lookup_logs SET castle_level_str = CAST(castle_level AS VARCHAR) WHERE castle_level IS NOT NULL"
    )

    # Drop the old integer column
    op.drop_column("player_lookup_logs", "castle_level")

    # Rename the new column to the original name
    op.alter_column("player_lookup_logs", "castle_level_str", new_column_name="castle_level")


def downgrade() -> None:
    # Add a new temporary integer column
    op.add_column(
        "player_lookup_logs",
        sa.Column("castle_level_int", sa.Integer(), nullable=True),
    )

    # Copy data from string column to integer column (only valid numbers)
    op.execute(
        "UPDATE player_lookup_logs SET castle_level_int = CAST(castle_level AS INTEGER) WHERE castle_level IS NOT NULL AND castle_level ~ '^[0-9]+$'"
    )

    # Drop the string column
    op.drop_column("player_lookup_logs", "castle_level")

    # Rename the new column to the original name
    op.alter_column("player_lookup_logs", "castle_level_int", new_column_name="castle_level")
