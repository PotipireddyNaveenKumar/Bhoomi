"""add task lifecycle fields due_at and expires_at

Revision ID: 002_task_lifecycle
Revises: 001_rec_traces
Create Date: 2026-09-21 01:25:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '002_task_lifecycle'
down_revision: Union[str, Sequence[str], None] = '001_rec_traces'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column('farm_tasks', sa.Column('due_at', sa.DateTime(timezone=True), nullable=True))
    op.add_column('farm_tasks', sa.Column('expires_at', sa.DateTime(timezone=True), nullable=True))
    
    op.create_index('ix_farm_tasks_due_at', 'farm_tasks', ['due_at'])
    op.create_index('ix_farm_tasks_expires_at', 'farm_tasks', ['expires_at'])
    op.create_index('ix_farm_tasks_status_due_at', 'farm_tasks', ['status', 'due_at'])


def downgrade() -> None:
    op.drop_index('ix_farm_tasks_status_due_at', table_name='farm_tasks')
    op.drop_index('ix_farm_tasks_expires_at', table_name='farm_tasks')
    op.drop_index('ix_farm_tasks_due_at', table_name='farm_tasks')
    op.drop_column('farm_tasks', 'expires_at')
    op.drop_column('farm_tasks', 'due_at')
