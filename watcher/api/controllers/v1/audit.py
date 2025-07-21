# -*- encoding: utf-8 -*-
# Copyright 2013 Red Hat, Inc.
# All Rights Reserved.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""
In the Watcher system, an :ref:`Audit <audit_definition>` is a request for
optimizing a :ref:`Cluster <cluster_definition>`.

The optimization is done in order to satisfy one :ref:`Goal <goal_definition>`
on a given :ref:`Cluster <cluster_definition>`.

For each :ref:`Audit <audit_definition>`, the Watcher system generates an
:ref:`Action Plan <action_plan_definition>`.

To see the life-cycle and description of an :ref:`Audit <audit_definition>`
states, visit :ref:`the Audit State machine <audit_state_machine>`.
"""

import datetime
from dateutil import tz

from http import HTTPStatus
import jsonschema
from oslo_log import log
from oslo_utils import timeutils
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes
from wsme import utils as wutils
import wsmeext.pecan as wsme_pecan

from watcher._i18n import _
from watcher.api.controllers import base
from watcher.api.controllers import link
from watcher.api.controllers.v1 import collection
from watcher.api.controllers.v1 import types
from watcher.api.controllers.v1 import utils as api_utils
from watcher.common import exception
from watcher.common import policy
from watcher.common import utils
from watcher.decision_engine import rpcapi
from watcher import objects

LOG = log.getLogger(__name__)


def _get_object_by_value(context, class_name, value):
    if utils.is_uuid_like(value) or utils.is_int_like(value):
        return class_name.get(context, value)
    else:
        return class_name.get_by_name(context, value)


def hide_fields_in_newer_versions(obj):
    """This method hides fields that were added in newer API versions.

    Certain node fields were introduced at certain API versions.
    These fields are only made available when the request's API version
    matches or exceeds the versions when these fields were introduced.
    """
    if not api_utils.allow_start_end_audit_time():
        obj.start_time = wtypes.Unset
        obj.end_time = wtypes.Unset
    if not api_utils.allow_force():
        obj.force = wtypes.Unset


class AuditPostType(wtypes.Base):

    name = wtypes.wsattr(wtypes.text, mandatory=False)

    audit_template_uuid = wtypes.wsattr(types.uuid, mandatory=False)

    goal = wtypes.wsattr(wtypes.text, mandatory=False)

    strategy = wtypes.wsattr(wtypes.text, mandatory=False)

    audit_type = wtypes.wsattr(wtypes.text, mandatory=True)

    state = wtypes.wsattr(wtypes.text, readonly=True,
                          default=objects.audit.State.PENDING)

    parameters = wtypes.wsattr({wtypes.text: types.jsontype}, mandatory=False,
                               default={})
    interval = wtypes.wsattr(types.interval_or_cron, mandatory=False)

    scope = wtypes.wsattr(types.jsontype, readonly=True)

    auto_trigger = wtypes.wsattr(bool, mandatory=False)

    hostname = wtypes.wsattr(wtypes.text, readonly=True, mandatory=False)

    start_time = wtypes.wsattr(datetime.datetime, mandatory=False)

    end_time = wtypes.wsattr(datetime.datetime, mandatory=False)

    force = wtypes.wsattr(bool, mandatory=False)

    def as_audit(self, context):
        audit_type_values = [val.value for val in objects.audit.AuditType]
        if self.audit_type not in audit_type_values:
            raise exception.AuditTypeNotFound(audit_type=self.audit_type)

        if not self.audit_template_uuid and not self.goal:
            message = _(
                'A valid goal or audit_template_id must be provided')
            raise exception.Invalid(message)

        if (self.audit_type == objects.audit.AuditType.ONESHOT.value and
                self.interval not in (wtypes.Unset, None)):
            raise exception.AuditIntervalNotAllowed(audit_type=self.audit_type)

        if (self.audit_type == objects.audit.AuditType.CONTINUOUS.value and
                self.interval in (wtypes.Unset, None)):
            raise exception.AuditIntervalNotSpecified(
                audit_type=self.audit_type)

        if self.audit_template_uuid and self.goal:
            raise exception.Invalid('Either audit_template_uuid '
                                    'or goal should be provided.')

        if (self.audit_type == objects.audit.AuditType.ONESHOT.value and
                (self.start_time not in (wtypes.Unset, None) or
                    self.end_time not in (wtypes.Unset, None))):
            raise exception.AuditStartEndTimeNotAllowed(
                audit_type=self.audit_type)

        if not api_utils.allow_start_end_audit_time():
            for field in ('start_time', 'end_time'):
                if getattr(self, field) not in (wtypes.Unset, None):
                    raise exception.NotAcceptable()

        # If audit_template_uuid was provided, we will provide any
        # variables not included in the request, but not override
        # those variables that were included.
        if self.audit_template_uuid:
            try:
                audit_template = objects.AuditTemplate.get(
                    context, self.audit_template_uuid)
            except exception.AuditTemplateNotFound:
                raise exception.Invalid(
                    message=_('The audit template UUID or name specified is '
                              'invalid'))
            at2a = {
                'goal': 'goal_id',
                'strategy': 'strategy_id',
                'scope': 'scope',
            }
            to_string_fields = set(['goal', 'strategy'])
            for k in at2a:
                if not getattr(self, k):
                    try:
                        at_attr = getattr(audit_template, at2a[k])
                        if at_attr and (k in to_string_fields):
                            at_attr = str(at_attr)
                        setattr(self, k, at_attr)
                    except AttributeError:
                        pass

        # Note: If audit name was not provided, used a default name
        if not self.name:
            if self.strategy:
                strategy = _get_object_by_value(context, objects.Strategy,
                                                self.strategy)
                self.name = "%s-%s" % (strategy.name,
                                       timeutils.utcnow().isoformat())
            elif self.audit_template_uuid:
                audit_template = objects.AuditTemplate.get(
                    context, self.audit_template_uuid)
                self.name = "%s-%s" % (audit_template.name,
                                       timeutils.utcnow().isoformat())
            else:
                goal = _get_object_by_value(context, objects.Goal, self.goal)
                self.name = "%s-%s" % (goal.name,
                                       timeutils.utcnow().isoformat())
        # No more than 63 characters
        if len(self.name) > 63:
            LOG.warning("Audit: %s length exceeds 63 characters",
                        self.name)
            self.name = self.name[0:63]

        return Audit(
            name=self.name,
            audit_type=self.audit_type,
            parameters=self.parameters,
            goal_id=self.goal,
            strategy_id=self.strategy,
            interval=self.interval,
            scope=self.scope,
            auto_trigger=self.auto_trigger,
            start_time=self.start_time,
            end_time=self.end_time,
            force=self.force)


class AuditPatchType(types.JsonPatchType):

    @staticmethod
    def mandatory_attrs():
        return ['/audit_template_uuid', '/type']

    @staticmethod
    def validate(patch):

        def is_new_state_none(p):
            return p.path == '/state' and p.op == 'replace' and p.value is None

        serialized_patch = {'path': patch.path,
                            'op': patch.op,
                            'value': patch.value}
        if (patch.path in AuditPatchType.mandatory_attrs() or
                is_new_state_none(patch)):
            msg = _("%(field)s can't be updated.")
            raise exception.PatchError(
                patch=serialized_patch,
                reason=msg % dict(field=patch.path))
        return types.JsonPatchType.validate(patch)


class Audit(base.APIBase):
    """API representation of an audit.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of an audit.
    """
    _goal_uuid = None
    _goal_name = None
    _strategy_uuid = None
    _strategy_name = None

    def _get_goal(self, value):
        if value == wtypes.Unset:
            return None
        goal = None
        try:
            if utils.is_uuid_like(value) or utils.is_int_like(value):
                goal = objects.Goal.get(
                    pecan.request.context, value)
            else:
                goal = objects.Goal.get_by_name(
                    pecan.request.context, value)
        except exception.GoalNotFound:
            pass
        if goal:
            self.goal_id = goal.id
        return goal

    def _get_goal_uuid(self):
        return self._goal_uuid

    def _set_goal_uuid(self, value):
        if value and self._goal_uuid != value:
            self._goal_uuid = None
            goal = self._get_goal(value)
            if goal:
                self._goal_uuid = goal.uuid

    def _get_goal_name(self):
        return self._goal_name

    def _set_goal_name(self, value):
        if value and self._goal_name != value:
            self._goal_name = None
            goal = self._get_goal(value)
            if goal:
                self._goal_name = goal.name

    def _get_strategy(self, value):
        if value == wtypes.Unset:
            return None
        strategy = None
        try:
            if utils.is_uuid_like(value) or utils.is_int_like(value):
                strategy = objects.Strategy.get(
                    pecan.request.context, value)
            else:
                strategy = objects.Strategy.get_by_name(
                    pecan.request.context, value)
        except exception.StrategyNotFound:
            pass
        if strategy:
            self.strategy_id = strategy.id
        return strategy

    def _get_strategy_uuid(self):
        return self._strategy_uuid

    def _set_strategy_uuid(self, value):
        if value and self._strategy_uuid != value:
            self._strategy_uuid = None
            strategy = self._get_strategy(value)
            if strategy:
                self._strategy_uuid = strategy.uuid

    def _get_strategy_name(self):
        return self._strategy_name

    def _set_strategy_name(self, value):
        if value and self._strategy_name != value:
            self._strategy_name = None
            strategy = self._get_strategy(value)
            if strategy:
                self._strategy_name = strategy.name

    uuid = types.uuid
    """Unique UUID for this audit"""

    name = wtypes.text
    """Name of this audit"""

    audit_type = wtypes.text
    """Type of this audit"""

    state = wtypes.text
    """This audit state"""

    goal_uuid = wtypes.wsproperty(
        wtypes.text, _get_goal_uuid, _set_goal_uuid, mandatory=True)
    """Goal UUID the audit refers to"""

    goal_name = wtypes.wsproperty(
        wtypes.text, _get_goal_name, _set_goal_name, mandatory=False)
    """The name of the goal this audit refers to"""

    strategy_uuid = wtypes.wsproperty(
        wtypes.text, _get_strategy_uuid, _set_strategy_uuid, mandatory=False)
    """Strategy UUID the audit refers to"""

    strategy_name = wtypes.wsproperty(
        wtypes.text, _get_strategy_name, _set_strategy_name, mandatory=False)
    """The name of the strategy this audit refers to"""

    parameters = {wtypes.text: types.jsontype}
    """The strategy parameters for this audit"""

    links = wtypes.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated audit links"""

    interval = wtypes.wsattr(wtypes.text, mandatory=False)
    """Launch audit periodically (in seconds)"""

    scope = wtypes.wsattr(types.jsontype, mandatory=False)
    """Audit Scope"""

    auto_trigger = wtypes.wsattr(bool, mandatory=False, default=False)
    """Autoexecute action plan once audit is succeeded"""

    next_run_time = wtypes.wsattr(datetime.datetime, mandatory=False)
    """The next time audit launch"""

    hostname = wtypes.wsattr(wtypes.text, mandatory=False)
    """Hostname the audit is running on"""

    start_time = wtypes.wsattr(datetime.datetime, mandatory=False)
    """The start time for continuous audit launch"""

    end_time = wtypes.wsattr(datetime.datetime, mandatory=False)
    """The end time that stopping continuous audit"""

    force = wsme.wsattr(bool, mandatory=False, default=False)
    """Allow Action Plan of this Audit be executed in parallel
       with other Action Plan"""

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Audit.fields)
        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))

        self.fields.append('goal_id')
        self.fields.append('strategy_id')
        fields.append('goal_uuid')
        setattr(self, 'goal_uuid', kwargs.get('goal_id',
                wtypes.Unset))
        fields.append('goal_name')
        setattr(self, 'goal_name', kwargs.get('goal_id',
                wtypes.Unset))
        fields.append('strategy_uuid')
        setattr(self, 'strategy_uuid', kwargs.get('strategy_id',
                wtypes.Unset))
        fields.append('strategy_name')
        setattr(self, 'strategy_name', kwargs.get('strategy_id',
                wtypes.Unset))

    @staticmethod
    def _convert_with_links(audit, url, expand=True):
        if not expand:
            audit.unset_fields_except(['uuid', 'name', 'audit_type', 'state',
                                       'goal_uuid', 'interval', 'scope',
                                       'strategy_uuid', 'goal_name',
                                       'strategy_name', 'auto_trigger',
                                       'next_run_time'])

        audit.links = [link.Link.make_link('self', url,
                                           'audits', audit.uuid),
                       link.Link.make_link('bookmark', url,
                                           'audits', audit.uuid,
                                           bookmark=True)
                       ]

        return audit

    @classmethod
    def convert_with_links(cls, rpc_audit, expand=True):
        audit = Audit(**rpc_audit.as_dict())
        hide_fields_in_newer_versions(audit)
        return cls._convert_with_links(audit, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     name='My Audit',
                     audit_type='ONESHOT',
                     state='PENDING',
                     created_at=timeutils.utcnow(),
                     deleted_at=None,
                     updated_at=timeutils.utcnow(),
                     interval='7200',
                     scope=[],
                     auto_trigger=False,
                     next_run_time=timeutils.utcnow(),
                     start_time=timeutils.utcnow(),
                     end_time=timeutils.utcnow())

        sample.goal_id = '7ae81bb3-dec3-4289-8d6c-da80bd8001ae'
        sample.strategy_id = '7ae81bb3-dec3-4289-8d6c-da80bd8001ff'

        return cls._convert_with_links(sample, 'http://localhost:9322', expand)


