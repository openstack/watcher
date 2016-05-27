# -*- encoding: utf-8 -*-
#
# Copyright 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.


"""SQLAlchemy storage backend."""

from oslo_config import cfg
from oslo_db import exception as db_exc
from oslo_db.sqlalchemy import session as db_session
from oslo_db.sqlalchemy import utils as db_utils
from sqlalchemy.orm import exc

from watcher import _i18n
from watcher.common import exception
from watcher.common import utils
from watcher.db import api
from watcher.db.sqlalchemy import models
from watcher.objects import action as action_objects
from watcher.objects import action_plan as ap_objects
from watcher.objects import audit as audit_objects
from watcher.objects import utils as objutils

CONF = cfg.CONF
_ = _i18n._

_FACADE = None


def _create_facade_lazily():
    global _FACADE
    if _FACADE is None:
        _FACADE = db_session.EngineFacade.from_config(CONF)
    return _FACADE


def get_engine():
    facade = _create_facade_lazily()
    return facade.get_engine()


def get_session(**kwargs):
    facade = _create_facade_lazily()
    return facade.get_session(**kwargs)


def get_backend():
    """The backend is this module itself."""
    return Connection()


def model_query(model, *args, **kwargs):
    """Query helper for simpler session usage.

    :param session: if present, the session to use
    """

    session = kwargs.get('session') or get_session()
    query = session.query(model, *args)
    return query


def add_identity_filter(query, value):
    """Adds an identity filter to a query.

    Filters results by ID, if supplied value is a valid integer.
    Otherwise attempts to filter results by UUID.

    :param query: Initial query to add filter to.
    :param value: Value for filtering results by.
    :return: Modified query.
    """
    if utils.is_int_like(value):
        return query.filter_by(id=value)
    elif utils.is_uuid_like(value):
        return query.filter_by(uuid=value)
    else:
        raise exception.InvalidIdentity(identity=value)


def _paginate_query(model, limit=None, marker=None, sort_key=None,
                    sort_dir=None, query=None):
    if not query:
        query = model_query(model)
    sort_keys = ['id']
    if sort_key and sort_key not in sort_keys:
        sort_keys.insert(0, sort_key)
    query = db_utils.paginate_query(query, model, limit, sort_keys,
                                    marker=marker, sort_dir=sort_dir)
    return query.all()


