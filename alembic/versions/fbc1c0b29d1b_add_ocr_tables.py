"""add_ocr_tables

Revision ID: fbc1c0b29d1b
Revises: d70e1e5fe277
Create Date: 2026-01-05 11:42:38.796662

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


# revision identifiers, used by Alembic.
revision: str = 'fbc1c0b29d1b'
down_revision: Union[str, None] = 'd70e1e5fe277'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # Create ocr_requests table
    op.create_table(
        'ocr_requests',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('user_id', sa.BigInteger(), nullable=False),
        sa.Column('guild_id', sa.BigInteger(), nullable=True),
        sa.Column('channel_id', sa.BigInteger(), nullable=True),
        sa.Column('ocr_type', sa.String(length=50), nullable=False),
        sa.Column('image_count', sa.Integer(), nullable=False),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['user_id'], ['users.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ocr_requests_user_id'), 'ocr_requests', ['user_id'], unique=False)
    op.create_index(op.f('ix_ocr_requests_ocr_type'), 'ocr_requests', ['ocr_type'], unique=False)
    op.create_index(op.f('ix_ocr_requests_created_at'), 'ocr_requests', ['created_at'], unique=False)

    # Create ocr_results table
    op.create_table(
        'ocr_results',
        sa.Column('id', sa.Integer(), autoincrement=True, nullable=False),
        sa.Column('ocr_request_id', sa.Integer(), nullable=False),
        sa.Column('image_index', sa.Integer(), nullable=False),
        sa.Column('extracted_data', postgresql.JSON(astext_type=sa.Text()), nullable=True),
        sa.Column('raw_text', sa.Text(), nullable=True),
        sa.Column('confidence_score', sa.Float(), nullable=True),
        sa.Column('success', sa.Boolean(), nullable=False),
        sa.Column('error_message', sa.Text(), nullable=True),
        sa.Column('created_at', sa.DateTime(timezone=True), server_default=sa.text('now()'), nullable=False),
        sa.ForeignKeyConstraint(['ocr_request_id'], ['ocr_requests.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )
    op.create_index(op.f('ix_ocr_results_ocr_request_id'), 'ocr_results', ['ocr_request_id'], unique=False)


def downgrade() -> None:
    # Drop ocr_results table
    op.drop_index(op.f('ix_ocr_results_ocr_request_id'), table_name='ocr_results')
    op.drop_table('ocr_results')

    # Drop ocr_requests table
    op.drop_index(op.f('ix_ocr_requests_created_at'), table_name='ocr_requests')
    op.drop_index(op.f('ix_ocr_requests_ocr_type'), table_name='ocr_requests')
    op.drop_index(op.f('ix_ocr_requests_user_id'), table_name='ocr_requests')
    op.drop_table('ocr_requests')
