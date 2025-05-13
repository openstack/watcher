"""change_efficiacy_indicator_decimals

Revision ID: 15f7375ca737
Revises: 609bec748f2a
Create Date: 2025-03-24 10:15:19.269061

"""""

# revision identifiers, used by Alembic.
revision = '15f7375ca737'
down_revision = '609bec748f2a'

from alembic import op
import sqlalchemy as sa

def upgrade():
    op.add_column('efficacy_indicators',
                  sa.Column('data', sa.Float())
                 )

