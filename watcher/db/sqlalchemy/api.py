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
from sqlalchemy.orm.exc import MultipleResultsFound
from sqlalchemy.orm.exc import NoResultFound

from watcher.common import exception
from watcher.common import utils
from watcher.db import api
from watcher.db.sqlalchemy import models
from watcher.objects.audit import AuditStatus
from watcher.openstack.common._i18n import _
from watcher.openstack.common import log

CONF = cfg.CONF

LOG = log.getLogger(__name__)


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


class Connection(api.Connection):
    """SqlAlchemy connection."""

    def __init__(self):
        pass

    def _add_audit_templates_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'name' in filters:
            query = query.filter_by(name=filters['name'])
        if 'host_aggregate' in filters:
            query = query.filter_by(host_aggregate=filters['host_aggregate'])
        if 'goal' in filters:
            query = query.filter_by(goal=filters['goal'])

        return query

    def _add_audits_filters(self, query, filters):
        if filters is None:
            filters = []

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
        return query

    def _add_action_plans_filters(self, query, filters):
        if filters is None:
            filters = []

        if 'state' in filters:
            query = query.filter_by(state=filters['state'])
        if 'audit_id' in filters:
            query = query.filter_by(audit_id=filters['audit_id'])
        if 'audit_uuid' in filters:
            query = query.join(models.Audit,
                               models.ActionPlan.audit_id == models.Audit.id)
            query = query.filter(models.Audit.uuid == filters['audit_uuid'])
        return query

    def _add_actions_filters(self, query, filters):
        if filters is None:
            filters = []

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
        if 'alarm' in filters:
            query = query.filter_by(alarm=filters['alarm'])

        return query

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

        audit_template = models.AuditTemplate()
        audit_template.update(values)

        try:
            audit_template.save()
        except db_exc.DBDuplicateEntry:
            raise exception.AuditTemplateAlreadyExists(uuid=values['uuid'],
                                                       name=values['name'])
        return audit_template

    def get_audit_template_by_id(self, context, audit_template_id):
        query = model_query(models.AuditTemplate)
        query = query.filter_by(id=audit_template_id)
        try:
            audit_template = query.one()
            if not context.show_deleted:
                if audit_template.deleted_at is not None:
                    raise exception.AuditTemplateNotFound(
                        audit_template=audit_template_id)
            return audit_template
        except NoResultFound:
            raise exception.AuditTemplateNotFound(
                audit_template=audit_template_id)

    def get_audit_template_by_uuid(self, context, audit_template_uuid):
        query = model_query(models.AuditTemplate)
        query = query.filter_by(uuid=audit_template_uuid)

        try:
            audit_template = query.one()
            if not context.show_deleted:
                if audit_template.deleted_at is not None:
                    raise exception.AuditTemplateNotFound(
                        audit_template=audit_template_uuid)
            return audit_template
        except NoResultFound:
            raise exception.AuditTemplateNotFound(
                audit_template=audit_template_uuid)

    def get_audit_template_by_name(self, context, audit_template_name):
        query = model_query(models.AuditTemplate)
        query = query.filter_by(name=audit_template_name)
        try:
            audit_template = query.one()
            if not context.show_deleted:
                if audit_template.deleted_at is not None:
                    raise exception.AuditTemplateNotFound(
                        audit_template=audit_template_name)
            return audit_template
        except MultipleResultsFound:
            raise exception.Conflict(
                'Multiple audit templates exist with same name.'
                ' Please use the audit template uuid instead.')
        except NoResultFound:
            raise exception.AuditTemplateNotFound(
                audit_template=audit_template_name)

    def destroy_audit_template(self, audit_template_id):
        session = get_session()
        with session.begin():
            query = model_query(models.AuditTemplate, session=session)
            query = add_identity_filter(query, audit_template_id)

            try:
                query.one()
            except NoResultFound:
                raise exception.AuditTemplateNotFound(node=audit_template_id)

            query.delete()

    def update_audit_template(self, audit_template_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing AuditTemplate.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_audit_template(audit_template_id, values)

    def _do_update_audit_template(self, audit_template_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.AuditTemplate, session=session)
            query = add_identity_filter(query, audit_template_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
                raise exception.AuditTemplateNotFound(
                    audit_template=audit_template_id)

            ref.update(values)
        return ref

    def soft_delete_audit_template(self, audit_template_id):
        session = get_session()
        with session.begin():
            query = model_query(models.AuditTemplate, session=session)
            query = add_identity_filter(query, audit_template_id)

            try:
                query.one()
            except NoResultFound:
                raise exception.AuditTemplateNotFound(node=audit_template_id)

            query.soft_delete()

    def get_audit_list(self, context, filters=None, limit=None, marker=None,
                       sort_key=None, sort_dir=None):
        query = model_query(models.Audit)
        query = self._add_audits_filters(query, filters)
        if not context.show_deleted:
            query = query.filter(~(models.Audit.state == 'DELETED'))

        return _paginate_query(models.Audit, limit, marker,
                               sort_key, sort_dir, query)

    def create_audit(self, values):
        # ensure defaults are present for new audits
        if not values.get('uuid'):
            values['uuid'] = utils.generate_uuid()

        if values.get('state') is None:
            values['state'] = AuditStatus.PENDING

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
                if audit.state == 'DELETED':
                    raise exception.AuditNotFound(audit=audit_id)
            return audit
        except NoResultFound:
            raise exception.AuditNotFound(audit=audit_id)

    def get_audit_by_uuid(self, context, audit_uuid):
        query = model_query(models.Audit)
        query = query.filter_by(uuid=audit_uuid)

        try:
            audit = query.one()
            if not context.show_deleted:
                if audit.state == 'DELETED':
                    raise exception.AuditNotFound(audit=audit_uuid)
            return audit
        except NoResultFound:
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
            except NoResultFound:
                raise exception.AuditNotFound(audit=audit_id)

            if is_audit_referenced(session, audit_ref['id']):
                raise exception.AuditReferenced(audit=audit_id)

            query.delete()

    def update_audit(self, audit_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Audit.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_audit(audit_id, values)

    def _do_update_audit(self, audit_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Audit, session=session)
            query = add_identity_filter(query, audit_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
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
            except NoResultFound:
                raise exception.AuditNotFound(node=audit_id)

            query.soft_delete()

    def get_action_list(self, context, filters=None, limit=None, marker=None,
                        sort_key=None, sort_dir=None):
        query = model_query(models.Action)
        query = self._add_actions_filters(query, filters)
        if not context.show_deleted:
            query = query.filter(~(models.Action.state == 'DELETED'))
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
                if action.state == 'DELETED':
                    raise exception.ActionNotFound(
                        action=action_id)
            return action
        except NoResultFound:
            raise exception.ActionNotFound(action=action_id)

    def get_action_by_uuid(self, context, action_uuid):
        query = model_query(models.Action)
        query = query.filter_by(uuid=action_uuid)
        try:
            action = query.one()
            if not context.show_deleted:
                if action.state == 'DELETED':
                    raise exception.ActionNotFound(
                        action=action_uuid)
            return action
        except NoResultFound:
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
            msg = _("Cannot overwrite UUID for an existing Action.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_action(action_id, values)

    def _do_update_action(self, action_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.Action, session=session)
            query = add_identity_filter(query, action_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
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
            except NoResultFound:
                raise exception.ActionNotFound(node=action_id)

            query.soft_delete()

    def get_action_plan_list(
        self, context, columns=None, filters=None, limit=None,
            marker=None, sort_key=None, sort_dir=None):
        query = model_query(models.ActionPlan)
        query = self._add_action_plans_filters(query, filters)
        if not context.show_deleted:
            query = query.filter(~(models.ActionPlan.state == 'DELETED'))

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
                if action_plan.state == 'DELETED':
                    raise exception.ActionPlanNotFound(
                        action_plan=action_plan_id)
            return action_plan
        except NoResultFound:
            raise exception.ActionPlanNotFound(action_plan=action_plan_id)

    def get_action_plan_by_uuid(self, context, action_plan__uuid):
        query = model_query(models.ActionPlan)
        query = query.filter_by(uuid=action_plan__uuid)

        try:
            action_plan = query.one()
            if not context.show_deleted:
                if action_plan.state == 'DELETED':
                    raise exception.ActionPlanNotFound(
                        action_plan=action_plan__uuid)
            return action_plan
        except NoResultFound:
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
            except NoResultFound:
                raise exception.ActionPlanNotFound(action_plan=action_plan_id)

            if is_action_plan_referenced(session, action_plan_ref['id']):
                raise exception.ActionPlanReferenced(
                    action_plan=action_plan_id)

            query.delete()

    def update_action_plan(self, action_plan_id, values):
        if 'uuid' in values:
            msg = _("Cannot overwrite UUID for an existing Audit.")
            raise exception.InvalidParameterValue(err=msg)

        return self._do_update_action_plan(action_plan_id, values)

    def _do_update_action_plan(self, action_plan_id, values):
        session = get_session()
        with session.begin():
            query = model_query(models.ActionPlan, session=session)
            query = add_identity_filter(query, action_plan_id)
            try:
                ref = query.with_lockmode('update').one()
            except NoResultFound:
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
            except NoResultFound:
                raise exception.ActionPlanNotFound(node=action_plan_id)

            query.soft_delete()
