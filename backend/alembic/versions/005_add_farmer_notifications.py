"""add farmer notifications table for durable delivery and inbox

Revision ID: 005_farmer_notifications
Revises: 004_scheduler_state
Create Date: 2026-09-21 03:30:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '005_farmer_notifications'
down_revision: Union[str, Sequence[str], None] = '004_scheduler_state'
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'farmer_notifications',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('farmer_id', sa.String(length=36), nullable=False),
        sa.Column('farm_id', sa.String(length=36), nullable=False),
        sa.Column('task_id', sa.String(length=36), nullable=False),
        sa.Column('event_id', sa.String(length=36), nullable=False),
        sa.Column('event_key', sa.String(length=120), nullable=False),
        sa.Column('notification_type', sa.String(length=50), nullable=False),
        sa.Column('title', sa.Text(), nullable=False),
        sa.Column('message', sa.Text(), nullable=False),
        sa.Column('locale', sa.String(length=10), nullable=False, server_default='en'),
        sa.Column('priority', sa.String(length=20), nullable=False, server_default='MEDIUM'),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('read_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('acknowledged_at', sa.DateTime(timezone=True), nullable=True),
        sa.Column('meta_payload', sa.JSON(), nullable=True),
        sa.ForeignKeyConstraint(['farm_id'], ['farms.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmer_profiles.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['task_id'], ['farm_tasks.id'], ondelete='CASCADE'),
        sa.ForeignKeyConstraint(['event_id'], ['farm_task_events.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('event_id', name='uq_farmer_notifications_event_id')
    )
    op.create_index('ix_farmer_notifications_farmer_id', 'farmer_notifications', ['farmer_id'])
    op.create_index('ix_farmer_notifications_farm_id', 'farmer_notifications', ['farm_id'])
    op.create_index('ix_farmer_notifications_task_id', 'farmer_notifications', ['task_id'])
    op.create_index('ix_farmer_notifications_event_id', 'farmer_notifications', ['event_id'])
    op.create_index('ix_farmer_notifications_event_key', 'farmer_notifications', ['event_key'])
    op.create_index('ix_farmer_notifications_notification_type', 'farmer_notifications', ['notification_type'])
    op.create_index('ix_farmer_notifications_created_at', 'farmer_notifications', ['created_at'])
    op.create_index('ix_farmer_notifications_farmer_created', 'farmer_notifications', ['farmer_id', 'created_at'])
    op.create_index('ix_farmer_notifications_farmer_read', 'farmer_notifications', ['farmer_id', 'read_at'])


def downgrade() -> None:
    op.drop_index('ix_farmer_notifications_farmer_read', table_name='farmer_notifications')
    op.drop_index('ix_farmer_notifications_farmer_created', table_name='farmer_notifications')
    op.drop_index('ix_farmer_notifications_created_at', table_name='farmer_notifications')
    op.drop_index('ix_farmer_notifications_notification_type', table_name='farmer_notifications')
    op.drop_index('ix_farmer_notifications_event_key', table_name='farmer_notifications')
    op.drop_index('ix_farmer_notifications_event_id', table_name='farmer_notifications')
    op.drop_index('ix_farmer_notifications_task_id', table_name='farmer_notifications')
    op.drop_index('ix_farmer_notifications_farm_id', table_name='farmer_notifications')
    op.drop_index('ix_farmer_notifications_farmer_id', table_name='farmer_notifications')
    op.drop_table('farmer_notifications')
