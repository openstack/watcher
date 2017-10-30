"""add name for audit

Revision ID: 3cfc94cecf4e
Revises: d098df6021e2
Create Date: 2017-07-19 15:44:57.661099

"""

# revision identifiers, used by Alembic.
revision = '3cfc94cecf4e'
down_revision = 'd09a5945e4a0'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('audits', sa.Column('name', sa.String(length=63), nullable=True))


def downgrade():
    op.drop_column('audits', 'name')
