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
An :ref:`Audit <audit_definition>` may be launched several times with the same
settings (:ref:`Goal <goal_definition>`, thresholds, ...). Therefore it makes
sense to save those settings in some sort of Audit preset object, which is
known as an :ref:`Audit Template <audit_template_definition>`.

An :ref:`Audit Template <audit_template_definition>` contains at least the
:ref:`Goal <goal_definition>` of the :ref:`Audit <audit_definition>`.

It may also contain some error handling settings indicating whether:

-  :ref:`Watcher Applier <watcher_applier_definition>` stops the
   entire operation
-  :ref:`Watcher Applier <watcher_applier_definition>` performs a rollback

and how many retries should be attempted before failure occurs (also the latter
can be complex: for example the scenario in which there are many first-time
failures on ultimately successful :ref:`Actions <action_definition>`).

Moreover, an :ref:`Audit Template <audit_template_definition>` may contain some
settings related to the level of automation for the
:ref:`Action Plan <action_plan_definition>` that will be generated by the
:ref:`Audit <audit_definition>`.
A flag will indicate whether the :ref:`Action Plan <action_plan_definition>`
will be launched automatically or will need a manual confirmation from the
:ref:`Administrator <administrator_definition>`.

Last but not least, an :ref:`Audit Template <audit_template_definition>` may
contain a list of extra parameters related to the
:ref:`Strategy <strategy_definition>` configuration. These parameters can be
provided as a list of key-value pairs.
"""

import datetime

from oslo_config import cfg
import pecan
from pecan import rest
import wsme
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from watcher.api.controllers import base
from watcher.api.controllers import link
from watcher.api.controllers.v1 import collection
from watcher.api.controllers.v1 import types
from watcher.api.controllers.v1 import utils as api_utils
from watcher.common import exception
from watcher.common import utils as common_utils
from watcher import objects


class AuditTemplatePatchType(types.JsonPatchType):
    @staticmethod
    def mandatory_attrs():
        return []

    @staticmethod
    def validate(patch):
        if patch.path == "/goal":
            AuditTemplatePatchType._validate_goal(patch)
        return types.JsonPatchType.validate(patch)

    @staticmethod
    def _validate_goal(patch):
        serialized_patch = {'path': patch.path, 'op': patch.op}
        if patch.value is not wsme.Unset:
            serialized_patch['value'] = patch.value
        new_goal = patch.value
        if new_goal and new_goal not in cfg.CONF.watcher_goals.goals.keys():
            raise exception.InvalidGoal(goal=new_goal)


class AuditTemplate(base.APIBase):
    """API representation of a audit template.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of an
    audit template.
    """

    uuid = wtypes.wsattr(types.uuid, readonly=True)
    """Unique UUID for this audit template"""

    name = wtypes.text
    """Name of this audit template"""

    description = wtypes.text
    """Short description of this audit template"""

    deadline = datetime.datetime
    """deadline of the audit template"""

    host_aggregate = wtypes.IntegerType(minimum=1)
    """ID of the Nova host aggregate targeted by the audit template"""

    extra = {wtypes.text: types.jsontype}
    """The metadata of the audit template"""

    goal = wtypes.text
    """Goal type of the audit template"""

    version = wtypes.text
    """Internal version of the audit template"""

    audits = wsme.wsattr([link.Link], readonly=True)
    """Links to the collection of audits contained in this audit template"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated audit template links"""

    def __init__(self, **kwargs):
        super(AuditTemplate, self).__init__()

        self.fields = []
        for field in objects.AuditTemplate.fields:
            # Skip fields we do not expose.
            if not hasattr(self, field):
                continue
            self.fields.append(field)
            setattr(self, field, kwargs.get(field, wtypes.Unset))

    @staticmethod
    def _convert_with_links(audit_template, url, expand=True):
        if not expand:
            audit_template.unset_fields_except(['uuid', 'name',
                                                'host_aggregate', 'goal'])

        audit_template.links = [link.Link.make_link('self', url,
                                                    'audit_templates',
                                                    audit_template.uuid),
                                link.Link.make_link('bookmark', url,
                                                    'audit_templates',
                                                    audit_template.uuid,
                                                    bookmark=True)
                                ]
        return audit_template

    @classmethod
    def convert_with_links(cls, rpc_audit_template, expand=True):
        audit_template = AuditTemplate(**rpc_audit_template.as_dict())
        return cls._convert_with_links(audit_template, pecan.request.host_url,
                                       expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     name='My Audit Template',
                     description='Description of my audit template',
                     host_aggregate=5,
                     goal='DUMMY',
                     extra={'automatic': True},
                     created_at=datetime.datetime.utcnow(),
                     deleted_at=None,
                     updated_at=datetime.datetime.utcnow())
        return cls._convert_with_links(sample, 'http://localhost:9322', expand)

    @staticmethod
    def validate(audit_template):
        if audit_template.goal not in cfg.CONF.watcher_goals.goals.keys():
            raise exception.InvalidGoal(audit_template.goal)
        return audit_template


class AuditTemplateCollection(collection.Collection):
    """API representation of a collection of audit templates."""

    audit_templates = [AuditTemplate]
    """A list containing audit templates objects"""

    def __init__(self, **kwargs):
        super(AuditTemplateCollection, self).__init__()
        self._type = 'audit_templates'

    @staticmethod
    def convert_with_links(rpc_audit_templates, limit, url=None, expand=False,
                           **kwargs):
        collection = AuditTemplateCollection()
        collection.audit_templates = \
            [AuditTemplate.convert_with_links(p, expand)
                for p in rpc_audit_templates]
        collection.next = collection.get_next(limit, url=url, **kwargs)
        return collection

    @classmethod
    def sample(cls):
        sample = cls()
        sample.audit_templates = [AuditTemplate.sample(expand=False)]
        return sample


