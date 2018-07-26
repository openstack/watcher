"""Set name for Audit as part of backward compatibility

Revision ID: a86240e89a29
Revises: 3cfc94cecf4e
Create Date: 2017-12-21 13:00:09.278587

"""

# revision identifiers, used by Alembic.
revision = 'a86240e89a29'
down_revision = '3cfc94cecf4e'

from alembic import op
from sqlalchemy.orm import sessionmaker
from watcher.db.sqlalchemy import models


def upgrade():
    connection = op.get_bind()
    session = sessionmaker()
    s = session(bind=connection)
    audits = s.query(
        models.Audit.strategy_id.label('strategy_id'),
        models.Audit.created_at.label('created_at')).filter(
        models.Audit.name is None).all()
    for audit in audits:
        strategy_name = s.query(models.Strategy).filter_by(
            id=audit.strategy_id).one().name
        s.query().filter(models.Audit.name is None).update(
            {'name': strategy_name + '-' + str(audit.created_at)})
    s.commit()


def downgrade():
    connection = op.get_bind()
    session = sessionmaker()
    s = session(bind=connection)
    audits = s.query(
        models.Audit.strategy_id.label('strategy_id'),
        models.Audit.created_at.label('created_at')).filter(
        models.Audit.name is not None).all()
    for audit in audits:
        s.query().filter(models.Audit.name is not None).update(
            {'name': None})
    s.commit()
