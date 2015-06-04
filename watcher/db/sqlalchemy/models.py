# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

"""
SQLAlchemy models for watcher service
"""

import json

from oslo_config import cfg
from oslo_db import options as db_options
from oslo_db.sqlalchemy import models
import six.moves.urllib.parse as urlparse
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import schema
from sqlalchemy import String
from sqlalchemy.types import TypeDecorator, TEXT

from watcher.common import paths


sql_opts = [
    cfg.StrOpt('mysql_engine',
               default='InnoDB',
               help='MySQL engine to use.')
]

_DEFAULT_SQL_CONNECTION = 'sqlite:///' + paths.state_path_def('watcher.sqlite')

cfg.CONF.register_opts(sql_opts, 'database')
db_options.set_defaults(cfg.CONF, _DEFAULT_SQL_CONNECTION, 'watcher.sqlite')


def table_args():
    engine_name = urlparse.urlparse(cfg.CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': cfg.CONF.database.mysql_engine,
                'mysql_charset': "utf8"}
    return None


class JsonEncodedType(TypeDecorator):
    """Abstract base type serialized as json-encoded string in db."""
    type = None
    impl = TEXT

    def process_bind_param(self, value, dialect):
        if value is None:
            # Save default value according to current type to keep the
            # interface the consistent.
            value = self.type()
        elif not isinstance(value, self.type):
            raise TypeError("%s supposes to store %s objects, but %s given"
                            % (self.__class__.__name__,
                               self.type.__name__,
                               type(value).__name__))
        serialized_value = json.dumps(value)
        return serialized_value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = json.loads(value)
        return value


class JSONEncodedDict(JsonEncodedType):
    """Represents dict serialized as json-encoded string in db."""
    type = dict


class JSONEncodedList(JsonEncodedType):
    """Represents list serialized as json-encoded string in db."""
    type = list


class WatcherBase(models.SoftDeleteMixin,
                  models.TimestampMixin, models.ModelBase):
    metadata = None

    def as_dict(self):
        d = {}
        for c in self.__table__.columns:
            d[c.name] = self[c.name]
        return d

    def save(self, session=None):
        import watcher.db.sqlalchemy.api as db_api

        if session is None:
            session = db_api.get_session()

        super(WatcherBase, self).save(session)


Base = declarative_base(cls=WatcherBase)


class AuditTemplate(Base):
    """Represents an audit template."""

    __tablename__ = 'audit_templates'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_audit_templates0uuid'),
        schema.UniqueConstraint('name', name='uniq_audit_templates0name'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(63), nullable=True)
    description = Column(String(255), nullable=True)
    host_aggregate = Column(Integer, nullable=True)
    goal = Column(String(63), nullable=True)
    extra = Column(JSONEncodedDict)
    version = Column(String(15), nullable=True)


class Audit(Base):
    """Represents an audit."""

    __tablename__ = 'audits'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_audits0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    type = Column(String(20))
    state = Column(String(20), nullable=True)
    deadline = Column(DateTime, nullable=True)
    audit_template_id = Column(Integer, ForeignKey('audit_templates.id'),
                               nullable=False)


class Action(Base):
    """Represents an action."""

    __tablename__ = 'actions'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_actions0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    action_plan_id = Column(Integer, ForeignKey('action_plans.id'),
                            nullable=True)
    # only for the first version
    action_type = Column(String(255))
    applies_to = Column(String(255))
    src = Column(String(255))
    dst = Column(String(255))
    parameter = Column(String(255))
    description = Column(String(255))
    state = Column(String(20), nullable=True)
    alarm = Column(String(36))
    next = Column(String(36), nullable=True)


class ActionPlan(Base):
    """Represents an action plan."""

    __tablename__ = 'action_plans'
    __table_args__ = (
        schema.UniqueConstraint('uuid', name='uniq_action_plans0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    first_action_id = Column(Integer)
    # first_action_id = Column(Integer, ForeignKeyConstraint(
    #     ['first_action_id'], ['actions.id'], name='fk_first_action_id'),
    #     nullable=True)
    audit_id = Column(Integer, ForeignKey('audits.id'),
                      nullable=True)
    state = Column(String(20), nullable=True)
