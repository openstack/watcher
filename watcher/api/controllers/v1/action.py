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
An :ref:`Action <action_definition>` is what enables Watcher to transform the
current state of a :ref:`Cluster <cluster_definition>` after an
:ref:`Audit <audit_definition>`.

An :ref:`Action <action_definition>` is an atomic task which changes the
current state of a target :ref:`Managed resource <managed_resource_definition>`
of the OpenStack :ref:`Cluster <cluster_definition>` such as:

-  Live migration of an instance from one compute node to another compute
   node with Nova
-  Changing the power level of a compute node (ACPI level, ...)
-  Changing the current state of a compute node (enable or disable) with Nova

In most cases, an :ref:`Action <action_definition>` triggers some concrete
commands on an existing OpenStack module (Nova, Neutron, Cinder, Ironic, etc.).

An :ref:`Action <action_definition>` has a life-cycle and its current state may
be one of the following:

-  **PENDING** : the :ref:`Action <action_definition>` has not been executed
   yet by the :ref:`Watcher Applier <watcher_applier_definition>`
-  **ONGOING** : the :ref:`Action <action_definition>` is currently being
   processed by the :ref:`Watcher Applier <watcher_applier_definition>`
-  **SUCCEEDED** : the :ref:`Action <action_definition>` has been executed
   successfully
-  **FAILED** : an error occurred while trying to execute the
   :ref:`Action <action_definition>`
-  **DELETED** : the :ref:`Action <action_definition>` is still stored in the
   :ref:`Watcher database <watcher_database_definition>` but is not returned
   any more through the Watcher APIs.
-  **CANCELLED** : the :ref:`Action <action_definition>` was in **PENDING** or
   **ONGOING** state and was cancelled by the
   :ref:`Administrator <administrator_definition>`

:ref:`Some default implementations are provided <watcher_planners>`, but it is
possible to :ref:`develop new implementations <implement_action_plugin>` which
are dynamically loaded by Watcher at launch time.
"""

from http import HTTPStatus
from oslo_utils import timeutils
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from watcher._i18n import _
from watcher.api.controllers import base
from watcher.api.controllers import link
from watcher.api.controllers.v1 import collection
from watcher.api.controllers.v1 import types
from watcher.api.controllers.v1 import utils as api_utils
from watcher.common import exception
from watcher.common import policy
from watcher import objects


def hide_fields_in_newer_versions(obj):
    """This method hides fields that were added in newer API versions.

    Certain node fields were introduced at certain API versions.
    These fields are only made available when the request's API version
    matches or exceeds the versions when these fields were introduced.
    """
    pass


class ActionPatchType(types.JsonPatchType):

    @staticmethod
    def mandatory_attrs():
        return []


class Action(base.APIBase):
    """API representation of a action.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a action.
    """
    _action_plan_uuid = None

    def _get_action_plan_uuid(self):
        return self._action_plan_uuid

    def _set_action_plan_uuid(self, value):
        if value == wtypes.Unset:
            self._action_plan_uuid = wtypes.Unset
        elif value and self._action_plan_uuid != value:
            try:
                action_plan = objects.ActionPlan.get(
                    pecan.request.context, value)
                self._action_plan_uuid = action_plan.uuid
                self.action_plan_id = action_plan.id
            except exception.ActionPlanNotFound:
                self._action_plan_uuid = None

    uuid = wtypes.wsattr(types.uuid, readonly=True)
    """Unique UUID for this action"""

    action_plan_uuid = wtypes.wsproperty(types.uuid, _get_action_plan_uuid,
                                         _set_action_plan_uuid,
                                         mandatory=True)
    """The action plan this action belongs to """

    state = wtypes.text
    """This audit state"""

    action_type = wtypes.text
    """Action type"""

    description = wtypes.text
    """Action description"""

    input_parameters = types.jsontype
    """One or more key/value pairs """

    parents = wtypes.wsattr(types.jsontype, readonly=True)
    """UUIDs of parent actions"""

    links = wtypes.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated action links"""

    def __init__(self, **kwargs):
        super(Action, self).__init__()

        self.fields = []
        fields = list(objects.Action.fields)
        fields.append('action_plan_uuid')
        for field in fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

        self.fields.append('action_plan_id')
        self.fields.append('description')
        setattr(self, 'action_plan_uuid', kwargs.get('action_plan_id',
                wtypes.Unset))

    @staticmethod
    def _convert_with_links(action, url, expand=True):
        if not expand:
            action.unset_fields_except(['uuid', 'state', 'action_plan_uuid',
                                        'action_plan_id', 'action_type',
                                        'parents'])

        action.links = [link.Link.make_link('self', url,
                                            'actions', action.uuid),
                        link.Link.make_link('bookmark', url,
                                            'actions', action.uuid,
                                            bookmark=True)
                        ]
        return action

    @classmethod
    def convert_with_links(cls, action, expand=True):
        action = Action(**action.as_dict())
        try:
            obj_action_desc = objects.ActionDescription.get_by_type(
                pecan.request.context, action.action_type)
            description = obj_action_desc.description
        except exception.ActionDescriptionNotFound:
            description = ""
        setattr(action, 'description', description)

        hide_fields_in_newer_versions(action)

        return cls._convert_with_links(action, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     description='action description',
                     state='PENDING',
                     created_at=timeutils.utcnow(),
                     deleted_at=None,
                     updated_at=timeutils.utcnow(),
                     parents=[])
        sample._action_plan_uuid = '7ae81bb3-dec3-4289-8d6c-da80bd8001ae'
        return cls._convert_with_links(sample, 'http://localhost:9322', expand)


