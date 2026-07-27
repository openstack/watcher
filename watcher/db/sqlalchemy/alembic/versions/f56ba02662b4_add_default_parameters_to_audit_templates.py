"""Add default_parameters to audit_templates

Revision ID: f56ba02662b4
Revises: 7150a7d8f228
Create Date: 2026-05-25 00:00:00.000000
"""

import sqlalchemy as sa

from alembic import op

from watcher.db.sqlalchemy import models


# revision identifiers, used by Alembic.
revision = 'f56ba02662b4'
down_revision = '7150a7d8f228'


def upgrade():
    op.add_column(
        'audit_templates',
        sa.Column(
            'default_parameters', models.JSONEncodedDict(), nullable=True
        ),
    )
