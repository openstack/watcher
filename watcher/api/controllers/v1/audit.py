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

import datetime

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
from watcher.common import utils
from watcher.decision_engine.framework.rpcapi import DecisionEngineAPI
from watcher import objects


class AuditPatchType(types.JsonPatchType):

    @staticmethod
    def mandatory_attrs():
        return ['/audit_template_uuid']


class Audit(base.APIBase):
    """API representation of a audit.

    This class enforces type checking and value constraints, and converts
    between the internal object model and the API representation of a audit.
    """
    _audit_template_uuid = None
    _audit_template_name = None

    def _get_audit_template(self, value):
        if value == wtypes.Unset:
            return None
        audit_template = None
        try:
            if utils.is_uuid_like(value) or utils.is_int_like(value):
                audit_template = objects.AuditTemplate.get(
                    pecan.request.context, value)
            else:
                audit_template = objects.AuditTemplate.get_by_name(
                    pecan.request.context, value)
        except exception.AuditTemplateNotFound:
            pass
        if audit_template:
            self.audit_template_id = audit_template.id
        return audit_template

    def _get_audit_template_uuid(self):
        return self._audit_template_uuid

    def _set_audit_template_uuid(self, value):
        if value and self._audit_template_uuid != value:
            self._audit_template_uuid = None
            audit_template = self._get_audit_template(value)
            if audit_template:
                self._audit_template_uuid = audit_template.uuid

    def _get_audit_template_name(self):
        return self._audit_template_name

    def _set_audit_template_name(self, value):
        if value and self._audit_template_name != value:
            self._audit_template_name = None
            audit_template = self._get_audit_template(value)
            if audit_template:
                self._audit_template_name = audit_template.name

    uuid = types.uuid
    """Unique UUID for this audit"""

    type = wtypes.text
    """Type of this audit"""

    deadline = datetime.datetime
    """deadline of the audit"""

    state = wtypes.text
    """This audit state"""

    audit_template_uuid = wsme.wsproperty(wtypes.text,
                                          _get_audit_template_uuid,
                                          _set_audit_template_uuid,
                                          mandatory=True)
    """The UUID of the audit template this audit refers to"""

    audit_template_name = wsme.wsproperty(wtypes.text,
                                          _get_audit_template_name,
                                          _set_audit_template_name,
                                          mandatory=False)
    """The name of the audit template this audit refers to"""

    links = wsme.wsattr([link.Link], readonly=True)
    """A list containing a self link and associated audit links"""

    def __init__(self, **kwargs):
        self.fields = []
        fields = list(objects.Audit.fields)

        for k in fields:
            # Skip fields we do not expose.
            if not hasattr(self, k):
                continue
            self.fields.append(k)
            setattr(self, k, kwargs.get(k, wtypes.Unset))

        self.fields.append('audit_template_id')

        # audit_template_uuid & audit_template_name are not part of
        # objects.Audit.fields because they're API-only attributes.
        fields.append('audit_template_uuid')
        setattr(self, 'audit_template_uuid', kwargs.get('audit_template_id',
                wtypes.Unset))
        fields.append('audit_template_name')
        setattr(self, 'audit_template_name', kwargs.get('audit_template_id',
                wtypes.Unset))

    @staticmethod
    def _convert_with_links(audit, url, expand=True):
        if not expand:
            audit.unset_fields_except(['uuid', 'type', 'deadline',
                                       'state', 'audit_template_uuid',
                                       'audit_template_name'])

        # The numeric ID should not be exposed to
        # the user, it's internal only.
        audit.audit_template_id = wtypes.Unset

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
        return cls._convert_with_links(audit, pecan.request.host_url, expand)

    @classmethod
    def sample(cls, expand=True):
        sample = cls(uuid='27e3153e-d5bf-4b7e-b517-fb518e17f34c',
                     type='ONESHOT',
                     state='PENDING',
                     deadline=None,
                     created_at=datetime.datetime.utcnow(),
                     deleted_at=None,
                     updated_at=datetime.datetime.utcnow())
        sample._audit_template_uuid = '7ae81bb3-dec3-4289-8d6c-da80bd8001ae'
        return cls._convert_with_links(sample, 'http://localhost:9322', expand)