class ActionCollection(collection.Collection):
    """API representation of a collection of actions."""

    actions = [Action]
    """A list containing actions objects"""

    def __init__(self, **kwargs):
        self._type = 'actions'

    @staticmethod
    def convert_with_links(actions, limit, url=None, expand=False,
                           **kwargs):

        collection = ActionCollection()
        collection.actions = [Action.convert_with_links(p, expand)
                              for p in actions]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.actions = [Action.sample(expand=False)]
        return sample


class ActionsController(rest.RestController):
    """REST controller for Actions."""

    def __init__(self):
        super(ActionsController, self).__init__()

    from_actions = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource Actions."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_actions_collection(self, marker, limit,
                                sort_key, sort_dir, expand=False,
                                resource_url=None,
                                action_plan_uuid=None, audit_uuid=None):
        additional_fields = ['action_plan_uuid']

        api_utils.validate_sort_key(sort_key, list(objects.Action.fields) +
                                    additional_fields)
        limit = api_utils.validate_limit(limit)
        api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Action.get_by_uuid(pecan.request.context,
                                                    marker)

        filters = {}
        if action_plan_uuid:
            filters['action_plan_uuid'] = action_plan_uuid

        if audit_uuid:
            filters['audit_uuid'] = audit_uuid

        need_api_sort = api_utils.check_need_api_sort(sort_key,
                                                      additional_fields)
        sort_db_key = (sort_key if not need_api_sort
                       else None)

        actions = objects.Action.list(pecan.request.context,
                                      limit,
                                      marker_obj, sort_key=sort_db_key,
                                      sort_dir=sort_dir,
                                      filters=filters)

        actions_collection = ActionCollection.convert_with_links(
            actions, limit, url=resource_url, expand=expand,
            sort_key=sort_key, sort_dir=sort_dir)

        if need_api_sort:
            api_utils.make_api_sort(actions_collection.actions,
                                    sort_key, sort_dir)

        return actions_collection

    @wsme_pecan.wsexpose(ActionCollection, types.uuid, int,
                         wtypes.text, wtypes.text, types.uuid,
                         types.uuid)
    def get_all(self, marker=None, limit=None,
                sort_key='id', sort_dir='asc', action_plan_uuid=None,
                audit_uuid=None):
        """Retrieve a list of actions.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param action_plan_uuid: Optional UUID of an action plan,
           to get only actions for that action plan.
        :param audit_uuid: Optional UUID of an audit,
           to get only actions for that audit.
        """
        context = pecan.request.context
        policy.enforce(context, 'action:get_all',
                       action='action:get_all')

        if action_plan_uuid and audit_uuid:
            raise exception.ActionFilterCombinationProhibited

        return self._get_actions_collection(
            marker, limit, sort_key, sort_dir,
            action_plan_uuid=action_plan_uuid, audit_uuid=audit_uuid)

    @wsme_pecan.wsexpose(ActionCollection, types.uuid, int,
                         wtypes.text, wtypes.text, types.uuid,
                         types.uuid)
    def detail(self, marker=None, limit=None,
               sort_key='id', sort_dir='asc', action_plan_uuid=None,
               audit_uuid=None):
        """Retrieve a list of actions with detail.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param action_plan_uuid: Optional UUID of an action plan,
           to get only actions for that action plan.
        :param audit_uuid: Optional UUID of an audit,
           to get only actions for that audit.
        """
        context = pecan.request.context
        policy.enforce(context, 'action:detail',
                       action='action:detail')

        # NOTE(lucasagomes): /detail should only work against collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "actions":
            raise exception.HTTPNotFound

        if action_plan_uuid and audit_uuid:
            raise exception.ActionFilterCombinationProhibited

        expand = True
        resource_url = '/'.join(['actions', 'detail'])
        return self._get_actions_collection(
            marker, limit, sort_key, sort_dir, expand, resource_url,
            action_plan_uuid=action_plan_uuid, audit_uuid=audit_uuid)

    @wsme_pecan.wsexpose(Action, types.uuid)
    def get_one(self, action_uuid):
        """Retrieve information about the given action.

        :param action_uuid: UUID of a action.
        """
        if self.from_actions:
            raise exception.OperationNotPermitted

        context = pecan.request.context
        action = api_utils.get_resource('Action', action_uuid)
        policy.enforce(context, 'action:get', action, action='action:get')

        return Action.convert_with_links(action)

    @wsme_pecan.wsexpose(Action, body=Action, status_code=HTTPStatus.CREATED)
    def post(self, action):
        """Create a new action(forbidden).

        :param action: a action within the request body.
        """
        # FIXME: blueprint edit-action-plan-flow
        raise exception.OperationNotPermitted(
            _("Cannot create an action directly"))

        if self.from_actions:
            raise exception.OperationNotPermitted

        action_dict = action.as_dict()
        context = pecan.request.context
        new_action = objects.Action(context, **action_dict)
        new_action.create()

        # Set the HTTP Location Header
        pecan.response.location = link.build_url('actions', new_action.uuid)
        return Action.convert_with_links(new_action)

    @wsme.validate(types.uuid, [ActionPatchType])
    @wsme_pecan.wsexpose(Action, types.uuid, body=[ActionPatchType])
    def patch(self, action_uuid, patch):
        """Update an existing action(forbidden).

        :param action_uuid: UUID of a action.
        :param patch: a json PATCH document to apply to this action.
        """
        # FIXME: blueprint edit-action-plan-flow
        raise exception.OperationNotPermitted(
            _("Cannot modify an action directly"))

        if self.from_actions:
            raise exception.OperationNotPermitted

        action_to_update = objects.Action.get_by_uuid(pecan.request.context,
                                                      action_uuid)
        try:
            action_dict = action_to_update.as_dict()
            action = Action(**api_utils.apply_jsonpatch(action_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.Action.fields:
            try:
                patch_val = getattr(action, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if action_to_update[field] != patch_val:
                action_to_update[field] = patch_val

        action_to_update.save()
        return Action.convert_with_links(action_to_update)

    @wsme_pecan.wsexpose(None, types.uuid, status_code=HTTPStatus.NO_CONTENT)
    def delete(self, action_uuid):
        """Delete a action(forbidden).

        :param action_uuid: UUID of a action.
        """
        # FIXME: blueprint edit-action-plan-flow
        raise exception.OperationNotPermitted(
            _("Cannot delete an action directly"))

        action_to_delete = objects.Action.get_by_uuid(
            pecan.request.context,
            action_uuid)
        action_to_delete.soft_delete()