class AuditTemplatesController(rest.RestController):
    """REST controller for AuditTemplates."""
    def __init__(self):
        super(AuditTemplatesController, self).__init__()

    from_audit_templates = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource AuditTemplates."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_audit_templates_collection(self, filters, marker, limit,
                                        sort_key, sort_dir, expand=False,
                                        resource_url=None):
        api_utils.validate_search_filters(
            filters, objects.audit_template.AuditTemplate.fields.keys())
        limit = api_utils.validate_limit(limit)
        api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.AuditTemplate.get_by_uuid(
                pecan.request.context,
                marker)

        audit_templates = objects.AuditTemplate.list(
            pecan.request.context,
            filters,
            limit,
            marker_obj, sort_key=sort_key,
            sort_dir=sort_dir)

        return AuditTemplateCollection.convert_with_links(audit_templates,
                                                          limit,
                                                          url=resource_url,
                                                          expand=expand,
                                                          sort_key=sort_key,
                                                          sort_dir=sort_dir)

    @wsme_pecan.wsexpose(AuditTemplateCollection, wtypes.text,
                         types.uuid, int, wtypes.text, wtypes.text)
    def get_all(self, goal=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc'):
        """Retrieve a list of audit templates.

        :param goal: goal name to filter by (case sensitive)
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        filters = api_utils.as_filters_dict(goal=goal)

        return self._get_audit_templates_collection(
            filters, marker, limit, sort_key, sort_dir)

    @wsme_pecan.wsexpose(AuditTemplateCollection, wtypes.text, types.uuid, int,
                         wtypes.text, wtypes.text)
    def detail(self, goal=None, marker=None, limit=None,
               sort_key='id', sort_dir='asc'):
        """Retrieve a list of audit templates with detail.

        :param goal: goal name to filter by (case sensitive)
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        # NOTE(lucasagomes): /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "audit_templates":
            raise exception.HTTPNotFound

        filters = api_utils.as_filters_dict(goal=goal)

        expand = True
        resource_url = '/'.join(['audit_templates', 'detail'])
        return self._get_audit_templates_collection(filters, marker, limit,
                                                    sort_key, sort_dir, expand,
                                                    resource_url)

    @wsme_pecan.wsexpose(AuditTemplate, wtypes.text)
    def get_one(self, audit_template):
        """Retrieve information about the given audit template.

        :param audit audit_template: UUID or name of an audit template.
        """
        if self.from_audit_templates:
            raise exception.OperationNotPermitted

        if common_utils.is_uuid_like(audit_template):
            rpc_audit_template = objects.AuditTemplate.get_by_uuid(
                pecan.request.context,
                audit_template)
        else:
            rpc_audit_template = objects.AuditTemplate.get_by_name(
                pecan.request.context,
                audit_template)

        return AuditTemplate.convert_with_links(rpc_audit_template)

    @wsme.validate(types.uuid, AuditTemplate)
    @wsme_pecan.wsexpose(AuditTemplate, body=AuditTemplate, status_code=201)
    def post(self, audit_template):
        """Create a new audit template.

        :param audit template: a audit template within the request body.
        """

        if self.from_audit_templates:
            raise exception.OperationNotPermitted

        audit_template_dict = audit_template.as_dict()
        context = pecan.request.context
        new_audit_template = objects.AuditTemplate(context,
                                                   **audit_template_dict)
        new_audit_template.create(context)

        # Set the HTTP Location Header
        pecan.response.location = link.build_url('audit_templates',
                                                 new_audit_template.uuid)
        return AuditTemplate.convert_with_links(new_audit_template)

    @wsme.validate(types.uuid, [AuditTemplatePatchType])
    @wsme_pecan.wsexpose(AuditTemplate, wtypes.text,
                         body=[AuditTemplatePatchType])
    def patch(self, audit_template, patch):
        """Update an existing audit template.

        :param audit template_uuid: UUID of a audit template.
        :param patch: a json PATCH document to apply to this audit template.
        """
        if self.from_audit_templates:
            raise exception.OperationNotPermitted

        if common_utils.is_uuid_like(audit_template):
            audit_template_to_update = objects.AuditTemplate.get_by_uuid(
                pecan.request.context,
                audit_template)
        else:
            audit_template_to_update = objects.AuditTemplate.get_by_name(
                pecan.request.context,
                audit_template)

        try:
            audit_template_dict = audit_template_to_update.as_dict()
            audit_template = AuditTemplate(**api_utils.apply_jsonpatch(
                audit_template_dict, patch))
        except api_utils.JSONPATCH_EXCEPTIONS as e:
            raise exception.PatchError(patch=patch, reason=e)

        # Update only the fields that have changed
        for field in objects.AuditTemplate.fields:
            try:
                patch_val = getattr(audit_template, field)
            except AttributeError:
                # Ignore fields that aren't exposed in the API
                continue
            if patch_val == wtypes.Unset:
                patch_val = None
            if audit_template_to_update[field] != patch_val:
                audit_template_to_update[field] = patch_val

        audit_template_to_update.save()
        return AuditTemplate.convert_with_links(audit_template_to_update)

    @wsme_pecan.wsexpose(None, wtypes.text, status_code=204)
    def delete(self, audit_template):
        """Delete a audit template.

        :param audit template_uuid: UUID or name of an audit template.
        """

        if common_utils.is_uuid_like(audit_template):
            audit_template_to_delete = objects.AuditTemplate.get_by_uuid(
                pecan.request.context,
                audit_template)
        else:
            audit_template_to_delete = objects.AuditTemplate.get_by_name(
                pecan.request.context,
                audit_template)

        audit_template_to_delete.soft_delete()
