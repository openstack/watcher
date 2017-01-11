"""ocata release

Revision ID: 9894235b4278
Revises: None
Create Date: 2017-02-01 09:40:05.065981

"""
from alembic import op
import oslo_db
import sqlalchemy as sa
from watcher.db.sqlalchemy import models


# revision identifiers, used by Alembic.
revision = '001'
down_revision = None


def upgrade():
    op.create_table(
        'goals',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', oslo_db.sqlalchemy.types.SoftDeleteInteger(),
                  nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=63), nullable=False),
        sa.Column('display_name', sa.String(length=63), nullable=False),
        sa.Column('efficacy_specification', models.JSONEncodedList(),
                  nullable=False),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'deleted', name='uniq_goals0name'),
        sa.UniqueConstraint('uuid', name='uniq_goals0uuid')
    )

    op.create_table(
        'scoring_engines',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', oslo_db.sqlalchemy.types.SoftDeleteInteger(),
                  nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('name', sa.String(length=63), nullable=False),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('metainfo', sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'deleted',
                            name='uniq_scoring_engines0name'),
        sa.UniqueConstraint('uuid', name='uniq_scoring_engines0uuid')
    )

    op.create_table(
        'services',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', oslo_db.sqlalchemy.types.SoftDeleteInteger(),
                  nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('name', sa.String(length=255), nullable=False),
        sa.Column('host', sa.String(length=255), nullable=False),
        sa.Column('last_seen_up', sa.DateTime(), nullable=True),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('host', 'name', 'deleted',
                            name='uniq_services0host0name0deleted')
    )

    op.create_table(
        'strategies',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', oslo_db.sqlalchemy.types.SoftDeleteInteger(),
                  nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=63), nullable=False),
        sa.Column('display_name', sa.String(length=63), nullable=False),
        sa.Column('goal_id', sa.Integer(), nullable=False),
        sa.Column('parameters_spec', models.JSONEncodedDict(),
                  nullable=True),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'deleted', name='uniq_strategies0name'),
        sa.UniqueConstraint('uuid', name='uniq_strategies0uuid')
    )

    op.create_table(
        'audit_templates',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', oslo_db.sqlalchemy.types.SoftDeleteInteger(),
                  nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=63), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('goal_id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=True),
        sa.Column('scope', models.JSONEncodedList(),
                  nullable=True),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('name', 'deleted',
                            name='uniq_audit_templates0name'),
        sa.UniqueConstraint('uuid', name='uniq_audit_templates0uuid')
    )
    op.create_table(
        'audits',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', oslo_db.sqlalchemy.types.SoftDeleteInteger(),
                  nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('audit_type', sa.String(length=20), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=True),
        sa.Column('parameters', models.JSONEncodedDict(), nullable=True),
        sa.Column('interval', sa.Integer(), nullable=True),
        sa.Column('goal_id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=True),
        sa.Column('scope', models.JSONEncodedList(), nullable=True),
        sa.Column('auto_trigger', sa.Boolean(), nullable=False),
        sa.ForeignKeyConstraint(['goal_id'], ['goals.id'], ),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_audits0uuid')
    )
    op.create_table(
        'action_plans',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', oslo_db.sqlalchemy.types.SoftDeleteInteger(),
                  nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('audit_id', sa.Integer(), nullable=False),
        sa.Column('strategy_id', sa.Integer(), nullable=False),
        sa.Column('state', sa.String(length=20), nullable=True),
        sa.Column('global_efficacy', models.JSONEncodedDict(), nullable=True),
        sa.ForeignKeyConstraint(['audit_id'], ['audits.id'], ),
        sa.ForeignKeyConstraint(['strategy_id'], ['strategies.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_action_plans0uuid')
    )

    op.create_table(
        'actions',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', oslo_db.sqlalchemy.types.SoftDeleteInteger(),
                  nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=False),
        sa.Column('action_plan_id', sa.Integer(), nullable=False),
        sa.Column('action_type', sa.String(length=255), nullable=False),
        sa.Column('input_parameters', models.JSONEncodedDict(), nullable=True),
        sa.Column('state', sa.String(length=20), nullable=True),
        sa.Column('parents', models.JSONEncodedList(), nullable=True),
        sa.ForeignKeyConstraint(['action_plan_id'], ['action_plans.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_actions0uuid')
    )

    op.create_table(
        'efficacy_indicators',
        sa.Column('created_at', sa.DateTime(), nullable=True),
        sa.Column('updated_at', sa.DateTime(), nullable=True),
        sa.Column('deleted_at', sa.DateTime(), nullable=True),
        sa.Column('deleted', oslo_db.sqlalchemy.types.SoftDeleteInteger(),
                  nullable=True),
        sa.Column('id', sa.Integer(), nullable=False),
        sa.Column('uuid', sa.String(length=36), nullable=True),
        sa.Column('name', sa.String(length=63), nullable=True),
        sa.Column('description', sa.String(length=255), nullable=True),
        sa.Column('unit', sa.String(length=63), nullable=True),
        sa.Column('value', sa.Numeric(), nullable=True),
        sa.Column('action_plan_id', sa.Integer(), nullable=False),
        sa.ForeignKeyConstraint(['action_plan_id'], ['action_plans.id'], ),
        sa.PrimaryKeyConstraint('id'),
        sa.UniqueConstraint('uuid', name='uniq_efficacy_indicators0uuid')
    )


def downgrade():
    op.drop_table('efficacy_indicators')
    op.drop_table('actions')
    op.drop_table('action_plans')
    op.drop_table('audits')
    op.drop_table('audit_templates')
    op.drop_table('strategies')
    op.drop_table('services')
    op.drop_table('scoring_engines')
    op.drop_table('goals')