class AuditCollection(collection.Collection):
    """API representation of a collection of audits."""

    audits = [Audit]
    """A list containing audits objects"""

    def __init__(self, **kwargs):
        super(AuditCollection, self).__init__()
        self._type = 'audits'

    @staticmethod
    def convert_with_links(rpc_audits, limit, url=None, expand=False,
                           **kwargs):
        collection = AuditCollection()
        collection.audits = [Audit.convert_with_links(p, expand)
                             for p in rpc_audits]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.audits = [Audit.sample(expand=False)]
        return sample


class AuditsController(rest.RestController):
    """REST controller for Audits."""

    def __init__(self):
        super(AuditsController, self).__init__()
        self.dc_client = rpcapi.DecisionEngineAPI()

    from_audits = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource Audits."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_audits_collection(self, marker, limit,
                               sort_key, sort_dir, expand=False,
                               resource_url=None, goal=None,
                               strategy=None):
        additional_fields = ["goal_uuid", "goal_name", "strategy_uuid",
                             "strategy_name"]

        api_utils.validate_sort_key(
            sort_key, list(objects.Audit.fields) + additional_fields)
        limit = api_utils.validate_limit(limit)
        api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Audit.get_by_uuid(pecan.request.context,
                                                   marker)

        filters = {}
        if goal:
            if utils.is_uuid_like(goal):
                filters['goal_uuid'] = goal
            else:
                # TODO(michaelgugino): add method to get goal by name.
                filters['goal_name'] = goal

        if strategy:
            if utils.is_uuid_like(strategy):
                filters['strategy_uuid'] = strategy
            else:
                # TODO(michaelgugino): add method to get goal by name.
                filters['strategy_name'] = strategy

        need_api_sort = api_utils.check_need_api_sort(sort_key,
                                                      additional_fields)
        sort_db_key = (sort_key if not need_api_sort
                       else None)

        audits = objects.Audit.list(pecan.request.context,
                                    limit,
                                    marker_obj, sort_key=sort_db_key,
                                    sort_dir=sort_dir, filters=filters)

        audits_collection = AuditCollection.convert_with_links(
            audits, limit, url=resource_url, expand=expand,
            sort_key=sort_key, sort_dir=sort_dir)

        if need_api_sort:
            api_utils.make_api_sort(audits_collection.audits, sort_key,
                                    sort_dir)

        return audits_collection

    @wsme_pecan.wsexpose(AuditCollection, types.uuid, int, wtypes.text,
                         wtypes.text, wtypes.text, wtypes.text)
    def get_all(self, marker=None, limit=None, sort_key='id', sort_dir='asc',
                goal=None, strategy=None):
        """Retrieve a list of audits.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param goal: goal UUID or name to filter by
        :param strategy: strategy UUID or name to filter by
        """

        context = pecan.request.context
        policy.enforce(context, 'audit:get_all',
                       action='audit:get_all')

        return self._get_audits_collection(marker, limit, sort_key,
                                           sort_dir, goal=goal,
                                           strategy=strategy)

    @wsme_pecan.wsexpose(AuditCollection, wtypes.text, types.uuid, int,
                         wtypes.text, wtypes.text)
    def detail(self, goal=None, marker=None, limit=None,
               sort_key='id', sort_dir='asc'):
        """Retrieve a list of audits with detail.

        :param goal: goal UUID or name to filter by
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        context = pecan.request.context
        policy.enforce(context, 'audit:detail',
                       action='audit:detail')
        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "audits":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['audits', 'detail'])
        return self._get_audits_collection(marker, limit,
                                           sort_key, sort_dir, expand,
                                           resource_url,
                                           goal=goal)

    @wsme_pecan.wsexpose(Audit, wtypes.text)
    def get_one(self, audit):
        """Retrieve information about the given audit.

        :param audit: UUID or name of an audit.
        """
        if self.from_audits:
            raise exception.OperationNotPermitted

        context = pecan.request.context
        rpc_audit = api_utils.get_resource('Audit', audit)
        policy.enforce(context, 'audit:get', rpc_audit, action='audit:get')

        return Audit.convert_with_links(rpc_audit)

    @wsme_pecan.wsexpose(Audit, body=AuditPostType,
                         status_code=HTTPStatus.CREATED)
    def post(self, audit_p):
        """Create a new audit.

        :param audit_p: an audit within the request body.
        """
        context = pecan.request.context
        policy.enforce(context, 'audit:create',
                       action='audit:create')
        audit = audit_p.as_audit(context)

        if self.from_audits:
            raise exception.OperationNotPermitted

        strategy_uuid = audit.strategy_uuid
        no_schema = True
        if strategy_uuid is not None:
            # validate parameter when predefined strategy in audit template
            strategy = objects.Strategy.get(pecan.request.context,
                                            strategy_uuid)
            schema = strategy.parameters_spec
            if schema:
                # validate input parameter with default value feedback
                no_schema = False
                try:
                    utils.StrictDefaultValidatingDraft4Validator(
                        schema).validate(audit.parameters)
                except jsonschema.exceptions.ValidationError as e:
                    raise exception.Invalid(
                        _('Invalid parameters for strategy: %s') % e)

        if no_schema and audit.parameters:
            raise exception.Invalid(_('Specify parameters but no predefined '
                                      'strategy for audit, or no '
                                      'parameter spec in predefined strategy'))

        audit_dict = audit.as_dict()
        # convert local time to UTC time
        start_time_value = audit_dict.get('start_time')
        end_time_value = audit_dict.get('end_time')
        if start_time_value:
            audit_dict['start_time'] = start_time_value.replace(
                tzinfo=tz.tzlocal()).astimezone(
                    tz.tzutc()).replace(tzinfo=None)
        if end_time_value:
            audit_dict['end_time'] = end_time_value.replace(
                tzinfo=tz.tzlocal()).astimezone(
                    tz.tzutc()).replace(tzinfo=None)

        new_audit = objects.Audit(context, **audit_dict)
        new_audit.create()

        # Set the HTTP Location Header
        pecan.response.location = link.build_url('audits', new_audit.uuid)

        # trigger decision-engine to run the audit
        if new_audit.audit_type == objects.audit.AuditType.ONESHOT.value:
            self.dc_client.trigger_audit(context, new_audit.uuid)

        return Audit.convert_with_links(new_audit)

    @wsme.validate(types.uuid, [AuditPatchType])
    @wsme_pecan.wsexpose(Audit, wtypes.text, body=[AuditPatchType])
    def patch(self, audit, patch):
        """Update an existing audit.

        :param audit: UUID or name of an audit.
        :param patch: a json PATCH document to apply to this audit.
        """
        if self.from_audits:
            raise exception.OperationNotPermitted

        context = pecan.request.context
        audit_to_update = api_utils.get_resource(
            'Audit', audit, eager=True)
        policy.enforce(context, 'audit:update', audit_to_update,
                       action='audit:update')

        try:
            audit_dict = audit_to_update.as_dict()

            initial_state = audit_dict['state']
            new_state = api_utils.get_patch_value(patch, 'state')
            if not api_utils.check_audit_state_transition(
                    patch, initial_state):
                error_message = _("State transition not allowed: "
                                  "(%(initial_state)s -> %(new_state)s)")
                raise exception.PatchError(
                    patch=patch,
                    reason=error_message % dict(
                        initial_state=initial_state, new_state=new_state))

            patch_path = api_utils.get_patch_key(patch, 'path')
            if patch_path in ('start_time', 'end_time'):
                patch_value = api_utils.get_patch_value(patch, patch_path)
                # convert string format to UTC time
                new_patch_value = wutils.parse_isodatetime(
                    patch_value).replace(
                        tzinfo=tz.tzlocal()).astimezone(
                            tz.tzutc()).replace(tzinfo=None)
                api_utils.set_patch_value(patch, patch_path, new_patch_value)

            audit = Audit(**api_utils.apply_jsonpatch(audit_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Audit.fields:
            try:
                patch_val = getattr(audit, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if audit_to_update[field] != patch_val:
                audit_to_update[field] = patch_val

        audit_to_update.save()
        return Audit.convert_with_links(audit_to_update)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=HTTPStatus.NO_CONTENT)
    def delete(self, audit):
        """Delete an audit.

        :param audit: UUID or name of an audit.
        """
        context = pecan.request.context
        audit_to_delete = api_utils.get_resource(
            'Audit', audit, eager=True)
        policy.enforce(context, 'audit:delete', audit_to_delete,
                       action='audit:delete')

        initial_state = audit_to_delete.state
        new_state = objects.audit.State.DELETED
        if not objects.audit.AuditStateTransitionManager(
                ).check_transition(initial_state, new_state):
            raise exception.DeleteError(
                state=initial_state)

        audit_to_delete.soft_delete()
