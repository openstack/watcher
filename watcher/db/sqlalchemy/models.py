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

from oslo_db.sqlalchemy import models
from oslo_serialization import jsonutils
from sqlalchemy import Boolean
from sqlalchemy import Column
from sqlalchemy import DateTime
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy import Float
from sqlalchemy import ForeignKey
from sqlalchemy import Integer
from sqlalchemy import LargeBinary
from sqlalchemy import Numeric
from sqlalchemy import orm
from sqlalchemy import String
from sqlalchemy import Text
from sqlalchemy.types import TypeDecorator, TEXT
from sqlalchemy import UniqueConstraint
import urllib.parse as urlparse
from watcher import conf

CONF = conf.CONF


def table_args():
    engine_name = urlparse.urlparse(CONF.database.connection).scheme
    if engine_name == 'mysql':
        return {'mysql_engine': CONF.database.mysql_engine,
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
        serialized_value = jsonutils.dumps(value)
        return serialized_value

    def process_result_value(self, value, dialect):
        if value is not None:
            value = jsonutils.loads(value)
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


Base = declarative_base(cls=WatcherBase)


class Goal(Base):
    """Represents a goal."""

    __tablename__ = 'goals'
    __table_args__ = (
        UniqueConstraint('uuid', name='uniq_goals0uuid'),
        UniqueConstraint('name', 'deleted', name='uniq_goals0name'),
        table_args(),
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36))
    name = Column(String(63), nullable=False)
    display_name = Column(String(63), nullable=False)
    efficacy_specification = Column(JSONEncodedList, nullable=False)


class Strategy(Base):
    """Represents a strategy."""

    __tablename__ = 'strategies'
    __table_args__ = (
        UniqueConstraint('uuid', name='uniq_strategies0uuid'),
        UniqueConstraint('name', 'deleted', name='uniq_strategies0name'),
        table_args()
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36))
    name = Column(String(63), nullable=False)
    display_name = Column(String(63), nullable=False)
    goal_id = Column(Integer, ForeignKey('goals.id'), nullable=False)
    parameters_spec = Column(JSONEncodedDict, nullable=True)

    goal = orm.relationship(Goal, foreign_keys=goal_id, lazy=None)


class AuditTemplate(Base):
    """Represents an audit template."""

    __tablename__ = 'audit_templates'
    __table_args__ = (
        UniqueConstraint('uuid', name='uniq_audit_templates0uuid'),
        UniqueConstraint('name', 'deleted', name='uniq_audit_templates0name'),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    uuid = Column(String(36))
    name = Column(String(63), nullable=True)
    description = Column(String(255), nullable=True)
    goal_id = Column(Integer, ForeignKey('goals.id'), nullable=False)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=True)
    scope = Column(JSONEncodedList)

    goal = orm.relationship(Goal, foreign_keys=goal_id, lazy=None)
    strategy = orm.relationship(Strategy, foreign_keys=strategy_id, lazy=None)


class Audit(Base):
    """Represents an audit."""

    __tablename__ = 'audits'
    __table_args__ = (
        UniqueConstraint('uuid', name='uniq_audits0uuid'),
        UniqueConstraint('name', 'deleted', name='uniq_audits0name'),
        table_args()
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36))
    name = Column(String(63), nullable=True)
    audit_type = Column(String(20))
    state = Column(String(20), nullable=True)
    parameters = Column(JSONEncodedDict, nullable=True)
    interval = Column(String(36), nullable=True)
    goal_id = Column(Integer, ForeignKey('goals.id'), nullable=False)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=True)
    scope = Column(JSONEncodedList, nullable=True)
    auto_trigger = Column(Boolean, nullable=False)
    next_run_time = Column(DateTime, nullable=True)
    hostname = Column(String(255), nullable=True)
    start_time = Column(DateTime, nullable=True)
    end_time = Column(DateTime, nullable=True)
    force = Column(Boolean, nullable=False)

    goal = orm.relationship(Goal, foreign_keys=goal_id, lazy=None)
    strategy = orm.relationship(Strategy, foreign_keys=strategy_id, lazy=None)


