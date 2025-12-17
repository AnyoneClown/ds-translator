"""Remove UserStats table

Revision ID: 83898d25754c
Revises: 701b3849f0fd
Create Date: 2025-12-17 22:28:39.393008

"""

from typing import Sequence, Union

import sqlalchemy as sa

from alembic import op

# revision identifiers, used by Alembic.
revision: str = "83898d25754c"
down_revision: Union[str, None] = "701b3849f0fd"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Drop the user_stats table entirely
    op.drop_table("user_stats")

    # ### remaining type/index adjustments from autogenerate ###
    op.alter_column(
        "player_lookup_logs", "user_id", existing_type=sa.INTEGER(), type_=sa.BigInteger(), existing_nullable=False
    )
    op.alter_column(
        "player_lookup_logs", "guild_id", existing_type=sa.INTEGER(), type_=sa.BigInteger(), existing_nullable=True
    )
    op.alter_column(
        "player_lookup_logs", "channel_id", existing_type=sa.INTEGER(), type_=sa.BigInteger(), existing_nullable=True
    )
    op.alter_column(
        "player_lookup_logs",
        "created_at",
        existing_type=sa.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.drop_index("ix_player_lookup_logs_created_at", table_name="player_lookup_logs", postgresql_using="prefix")
    op.create_index(op.f("ix_player_lookup_logs_created_at"), "player_lookup_logs", ["created_at"], unique=False)
    op.drop_index("ix_player_lookup_logs_kingshot_id", table_name="player_lookup_logs", postgresql_using="prefix")
    op.create_index(op.f("ix_player_lookup_logs_kingshot_id"), "player_lookup_logs", ["kingshot_id"], unique=False)
    op.drop_index("ix_player_lookup_logs_user_id", table_name="player_lookup_logs", postgresql_using="prefix")
    op.create_index(op.f("ix_player_lookup_logs_user_id"), "player_lookup_logs", ["user_id"], unique=False)
    op.alter_column(
        "translation_logs", "user_id", existing_type=sa.INTEGER(), type_=sa.BigInteger(), existing_nullable=False
    )
    op.alter_column(
        "translation_logs", "guild_id", existing_type=sa.INTEGER(), type_=sa.BigInteger(), existing_nullable=True
    )
    op.alter_column(
        "translation_logs", "channel_id", existing_type=sa.INTEGER(), type_=sa.BigInteger(), existing_nullable=True
    )
    op.alter_column(
        "translation_logs", "original_text", existing_type=sa.VARCHAR(), type_=sa.Text(), existing_nullable=False
    )
    op.alter_column(
        "translation_logs", "translated_text", existing_type=sa.VARCHAR(), type_=sa.Text(), existing_nullable=False
    )
    op.alter_column(
        "translation_logs",
        "created_at",
        existing_type=sa.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.drop_index("ix_translation_logs_created_at", table_name="translation_logs", postgresql_using="prefix")
    op.create_index(op.f("ix_translation_logs_created_at"), "translation_logs", ["created_at"], unique=False)
    op.drop_index("ix_translation_logs_user_id", table_name="translation_logs", postgresql_using="prefix")
    op.create_index(op.f("ix_translation_logs_user_id"), "translation_logs", ["user_id"], unique=False)
    op.alter_column(
        "users",
        "id",
        existing_type=sa.INTEGER(),
        type_=sa.BigInteger(),
        existing_nullable=False,
        autoincrement=True,
        existing_server_default=sa.text("unique_rowid()"),
    )
    op.alter_column(
        "users",
        "joined_at",
        existing_type=sa.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    op.alter_column(
        "users",
        "last_seen",
        existing_type=sa.TIMESTAMP(),
        type_=sa.DateTime(timezone=True),
        existing_nullable=False,
        existing_server_default=sa.text("now()"),
    )
    # ### end Alembic commands ###


def downgrade() -> None:
    # Recreate the user_stats table if rolling back
    op.create_table(
        "user_stats",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("user_id", sa.INTEGER(), nullable=False),
        sa.Column("translations_requested", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("translations_provided", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("messages_sent", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("commands_used", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("last_translation_at", sa.TIMESTAMP(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.Column("updated_at", sa.TIMESTAMP(), nullable=False, server_default=sa.text("now()")),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.Index("ix_user_stats_user_id", "user_id", postgresql_using="prefix"),
    )
    # ### end Alembic commands ###
