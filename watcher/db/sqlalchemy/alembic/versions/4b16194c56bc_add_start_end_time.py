"""add_start_end_time

Revision ID: 4b16194c56bc
Revises: 52804f2498c4
Create Date: 2018-03-23 00:36:29.031259

"""

# revision identifiers, used by Alembic.
revision = '4b16194c56bc'
down_revision = '52804f2498c4'

from alembic import op
import sqlalchemy as sa


def upgrade():
    op.add_column('audits', sa.Column('start_time', sa.DateTime(), nullable=True))
    op.add_column('audits', sa.Column('end_time', sa.DateTime(), nullable=True))


def downgrade():
    op.drop_column('audits', 'start_time')
    op.drop_column('audits', 'end_time')
