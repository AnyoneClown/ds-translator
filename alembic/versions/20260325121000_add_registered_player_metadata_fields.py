"""Add metadata fields to registered_players

Revision ID: 20260325121000
Revises: cbc56878cd34
Create Date: 2026-03-25 12:10:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260325121000"
down_revision: Union[str, None] = "cbc56878cd34"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column("registered_players", sa.Column("kingdom", sa.String(length=100), nullable=True))
    op.add_column("registered_players", sa.Column("castle_level", sa.String(length=255), nullable=True))


def downgrade() -> None:
    op.drop_column("registered_players", "castle_level")
    op.drop_column("registered_players", "kingdom")
