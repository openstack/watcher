"""Add cron support for audit table

Revision ID: d098df6021e2
Revises: 0f6042416884
Create Date: 2017-06-08 16:21:35.746752

"""
from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd098df6021e2'
down_revision = '0f6042416884'


def upgrade():
    op.alter_column('audits', 'interval', existing_type=sa.String(36),
                    nullable=True)
    op.add_column('audits',
                  sa.Column('next_run_time', sa.DateTime(), nullable=True))


def downgrade():
    op.alter_column('audits', 'interval', existing_type=sa.Integer(),
                    nullable=True)
    op.drop_column('audits', 'next_run_time')