class AuditCollection(collection.Collection):
    """API representation of a collection of audits."""

    audits = [Audit]
    """A list containing audits objects"""

    def __init__(self, **kwargs):
        self._type = 'audits'

    @staticmethod
    def convert_with_links(rpc_audits, limit, url=None, expand=False,
                           **kwargs):
        collection = AuditCollection()
        collection.audits = [Audit.convert_with_links(p, expand)
                             for p in rpc_audits]

        if 'sort_key' in kwargs:
            reverse = False
            if kwargs['sort_key'] == 'audit_template_uuid':
                if 'sort_dir' in kwargs:
                    reverse = True if kwargs['sort_dir'] == 'desc' else False
                collection.audits = sorted(
                    collection.audits,
                    key=lambda audit: audit.audit_template_uuid,
                    reverse=reverse)

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

    from_audits = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource Audits."""

    _custom_actions = {
        'detail': ['GET'],
    }

    def _get_audits_collection(self, marker, limit,
                               sort_key, sort_dir, expand=False,
                               resource_url=None, audit_template=None):
        limit = api_utils.validate_limit(limit)
        sort_dir = api_utils.validate_sort_dir(sort_dir)

        marker_obj = None
        if marker:
            marker_obj = objects.Audit.get_by_uuid(pecan.request.context,
                                                   marker)

        filters = {}
        if audit_template:
            if utils.is_uuid_like(audit_template):
                filters['audit_template_uuid'] = audit_template
            else:
                filters['audit_template_name'] = audit_template

        if sort_key == 'audit_template_uuid':
            sort_db_key = None
        else:
            sort_db_key = sort_key

        audits = objects.Audit.list(pecan.request.context,
                                    limit,
                                    marker_obj, sort_key=sort_db_key,
                                    sort_dir=sort_dir, filters=filters)

        return AuditCollection.convert_with_links(audits, limit,
                                                  url=resource_url,
                                                  expand=expand,
                                                  sort_key=sort_key,
                                                  sort_dir=sort_dir)

    @wsme_pecan.wsexpose(AuditCollection, types.uuid,
                         types.uuid, int, wtypes.text,
                         wtypes.text, wtypes.text)
    def get_all(self, audit_uuid=None, marker=None, limit=None,
                sort_key='id', sort_dir='asc', audit_template=None):
        """Retrieve a list of audits.

        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        :param audit_template: Optional UUID or name of an audit
         template, to get only audits for that audit template.
        """
        return self._get_audits_collection(marker, limit, sort_key,
                                           sort_dir,
                                           audit_template=audit_template)

    @wsme_pecan.wsexpose(AuditCollection, types.uuid,
                         types.uuid, int, wtypes.text, wtypes.text)
    def detail(self, audit_uuid=None, marker=None, limit=None,
               sort_key='id', sort_dir='asc'):
        """Retrieve a list of audits with detail.

        :param audit_uuid: UUID of a audit, to get only audits for that audit.
        :param marker: pagination marker for large data sets.
        :param limit: maximum number of resources to return in a single result.
        :param sort_key: column to sort results by. Default: id.
        :param sort_dir: direction to sort. "asc" or "desc". Default: asc.
        """
        # NOTE(lucasagomes): /detail should only work agaist collections
        parent = pecan.request.path.split('/')[:-1][-1]
        if parent != "audits":
            raise exception.HTTPNotFound

        expand = True
        resource_url = '/'.join(['audits', 'detail'])
        return self._get_audits_collection(marker, limit,
                                           sort_key, sort_dir, expand,
                                           resource_url)

    @wsme_pecan.wsexpose(Audit, types.uuid)
    def get_one(self, audit_uuid):
        """Retrieve information about the given audit.

        :param audit_uuid: UUID of a audit.
        """
        if self.from_audits:
            raise exception.OperationNotPermitted

        rpc_audit = objects.Audit.get_by_uuid(pecan.request.context,
                                              audit_uuid)
        return Audit.convert_with_links(rpc_audit)

    @wsme_pecan.wsexpose(Audit, body=Audit, status_code=201)
    def post(self, audit):
        """Create a new audit.

        :param audit: a audit within the request body.
        """
        if self.from_audits:
            raise exception.OperationNotPermitted

        audit_dict = audit.as_dict()
        context = pecan.request.context
        new_audit = objects.Audit(context, **audit_dict)
        new_audit.create(context)

        # Set the HTTP Location Header
        pecan.response.location = link.build_url('audits', new_audit.uuid)

        # trigger decision-engine to run the audit

        dc_client = DecisionEngineAPI()
        dc_client.trigger_audit(context, new_audit.uuid)

        return Audit.convert_with_links(new_audit)

    @wsme.validate(types.uuid, [AuditPatchType])
    @wsme_pecan.wsexpose(Audit, types.uuid, body=[AuditPatchType])
    def patch(self, audit_uuid, patch):
        """Update an existing audit.

        :param audit_uuid: UUID of a audit.
        :param patch: a json PATCH document to apply to this audit.
        """
        if self.from_audits:
            raise exception.OperationNotPermitted

        audit_to_update = objects.Audit.get_by_uuid(pecan.request.context,
                                                    audit_uuid)
        try:
            audit_dict = audit_to_update.as_dict()
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

    @wsme_pecan.wsexpose(None, types.uuid, status_code=204)
    def delete(self, audit_uuid):
        """Delete a audit.

        :param audit_uuid: UUID of a audit.
        """

        audit_to_delete = objects.Audit.get_by_uuid(
            pecan.request.context,
            audit_uuid)
        audit_to_delete.soft_delete()
