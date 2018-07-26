"""Add hostname field to both Audit and Action Plan models

Revision ID: 52804f2498c4
Revises: a86240e89a29
Create Date: 2018-06-26 13:06:45.530387

"""

# revision identifiers, used by Alembic.
revision = '52804f2498c4'
down_revision = 'a86240e89a29'

from alembic import op
import sqlalchemy as sa


def upgrade():
    for table in ('audits', 'action_plans'):
        op.add_column(
            table,
            sa.Column('hostname', sa.String(length=255), nullable=True))


def downgrade():
    for table in ('audits', 'action_plans'):
        op.drop_column(table, 'hostname')
