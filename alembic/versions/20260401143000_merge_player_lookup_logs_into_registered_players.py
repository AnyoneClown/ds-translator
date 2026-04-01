"""merge_player_lookup_logs_into_registered_players

Revision ID: 20260401143000
Revises: 20260325121000
Create Date: 2026-04-01 14:30:00.000000

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "20260401143000"
down_revision: Union[str, None] = "20260325121000"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Seed missing players from latest successful lookups.
    op.execute(
        """
        WITH latest_lookup AS (
            SELECT
                kingshot_id,
                kingshot_name,
                kingdom,
                castle_level,
                user_id,
                ROW_NUMBER() OVER (PARTITION BY kingshot_id ORDER BY created_at DESC, id DESC) AS rn
            FROM player_lookup_logs
            WHERE success = true
        )
        INSERT INTO registered_players (player_id, player_name, kingdom, castle_level, enabled, added_by_user_id)
        SELECT
            latest_lookup.kingshot_id,
            NULLIF(latest_lookup.kingshot_name, ''),
            NULLIF(latest_lookup.kingdom, ''),
            NULLIF(latest_lookup.castle_level, ''),
            false,
            latest_lookup.user_id
        FROM latest_lookup
        WHERE latest_lookup.rn = 1
          AND latest_lookup.kingshot_id IS NOT NULL
          AND latest_lookup.user_id IS NOT NULL
          AND NOT EXISTS (
              SELECT 1
              FROM registered_players rp
              WHERE rp.player_id = latest_lookup.kingshot_id
          )
        """
    )

    # Refresh existing player metadata from latest successful lookups.
    op.execute(
        """
        WITH latest_lookup AS (
            SELECT
                kingshot_id,
                kingshot_name,
                kingdom,
                castle_level,
                ROW_NUMBER() OVER (PARTITION BY kingshot_id ORDER BY created_at DESC, id DESC) AS rn
            FROM player_lookup_logs
            WHERE success = true
        )
        UPDATE registered_players rp
        SET
            player_name = COALESCE(NULLIF(latest_lookup.kingshot_name, ''), rp.player_name),
            kingdom = COALESCE(NULLIF(latest_lookup.kingdom, ''), rp.kingdom),
            castle_level = COALESCE(NULLIF(latest_lookup.castle_level, ''), rp.castle_level),
            updated_at = now()
        FROM latest_lookup
        WHERE latest_lookup.rn = 1
          AND rp.player_id = latest_lookup.kingshot_id
        """
    )

    op.drop_table("player_lookup_logs")


def downgrade() -> None:
    op.create_table(
        "player_lookup_logs",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.BigInteger(), nullable=False),
        sa.Column("guild_id", sa.BigInteger(), nullable=True),
        sa.Column("channel_id", sa.BigInteger(), nullable=True),
        sa.Column("kingshot_id", sa.String(length=255), nullable=False),
        sa.Column("kingshot_name", sa.String(length=255), nullable=True),
        sa.Column("kingdom", sa.String(length=100), nullable=True),
        sa.Column("castle_level", sa.String(length=255), nullable=True),
        sa.Column("success", sa.Boolean(), nullable=False),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
        ),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index(op.f("ix_player_lookup_logs_created_at"), "player_lookup_logs", ["created_at"], unique=False)
    op.create_index(op.f("ix_player_lookup_logs_kingshot_id"), "player_lookup_logs", ["kingshot_id"], unique=False)
    op.create_index(op.f("ix_player_lookup_logs_user_id"), "player_lookup_logs", ["user_id"], unique=False)

    op.execute(
        """
        INSERT INTO player_lookup_logs (user_id, kingshot_id, kingshot_name, kingdom, castle_level, success)
        SELECT added_by_user_id, player_id, player_name, kingdom, castle_level, true
        FROM registered_players
        WHERE added_by_user_id IS NOT NULL
        """
    )
