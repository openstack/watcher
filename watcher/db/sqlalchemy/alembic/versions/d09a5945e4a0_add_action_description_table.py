"""add action description table

Revision ID: d09a5945e4a0
Revises: d098df6021e2
Create Date: 2017-07-13 20:33:01.473711

"""

from alembic import op
import oslo_db
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision = 'd09a5945e4a0'
down_revision = 'd098df6021e2'


def upgrade():
    op.create_table(
        'action_descriptions',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', oslo_db.sqlalchemy.types.SoftDeleteInteger(),
                  nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=255), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('action_type',
                            name='uniq_action_description0action_type')
    )


def downgrade():
    op.drop_table('action_descriptions')