class ActionPlan(Base):
    """Represents an action plan."""

    __tablename__ = 'action_plans'
    __table_args__ = (
        UniqueConstraint('uuid', name='uniq_action_plans0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36))
    audit_id = Column(Integer, ForeignKey('audits.id'), nullable=False)
    strategy_id = Column(Integer, ForeignKey('strategies.id'), nullable=False)
    state = Column(String(20), nullable=True)
    global_efficacy = Column(JSONEncodedList, nullable=True)
    hostname = Column(String(255), nullable=True)

    audit = orm.relationship(Audit, foreign_keys=audit_id, lazy=None)
    strategy = orm.relationship(Strategy, foreign_keys=strategy_id, lazy=None)


class Action(Base):
    """Represents an action."""

    __tablename__ = 'actions'
    __table_args__ = (
        UniqueConstraint('uuid', name='uniq_actions0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), nullable=False)
    action_plan_id = Column(Integer, ForeignKey('action_plans.id'),
                            nullable=False)
    # only for the first version
    action_type = Column(String(255), nullable=False)
    input_parameters = Column(JSONEncodedDict, nullable=True)
    state = Column(String(20), nullable=True)
    parents = Column(JSONEncodedList, nullable=True)

    action_plan = orm.relationship(
        ActionPlan, foreign_keys=action_plan_id, lazy=None)


class EfficacyIndicator(Base):
    """Represents an efficacy indicator."""

    __tablename__ = 'efficacy_indicators'
    __table_args__ = (
        UniqueConstraint('uuid', name='uniq_efficacy_indicators0uuid'),
        table_args()
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36))
    name = Column(String(63))
    description = Column(String(255), nullable=True)
    unit = Column(String(63), nullable=True)
    value = Column(Numeric())
    action_plan_id = Column(Integer, ForeignKey('action_plans.id'),
                            nullable=False)

    action_plan = orm.relationship(
        ActionPlan, foreign_keys=action_plan_id, lazy=None)


class ScoringEngine(Base):
    """Represents a scoring engine."""

    __tablename__ = 'scoring_engines'
    __table_args__ = (
        UniqueConstraint('uuid', name='uniq_scoring_engines0uuid'),
        UniqueConstraint('name', 'deleted', name='uniq_scoring_engines0name'),
        table_args()
    )
    id = Column(Integer, primary_key=True, autoincrement=True)
    uuid = Column(String(36), nullable=False)
    name = Column(String(63), nullable=False)
    description = Column(String(255), nullable=True)
    # Metainfo might contain some additional information about the data model.
    # The format might vary between different models (e.g. be JSON, XML or
    # even some custom format), the blob type should cover all scenarios.
    metainfo = Column(Text, nullable=True)


class Service(Base):
    """Represents a service entity"""

    __tablename__ = 'services'
    __table_args__ = (
        UniqueConstraint('host', 'name', 'deleted',
                         name="uniq_services0host0name0deleted"),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    name = Column(String(255), nullable=False)
    host = Column(String(255), nullable=False)
    last_seen_up = Column(DateTime, nullable=True)


class ActionDescription(Base):
    """Represents a action description"""

    __tablename__ = 'action_descriptions'
    __table_args__ = (
        UniqueConstraint('action_type',
                         name="uniq_action_description0action_type"),
        table_args()
    )
    id = Column(Integer, primary_key=True)
    action_type = Column(String(255), nullable=False)
    description = Column(String(255), nullable=False)


class APScheulerJob(Base):
    """Represents apscheduler jobs"""

    __tablename__ = 'apscheduler_jobs'
    __table_args__ = (
        UniqueConstraint('id',
                         name="uniq_apscheduler_jobs0id"),
        table_args()
    )
    id = Column(String(191), nullable=False, primary_key=True)
    next_run_time = Column(Float(25), index=True)
    job_state = Column(LargeBinary, nullable=False)
    tag = Column(JSONEncodedDict(), nullable=True)
    service_id = Column(Integer, ForeignKey('services.id'),
                        nullable=False)

    service = orm.relationship(
        Service, foreign_keys=service_id, lazy=None)
