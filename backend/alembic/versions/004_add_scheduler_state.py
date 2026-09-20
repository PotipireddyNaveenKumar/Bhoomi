"""add task scheduler state table for background execution observability

Revision ID: 004_scheduler_state
Revises: 003_task_events
Create Date: 2026-09-21 02:20:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '004_scheduler_state'
down_revision: Union[str, Sequence[str], None] = '003_task_events'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'task_scheduler_state',
        sa.Column('id', sa.String(length=50), nullable=False),
        sa.Column('last_run_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('consecutive_ticks', sa.Integer(), nullable=False, server_default='0'),
        sa.Column('interval_seconds', sa.Integer(), nullable=False, server_default='900'),
        sa.Column('process_pid', sa.Integer(), nullable=True),
        sa.Column('last_lock_acquired', sa.Boolean(), nullable=False, server_default=sa.true()),
        sa.Column('last_run_stats', sa.JSON(), nullable=True),
        sa.Column('last_run_logs', sa.JSON(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.PrimaryKeyConstraint('id')
    )


def downgrade() -> None:
    op.drop_table('task_scheduler_state')
