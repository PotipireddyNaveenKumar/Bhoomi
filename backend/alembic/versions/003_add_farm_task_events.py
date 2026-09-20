"""add farm task events table for durable reminders and lifecycle events

Revision ID: 003_task_events
Revises: 002_task_lifecycle
Create Date: 2026-09-21 02:00:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '003_task_events'
down_revision: Union[str, Sequence[str], None] = '002_task_lifecycle'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'farm_task_events',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('task_id', sa.String(length=36), nullable=False),
        sa.Column('farmer_id', sa.String(length=36), nullable=False),
        sa.Column('farm_id', sa.String(length=36), nullable=False),
        sa.Column('event_type', sa.String(length=50), nullable=False),
        sa.Column('event_key', sa.String(length=120), nullable=False),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('scheduled_for', sa.DateTime(timezone=True), nullable=True),
        sa.Column('delivered_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('payload', sa.JSON(), nullable=True),
        sa.Column('status', sa.String(length=30), nullable=False, server_default='PENDING'),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmer_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['farm_tasks.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_key', name='uq_farm_task_events_event_key')
    )
    op.create_index('ix_farm_task_events_task_id', 'farm_task_events', ['task_id'])
    op.create_index('ix_farm_task_events_farmer_id', 'farm_task_events', ['farmer_id'])
    op.create_index('ix_farm_task_events_farm_id', 'farm_task_events', ['farm_id'])
    op.create_index('ix_farm_task_events_event_type', 'farm_task_events', ['event_type'])
    op.create_index('ix_farm_task_events_event_key', 'farm_task_events', ['event_key'])
    op.create_index('ix_farm_task_events_status', 'farm_task_events', ['status'])


def downgrade() -> None:
    op.drop_index('ix_farm_task_events_status', table_name='farm_task_events')
    op.drop_index('ix_farm_task_events_event_key', table_name='farm_task_events')
    op.drop_index('ix_farm_task_events_event_type', table_name='farm_task_events')
    op.drop_index('ix_farm_task_events_farm_id', table_name='farm_task_events')
    op.drop_index('ix_farm_task_events_farmer_id', table_name='farm_task_events')
    op.drop_index('ix_farm_task_events_task_id', table_name='farm_task_events')
    op.drop_table('farm_task_events')
