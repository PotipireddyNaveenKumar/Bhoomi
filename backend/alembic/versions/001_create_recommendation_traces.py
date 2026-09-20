"""create recommendation_traces table

Revision ID: 001_rec_traces
Revises: 
Create Date: 2026-09-21 00:10:00.000000

"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


# revision identifiers, used by Alembic.
revision: str = '001_rec_traces'
down_revision: Union[str, Sequence[str], None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        'recommendation_traces',
        sa.Column('id', sa.String(length=36), nullable=False),
        sa.Column('decision_id', sa.String(length=64), nullable=False),
        sa.Column('recommendation_id', sa.String(length=64), nullable=False),
        sa.Column('farmer_id', sa.String(length=36), nullable=False),
        sa.Column('farm_id', sa.String(length=64), nullable=True),
        sa.Column('decision_type', sa.String(length=100), nullable=True),
        sa.Column('intent', sa.String(length=100), nullable=True),
        sa.Column('created_at', sa.DateTime(), nullable=False),
        sa.Column('updated_at', sa.DateTime(), nullable=False),
        sa.Column('input_context', sa.JSON(), nullable=False),
        sa.Column('data_freshness', sa.JSON(), nullable=False),
        sa.Column('tools_used', sa.JSON(), nullable=False),
        sa.Column('model_versions', sa.JSON(), nullable=False),
        sa.Column('rag_sources', sa.JSON(), nullable=False),
        sa.Column('weather_source', sa.String(length=100), nullable=True),
        sa.Column('market_source', sa.String(length=100), nullable=True),
        sa.Column('calculations', sa.JSON(), nullable=False),
        sa.Column('safety_checks', sa.JSON(), nullable=False),
        sa.Column('recommendation_text', sa.Text(), nullable=False),
        sa.Column('confidence', sa.Float(), nullable=False),
        sa.Column('assumptions', sa.JSON(), nullable=False),
        sa.Column('rationale', sa.Text(), nullable=True),
        sa.Column('evidence', sa.JSON(), nullable=False),
        sa.Column('xai_info', sa.JSON(), nullable=False),
        sa.Column('farmer_action', sa.String(length=50), nullable=False),
        sa.Column('outcome', sa.Text(), nullable=True),
        sa.Column('feedback_rating', sa.String(length=50), nullable=True),
        sa.Column('feedback_notes', sa.Text(), nullable=True),
        sa.Column('locale', sa.String(length=20), nullable=False),
        sa.Column('metadata_json', sa.JSON(), nullable=False),
        sa.ForeignKeyConstraint(['farmer_id'], ['farmer_profiles.id'], ondelete='CASCADE'),
        sa.PrimaryKeyConstraint('id')
    )

    # Unique index on decision_id
    op.create_index('ix_recommendation_traces_decision_id', 'recommendation_traces', ['decision_id'], unique=True)
    # Individual lookup indexes
    op.create_index('ix_recommendation_traces_recommendation_id', 'recommendation_traces', ['recommendation_id'], unique=False)
    op.create_index('ix_recommendation_traces_farmer_id', 'recommendation_traces', ['farmer_id'], unique=False)
    op.create_index('ix_recommendation_traces_farm_id', 'recommendation_traces', ['farm_id'], unique=False)
    op.create_index('ix_recommendation_traces_decision_type', 'recommendation_traces', ['decision_type'], unique=False)
    op.create_index('ix_recommendation_traces_farmer_action', 'recommendation_traces', ['farmer_action'], unique=False)
    op.create_index('ix_recommendation_traces_created_at', 'recommendation_traces', ['created_at'], unique=False)

    # Composite query indexes
    op.create_index('ix_rec_traces_farmer_created', 'recommendation_traces', ['farmer_id', 'created_at'], unique=False)
    op.create_index('ix_rec_traces_farm_created', 'recommendation_traces', ['farm_id', 'created_at'], unique=False)
    op.create_index('ix_rec_traces_farmer_type', 'recommendation_traces', ['farmer_id', 'decision_type'], unique=False)


def downgrade() -> None:
    op.drop_index('ix_rec_traces_farmer_type', table_name='recommendation_traces')
    op.drop_index('ix_rec_traces_farm_created', table_name='recommendation_traces')
    op.drop_index('ix_rec_traces_farmer_created', table_name='recommendation_traces')
    op.drop_index('ix_recommendation_traces_created_at', table_name='recommendation_traces')
    op.drop_index('ix_recommendation_traces_farmer_action', table_name='recommendation_traces')
    op.drop_index('ix_recommendation_traces_decision_type', table_name='recommendation_traces')
    op.drop_index('ix_recommendation_traces_farm_id', table_name='recommendation_traces')
    op.drop_index('ix_recommendation_traces_farmer_id', table_name='recommendation_traces')
    op.drop_index('ix_recommendation_traces_recommendation_id', table_name='recommendation_traces')
    op.drop_index('ix_recommendation_traces_decision_id', table_name='recommendation_traces')
    op.drop_table('recommendation_traces')
