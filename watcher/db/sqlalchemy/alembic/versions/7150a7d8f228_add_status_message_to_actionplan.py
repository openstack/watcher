"""Add status_message to Audits, ActionPlans and Actions
Revision ID: 7150a7d8f228
Revises: 15f7375ca737
Create Date: 2025-07-03 11:57:05.875500
"""

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = '7150a7d8f228'
down_revision = '15f7375ca737'
def upgrade():
    op.add_column('action_plans',
        sa.Column('status_message', sa.String(length=255), nullable=True)
        )
    op.add_column('actions',
        sa.Column('status_message', sa.String(length=255), nullable=True)
        )
    op.add_column('audits',
        sa.Column('status_message', sa.String(length=255), nullable=True)
        )
