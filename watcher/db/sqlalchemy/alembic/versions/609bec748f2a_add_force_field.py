"""add_force_field

Revision ID: 609bec748f2a
Revises: 4b16194c56bc
Create Date: 2019-05-05 14:06:14.249124

"""

# revision identifiers, used by Alembic.
revision = '609bec748f2a'
down_revision = '4b16194c56bc'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('audits', sa.Column('force', sa.Boolean, default=False))


def downgrade():
    op.drop_column('audits', 'force')
