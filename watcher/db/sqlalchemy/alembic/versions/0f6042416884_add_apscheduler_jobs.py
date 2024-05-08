"""Add apscheduler_jobs table to store background jobs

Revision ID: 0f6042416884
Revises: 001
Create Date: 2017-03-24 11:21:29.036532

"""
from alembic import op
from sqlalchemy import inspect
import sqlalchemy as sa

from watcher.db.sqlalchemy import models

# revision identifiers, used by Alembic.
revision = '0f6042416884'
down_revision = '001'

def _table_exists(table_name):
    bind = op.get_context().bind
    insp = inspect(bind)
    names = insp.get_table_names()
    return any(t == table_name for t in names)


def upgrade():
    if _table_exists('apscheduler_jobs'):
        return

    op.create_table(
        'apscheduler_jobs',
        sa.Column('id', sa.Unicode(191),
                  nullable=False),
        sa.Column('next_run_time', sa.Float(25), index=True),
        sa.Column('job_state', sa.LargeBinary, nullable=False),
        sa.Column('service_id', sa.Integer(), nullable=False),
        sa.Column('tag', models.JSONEncodedDict(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.ForeignKeyConstraint(['service_id'], ['services.id'])
    )


def downgrade():
    op.drop_table('apscheduler_jobs')