class Connection(api.BaseConnection):
    """SqlAlchemy connection."""

    def __init__(self):
        super(Connection, self).__init__()

    def __add_soft_delete_mixin_filters(self, query, filters, model):
        if 'deleted' in filters:
            if bool(filters['deleted']):
                query = query.filter(model.deleted != 0)
            else:
                query = query.filter(model.deleted == 0)
        if 'deleted_at__eq' in filters:
            query = query.filter(
                model.deleted_at == objutils.datetime_or_str_or_none(
                    filters['deleted_at__eq']))
        if 'deleted_at__gt' in filters:
            query = query.filter(
                model.deleted_at > objutils.datetime_or_str_or_none(
                    filters['deleted_at__gt']))
        if 'deleted_at__gte' in filters:
            query = query.filter(
                model.deleted_at >= objutils.datetime_or_str_or_none(
                    filters['deleted_at__gte']))
        if 'deleted_at__lt' in filters:
            query = query.filter(
                model.deleted_at < objutils.datetime_or_str_or_none(
                    filters['deleted_at__lt']))
        if 'deleted_at__lte' in filters:
            query = query.filter(
                model.deleted_at <= objutils.datetime_or_str_or_none(
                    filters['deleted_at__lte']))

        return query

    def __add_timestamp_mixin_filters(self, query, filters, model):
        if 'created_at__eq' in filters:
            query = query.filter(
                model.created_at == objutils.datetime_or_str_or_none(
                    filters['created_at__eq']))
        if 'created_at__gt' in filters:
            query = query.filter(
                model.created_at > objutils.datetime_or_str_or_none(
                    filters['created_at__gt']))
        if 'created_at__gte' in filters:
            query = query.filter(
                model.created_at >= objutils.datetime_or_str_or_none(
                    filters['created_at__gte']))
        if 'created_at__lt' in filters:
            query = query.filter(
                model.created_at < objutils.datetime_or_str_or_none(
                    filters['created_at__lt']))
        if 'created_at__lte' in filters:
            query = query.filter(
                model.created_at <= objutils.datetime_or_str_or_none(
                    filters['created_at__lte']))

        if 'updated_at__eq' in filters:
            query = query.filter(
                model.updated_at == objutils.datetime_or_str_or_none(
                    filters['updated_at__eq']))
        if 'updated_at__gt' in filters:
            query = query.filter(
                model.updated_at > objutils.datetime_or_str_or_none(
                    filters['updated_at__gt']))
        if 'updated_at__gte' in filters:
            query = query.filter(
                model.updated_at >= objutils.datetime_or_str_or_none(
                    filters['updated_at__gte']))
        if 'updated_at__lt' in filters:
            query = query.filter(
                model.updated_at < objutils.datetime_or_str_or_none(
                    filters['updated_at__lt']))
        if 'updated_at__lte' in filters:
            query = query.filter(
                model.updated_at <= objutils.datetime_or_str_or_none(
                    filters['updated_at__lte']))

        return query

    def __add_simple_filter(self, query, model, fieldname, value):
        return query.filter(getattr(model, fieldname) == value)

    def __add_join_filter(self, query, model, join_model, fieldname, value):
        query = query.join(join_model)
        return self.__add_simple_filter(query, join_model, fieldname, value)

    def _add_filters(self, query, model, filters=None,
                     plain_fields=None, join_fieldmap=None):
        """Generic way to add filters to a Watcher model

        :param query: a :py:class:`sqlalchemy.orm.query.Query` instance
        :param model: the model class the filters should relate to
        :param filters: dict with the following structure {"fieldname": value}
        :param plain_fields: a :py:class:`sqlalchemy.orm.query.Query` instance
        :param join_fieldmap: a :py:class:`sqlalchemy.orm.query.Query` instance

        """
        filters = filters or {}
        plain_fields = plain_fields or ()
        join_fieldmap = join_fieldmap or {}

        for fieldname, value in filters.items():
            if fieldname in plain_fields:
                query = self.__add_simple_filter(
                    query, model, fieldname, value)
            elif fieldname in join_fieldmap:
                join_field, join_model = join_fieldmap[fieldname]
                query = self.__add_join_filter(
                    query, model, join_model, join_field, value)

        query = self.__add_soft_delete_mixin_filters(query, filters, model)
        query = self.__add_timestamp_mixin_filters(query, filters, model)

        return query

    def _get(self, context, model, fieldname, value):
        query = model_query(model)
        query = query.filter(getattr(model, fieldname) == value)
        if not context.show_deleted:
            query = query.filter(model.deleted_at.is_(None))

        try:
            obj = query.one()
        except exc.NoResultFound:
            raise exception.ResourceNotFound(name=model.__name__, id=value)

        return obj

    def _update(self, model, id_, values):
        session = get_session()
        with session.begin():
            query = model_query(model, session=session)
            query = add_identity_filter(query, id_)
            try:
                ref = query.with_lockmode('update').one()
            except exc.NoResultFound:
                raise exception.ResourceNotFound(name=model.__name__, id=id_)

            ref.update(values)
        return ref

    def _soft_delete(self, model, id_):
        session = get_session()
        with session.begin():
            query = model_query(model, session=session)
            query = add_identity_filter(query, id_)
            try:
                query.one()
            except exc.NoResultFound:
                raise exception.ResourceNotFound(name=model.__name__, id=id_)

            query.soft_delete()

    def _destroy(self, model, id_):
        session = get_session()
        with session.begin():
            query = model_query(model, session=session)
            query = add_identity_filter(query, id_)

            try:
                query.one()
            except exc.NoResultFound:
                raise exception.ResourceNotFound(name=model.__name__, id=id_)

            query.delete()

    def _add_goals_filters(self, query, filters):
        if filters is None:
            filters = {}

        plain_fields = ['uuid', 'name', 'display_name']

        return self._add_filters(
            query=query, model=models.Goal, filters=filters,
            plain_fields=plain_fields)

    def _add_strategies_filters(self, query, filters):
        plain_fields = ['uuid', 'name', 'display_name', 'goal_id']
        join_fieldmap = {
            'goal_uuid': ("uuid", models.Goal),
            'goal_name': ("name", models.Goal)
        }

        return self._add_filters(
            query=query, model=models.Strategy, filters=filters,
            plain_fields=plain_fields, join_fieldmap=join_fieldmap)

    def _add_audit_templates_filters(self, query, filters):
        if filters is None:
            filters = {}

        plain_fields = ['uuid', 'name', 'host_aggregate',
                        'goal_id', 'strategy_id']
        join_fieldmap = {
            'goal_uuid': ("uuid", models.Goal),
            'goal_name': ("name", models.Goal),
            'strategy_uuid': ("uuid", models.Strategy),
            'strategy_name': ("name", models.Strategy),
        }

        return self._add_filters(
            query=query, model=models.AuditTemplate, filters=filters,
            plain_fields=plain_fields, join_fieldmap=join_fieldmap)

    def _add_audits_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'uuid' in filters:
            query = query.filter_by(uuid=filters['uuid'])
        if 'type' in filters:
            query = query.filter_by(type=filters['type'])
        if 'state' in filters:
            query = query.filter_by(state=filters['state'])
        if 'audit_template_id' in filters:
            query = query.filter_by(
                audit_template_id=filters['audit_template_id'])
        if 'audit_template_uuid' in filters:
            query = query.join(
                models.AuditTemplate,
                models.Audit.audit_template_id == models.AuditTemplate.id)
            query = query.filter(
                models.AuditTemplate.uuid == filters['audit_template_uuid'])
        if 'audit_template_name' in filters:
            query = query.join(
                models.AuditTemplate,
                models.Audit.audit_template_id == models.AuditTemplate.id)
            query = query.filter(
                models.AuditTemplate.name ==
                filters['audit_template_name'])

        query = self.__add_soft_delete_mixin_filters(
            query, filters, models.Audit)
        query = self.__add_timestamp_mixin_filters(
            query, filters, models.Audit)

        return query

    def _add_action_plans_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'uuid' in filters:
            query = query.filter_by(uuid=filters['uuid'])
        if 'state' in filters:
            query = query.filter_by(state=filters['state'])
        if 'audit_id' in filters:
            query = query.filter_by(audit_id=filters['audit_id'])
        if 'audit_uuid' in filters:
            query = query.join(models.Audit,
                               models.ActionPlan.audit_id == models.Audit.id)
            query = query.filter(models.Audit.uuid == filters['audit_uuid'])

        query = self.__add_soft_delete_mixin_filters(
            query, filters, models.ActionPlan)
        query = self.__add_timestamp_mixin_filters(
            query, filters, models.ActionPlan)

        return query

    def _add_actions_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'uuid' in filters:
            query = query.filter_by(uuid=filters['uuid'])
        if 'action_plan_id' in filters:
            query = query.filter_by(action_plan_id=filters['action_plan_id'])
        if 'action_plan_uuid' in filters:
            query = query.join(
                models.ActionPlan,
                models.Action.action_plan_id == models.ActionPlan.id)
            query = query.filter(
                models.ActionPlan.uuid == filters['action_plan_uuid'])
        if 'audit_uuid' in filters:
            stmt = model_query(models.ActionPlan).join(
                models.Audit,
                models.Audit.id == models.ActionPlan.audit_id)\
                .filter_by(uuid=filters['audit_uuid']).subquery()
            query = query.filter_by(action_plan_id=stmt.c.id)

        if 'state' in filters:
            query = query.filter_by(state=filters['state'])

        query = self.__add_soft_delete_mixin_filters(
            query, filters, models.Action)
        query = self.__add_timestamp_mixin_filters(
            query, filters, models.Action)

        return query

    # ### GOALS ### #

    def get_goal_list(self, context, filters=None, limit=None,
                      marker=None, sort_key=None, sort_dir=None):

        query = model_query(models.Goal)
        query = self._add_goals_filters(query, filters)
        if not context.show_deleted:
            query = query.filter_by(deleted_at=None)
        return _paginate_query(models.Goal, limit, marker,
                               sort_key, sort_dir, query)

    def create_goal(self, values):
        # ensure defaults are present for new goals
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        goal = models.Goal()
        goal.update(values)

        try:
            goal.save()
        except db_exc.DBDuplicateEntry:
            raise exception.GoalAlreadyExists(uuid=values['uuid'])
        return goal

    def _get_goal(self, context, fieldname, value):
        try:
            return self._get(context, model=models.Goal,
                             fieldname=fieldname, value=value)
        except exception.ResourceNotFound:
            raise exception.GoalNotFound(goal=value)

    def get_goal_by_id(self, context, goal_id):
        return self._get_goal(context, fieldname="id", value=goal_id)

    def get_goal_by_uuid(self, context, goal_uuid):
        return self._get_goal(context, fieldname="uuid", value=goal_uuid)

    def get_goal_by_name(self, context, goal_name):
        return self._get_goal(context, fieldname="name", value=goal_name)

    def destroy_goal(self, goal_id):
        try:
            return self._destroy(models.Goal, goal_id)
        except exception.ResourceNotFound:
            raise exception.GoalNotFound(goal=goal_id)

    def update_goal(self, goal_id, values):
        if 'uuid' in values:
            raise exception.Invalid(
                message=_("Cannot overwrite UUID for an existing Goal."))

        try:
            return self._update(models.Goal, goal_id, values)
        except exception.ResourceNotFound:
            raise exception.GoalNotFound(goal=goal_id)

    def soft_delete_goal(self, goal_id):
        try:
            self._soft_delete(models.Goal, goal_id)
        except exception.ResourceNotFound:
            raise exception.GoalNotFound(goal=goal_id)

    # ### STRATEGIES ### #

    def get_strategy_list(self, context, filters=None, limit=None,
                          marker=None, sort_key=None, sort_dir=None):

        query = model_query(models.Strategy)
        query = self._add_strategies_filters(query, filters)
        if not context.show_deleted:
            query = query.filter_by(deleted_at=None)
        return _paginate_query(models.Strategy, limit, marker,
                               sort_key, sort_dir, query)

    def create_strategy(self, values):
        # ensure defaults are present for new strategies
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        strategy = models.Strategy()
        strategy.update(values)

        try:
            strategy.save()
        except db_exc.DBDuplicateEntry:
            raise exception.StrategyAlreadyExists(uuid=values['uuid'])
        return strategy

    def _get_strategy(self, context, fieldname, value):
        try:
            return self._get(context, model=models.Strategy,
                             fieldname=fieldname, value=value)
        except exception.ResourceNotFound:
            raise exception.StrategyNotFound(strategy=value)

    def get_strategy_by_id(self, context, strategy_id):
        return self._get_strategy(context, fieldname="id", value=strategy_id)

    def get_strategy_by_uuid(self, context, strategy_uuid):
        return self._get_strategy(
            context, fieldname="uuid", value=strategy_uuid)

    def get_strategy_by_name(self, context, strategy_name):
        return self._get_strategy(
            context, fieldname="name", value=strategy_name)

    def destroy_strategy(self, strategy_id):
        try:
            return self._destroy(models.Strategy, strategy_id)
        except exception.ResourceNotFound:
            raise exception.StrategyNotFound(strategy=strategy_id)

    def update_strategy(self, strategy_id, values):
        if 'uuid' in values:
            raise exception.Invalid(
                message=_("Cannot overwrite UUID for an existing Strategy."))

        try:
            return self._update(models.Strategy, strategy_id, values)
        except exception.ResourceNotFound:
            raise exception.StrategyNotFound(strategy=strategy_id)

    def soft_delete_strategy(self, strategy_id):
        try:
            self._soft_delete(models.Strategy, strategy_id)
        except exception.ResourceNotFound:
            raise exception.StrategyNotFound(strategy=strategy_id)

    # ### AUDIT TEMPLATES ### #

    def get_audit_template_list(self, context, filters=None, limit=None,
                                marker=None, sort_key=None, sort_dir=None):

        query = model_query(models.AuditTemplate)
        query = self._add_audit_templates_filters(query, filters)
        if not context.show_deleted:
            query = query.filter_by(deleted_at=None)
        return _paginate_query(models.AuditTemplate, limit, marker,
                               sort_key, sort_dir, query)

    def create_audit_template(self, values):
        # ensure defaults are present for new audit_templates
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        query = model_query(models.AuditTemplate)
        query = query.filter_by(name=values.get('name'),
                                deleted_at=None)

        if len(query.all()) > 0:
            raise exception.AuditTemplateAlreadyExists(
                audit_template=values['name'])

        audit_template = models.AuditTemplate()
        audit_template.update(values)

        try:
            audit_template.save()
        except db_exc.DBDuplicateEntry:
            raise exception.AuditTemplateAlreadyExists(
                audit_template=values['name'])
        return audit_template

    def _get_audit_template(self, context, fieldname, value):
        try:
            return self._get(context, model=models.AuditTemplate,
                             fieldname=fieldname, value=value)
        except exception.ResourceNotFound:
            raise exception.AuditTemplateNotFound(audit_template=value)

    def get_audit_template_by_id(self, context, audit_template_id):
        return self._get_audit_template(
            context, fieldname="id", value=audit_template_id)

    def get_audit_template_by_uuid(self, context, audit_template_uuid):
        return self._get_audit_template(
            context, fieldname="uuid", value=audit_template_uuid)

    def get_audit_template_by_name(self, context, audit_template_name):
        return self._get_audit_template(
            context, fieldname="name", value=audit_template_name)

    def destroy_audit_template(self, audit_template_id):
        try:
            return self._destroy(models.AuditTemplate, audit_template_id)
        except exception.ResourceNotFound:
            raise exception.AuditTemplateNotFound(
                audit_template=audit_template_id)

    def update_audit_template(self, audit_template_id, values):
        if 'uuid' in values:
            raise exception.Invalid(
                message=_("Cannot overwrite UUID for an existing "
                          "Audit Template."))
        try:
            return self._update(
                models.AuditTemplate, audit_template_id, values)
        except exception.ResourceNotFound:
            raise exception.AuditTemplateNotFound(
                audit_template=audit_template_id)

    def soft_delete_audit_template(self, audit_template_id):
        try:
            self._soft_delete(models.AuditTemplate, audit_template_id)
        except exception.ResourceNotFound:
            raise exception.AuditTemplateNotFound(
                audit_template=audit_template_id)

    # ### AUDITS ### #

    def get_audit_list(self, context, filters=None, limit=None, marker=None,
                       sort_key=None, sort_dir=None):
        query = model_query(models.Audit)
        query = self._add_audits_filters(query, filters)
        if not context.show_deleted:
            query = query.filter(
                ~(models.Audit.state == audit_objects.State.DELETED))

        return _paginate_query(models.Audit, limit, marker,
                               sort_key, sort_dir, query)

    def create_audit(self, values):
        # ensure defaults are present for new audits
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        if values.get('state') is None:
            values['state'] = audit_objects.State.PENDING

        audit = models.Audit()
        audit.update(values)

        try:
            audit.save()
        except db_exc.DBDuplicateEntry:
            raise exception.AuditAlreadyExists(uuid=values['uuid'])
        return audit

    def get_audit_by_id(self, context, audit_id):
        query = model_query(models.Audit)
        query = query.filter_by(id=audit_id)
        try:
            audit = query.one()
            if not context.show_deleted:
                if audit.state == audit_objects.State.DELETED:
                    raise exception.AuditNotFound(audit=audit_id)
            return audit
        except exc.NoResultFound:
            raise exception.AuditNotFound(audit=audit_id)

    def get_audit_by_uuid(self, context, audit_uuid):
        query = model_query(models.Audit)
        query = query.filter_by(uuid=audit_uuid)

        try:
            audit = query.one()
            if not context.show_deleted:
                if audit.state == audit_objects.State.DELETED:
                    raise exception.AuditNotFound(audit=audit_uuid)
            return audit
        except exc.NoResultFound:
            raise exception.AuditNotFound(audit=audit_uuid)

    def destroy_audit(self, audit_id):
        def is_audit_referenced(session, audit_id):
            """Checks whether the audit is referenced by action_plan(s)."""
            query = model_query(models.ActionPlan, session=session)
            query = self._add_action_plans_filters(
                query, {'audit_id': audit_id})
            return query.count() != 0

        session = get_session()
        with session.begin():
            query = model_query(models.Audit, session=session)
            query = add_identity_filter(query, audit_id)

            try:
                audit_ref = query.one()
            except exc.NoResultFound:
                raise exception.AuditNotFound(audit=audit_id)

            if is_audit_referenced(session, audit_ref['id']):
                raise exception.AuditReferenced(audit=audit_id)

            query.delete()

    def update_audit(self, audit_id, values):
        if 'uuid' in values:
            raise exception.Invalid(
                message=_("Cannot overwrite UUID for an existing "
                          "Audit."))

        return self._do_update_audit(audit_id, values)

    def _do_update_audit(self, audit_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Audit, session=session)
            query = add_identity_filter(query, audit_id)
            try:
                ref = query.with_lockmode('update').one()
            except exc.NoResultFound:
                raise exception.AuditNotFound(audit=audit_id)

            ref.update(values)
        return ref

    def soft_delete_audit(self, audit_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Audit, session=session)
            query = add_identity_filter(query, audit_id)

            try:
                query.one()
            except exc.NoResultFound:
                raise exception.AuditNotFound(audit=audit_id)

            query.soft_delete()

    # ### ACTIONS ### #

    def get_action_list(self, context, filters=None, limit=None, marker=None,
                        sort_key=None, sort_dir=None):
        query = model_query(models.Action)
        query = self._add_actions_filters(query, filters)
        if not context.show_deleted:
            query = query.filter(
                ~(models.Action.state == action_objects.State.DELETED))
        return _paginate_query(models.Action, limit, marker,
                               sort_key, sort_dir, query)

    def create_action(self, values):
        # ensure defaults are present for new actions
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        action = models.Action()
        action.update(values)
        try:
            action.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ActionAlreadyExists(uuid=values['uuid'])
        return action

    def get_action_by_id(self, context, action_id):
        query = model_query(models.Action)
        query = query.filter_by(id=action_id)
        try:
            action = query.one()
            if not context.show_deleted:
                if action.state == action_objects.State.DELETED:
                    raise exception.ActionNotFound(
                        action=action_id)
            return action
        except exc.NoResultFound:
            raise exception.ActionNotFound(action=action_id)

    def get_action_by_uuid(self, context, action_uuid):
        query = model_query(models.Action)
        query = query.filter_by(uuid=action_uuid)
        try:
            action = query.one()
            if not context.show_deleted:
                if action.state == action_objects.State.DELETED:
                    raise exception.ActionNotFound(
                        action=action_uuid)
            return action
        except exc.NoResultFound:
            raise exception.ActionNotFound(action=action_uuid)

    def destroy_action(self, action_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Action, session=session)
            query = add_identity_filter(query, action_id)
            count = query.delete()
            if count != 1:
                raise exception.ActionNotFound(action_id)

    def update_action(self, action_id, values):
        # NOTE(dtantsur): this can lead to very strange errors
        if 'uuid' in values:
            raise exception.Invalid(
                message=_("Cannot overwrite UUID for an existing "
                          "Action."))

        return self._do_update_action(action_id, values)

    def _do_update_action(self, action_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Action, session=session)
            query = add_identity_filter(query, action_id)
            try:
                ref = query.with_lockmode('update').one()
            except exc.NoResultFound:
                raise exception.ActionNotFound(action=action_id)

            ref.update(values)
        return ref

    def soft_delete_action(self, action_id):
        session = get_session()
        with session.begin():
            query = model_query(models.Action, session=session)
            query = add_identity_filter(query, action_id)

            try:
                query.one()
            except exc.NoResultFound:
                raise exception.ActionNotFound(action=action_id)

            query.soft_delete()

    # ### ACTION PLANS ### #

    def get_action_plan_list(
        self, context, columns=None, filters=None, limit=None,
            marker=None, sort_key=None, sort_dir=None):
        query = model_query(models.ActionPlan)
        query = self._add_action_plans_filters(query, filters)
        if not context.show_deleted:
            query = query.filter(
                ~(models.ActionPlan.state == ap_objects.State.DELETED))

        return _paginate_query(models.ActionPlan, limit, marker,
                               sort_key, sort_dir, query)

    def create_action_plan(self, values):
        # ensure defaults are present for new audits
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        action_plan = models.ActionPlan()
        action_plan.update(values)

        try:
            action_plan.save()
        except db_exc.DBDuplicateEntry:
            raise exception.ActionPlanAlreadyExists(uuid=values['uuid'])
        return action_plan

    def get_action_plan_by_id(self, context, action_plan_id):
        query = model_query(models.ActionPlan)
        query = query.filter_by(id=action_plan_id)
        try:
            action_plan = query.one()
            if not context.show_deleted:
                if action_plan.state == ap_objects.State.DELETED:
                    raise exception.ActionPlanNotFound(
                        action_plan=action_plan_id)
            return action_plan
        except exc.NoResultFound:
            raise exception.ActionPlanNotFound(action_plan=action_plan_id)

    def get_action_plan_by_uuid(self, context, action_plan__uuid):
        query = model_query(models.ActionPlan)
        query = query.filter_by(uuid=action_plan__uuid)

        try:
            action_plan = query.one()
            if not context.show_deleted:
                if action_plan.state == ap_objects.State.DELETED:
                    raise exception.ActionPlanNotFound(
                        action_plan=action_plan__uuid)
            return action_plan
        except exc.NoResultFound:
            raise exception.ActionPlanNotFound(action_plan=action_plan__uuid)

    def destroy_action_plan(self, action_plan_id):
        def is_action_plan_referenced(session, action_plan_id):
            """Checks whether the action_plan is referenced by action(s)."""
            query = model_query(models.Action, session=session)
            query = self._add_actions_filters(
                query, {'action_plan_id': action_plan_id})
            return query.count() != 0

        session = get_session()
        with session.begin():
            query = model_query(models.ActionPlan, session=session)
            query = add_identity_filter(query, action_plan_id)

            try:
                action_plan_ref = query.one()
            except exc.NoResultFound:
                raise exception.ActionPlanNotFound(action_plan=action_plan_id)

            if is_action_plan_referenced(session, action_plan_ref['id']):
                raise exception.ActionPlanReferenced(
                    action_plan=action_plan_id)

            query.delete()

    def update_action_plan(self, action_plan_id, values):
        if 'uuid' in values:
            raise exception.Invalid(
                message=_("Cannot overwrite UUID for an existing "
                          "Action Plan."))

        return self._do_update_action_plan(action_plan_id, values)

    def _do_update_action_plan(self, action_plan_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.ActionPlan, session=session)
            query = add_identity_filter(query, action_plan_id)
            try:
                ref = query.with_lockmode('update').one()
            except exc.NoResultFound:
                raise exception.ActionPlanNotFound(action_plan=action_plan_id)

            ref.update(values)
        return ref

    def soft_delete_action_plan(self, action_plan_id):
        session = get_session()
        with session.begin():
            query = model_query(models.ActionPlan, session=session)
            query = add_identity_filter(query, action_plan_id)

            try:
                query.one()
            except exc.NoResultFound:
                raise exception.ActionPlanNotFound(action_plan=action_plan_id)

            query.soft_delete()
