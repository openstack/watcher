# Copyright 2013 Red Hat, Inc.
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
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

from operator import attrgetter

import jsonpatch
from oslo_config import cfg
from oslo_utils import reflection
from oslo_utils import uuidutils
import pecan
import wsme

from watcher._i18n import _
from watcher.api.controllers.v1 import versions
from watcher.common import utils
from watcher import objects

CONF = cfg.CONF


JSONPATCH_EXCEPTIONS = (jsonpatch.JsonPatchException,
                        jsonpatch.JsonPointerException,
                        KeyError)


def validate_limit(limit):
    if limit is None:
        return CONF.api.max_limit

    if limit <= 0:
        # Case where we don't a valid limit value
        raise wsme.exc.ClientSideError(_("Limit must be positive"))

    if limit and not CONF.api.max_limit:
        # Case where we don't have an upper limit
        return limit

    return min(CONF.api.max_limit, limit)


def validate_sort_dir(sort_dir):
    if sort_dir not in ['asc', 'desc']:
        raise wsme.exc.ClientSideError(_("Invalid sort direction: %s. "
                                         "Acceptable values are "
                                         "'asc' or 'desc'") % sort_dir)


def validate_sort_key(sort_key, allowed_fields):
    # Very lightweight validation for now
    if sort_key not in allowed_fields:
        raise wsme.exc.ClientSideError(
            _("Invalid sort key: %s") % sort_key)


def validate_search_filters(filters, allowed_fields):
    # Very lightweight validation for now
    # todo: improve this (e.g. https://www.parse.com/docs/rest/guide/#queries)
    for filter_name in filters:
        if filter_name not in allowed_fields:
            raise wsme.exc.ClientSideError(
                _("Invalid filter: %s") % filter_name)


def check_need_api_sort(sort_key, additional_fields):
    return sort_key in additional_fields


def make_api_sort(sorting_list, sort_key, sort_dir):
    # First sort by uuid field, than sort by sort_key
    # sort() ensures stable sorting, so we could
    # make lexicographical sort
    reverse_direction = (sort_dir == 'desc')
    sorting_list.sort(key=attrgetter('uuid'), reverse=reverse_direction)
    sorting_list.sort(key=attrgetter(sort_key), reverse=reverse_direction)


def apply_jsonpatch(doc, patch):
    for p in patch:
        if p['op'] == 'add' and p['path'].count('/') == 1:
            if p['path'].lstrip('/') not in doc:
                msg = _('Adding a new attribute (%s) to the root of '
                        ' the resource is not allowed')
                raise wsme.exc.ClientSideError(msg % p['path'])
    return jsonpatch.apply_patch(doc, jsonpatch.JsonPatch(patch))


def get_patch_value(patch, key):
    for p in patch:
        if p['op'] == 'replace' and p['path'] == '/%s' % key:
            return p['value']


def set_patch_value(patch, key, value):
    for p in patch:
        if p['op'] == 'replace' and p['path'] == '/%s' % key:
            p['value'] = value


def get_patch_key(patch, key):
    for p in patch:
        if p['op'] == 'replace' and key in p.keys():
            return p[key][1:]


def check_audit_state_transition(patch, initial):
    is_transition_valid = True
    state_value = get_patch_value(patch, "state")
    if state_value is not None:
        is_transition_valid = objects.audit.AuditStateTransitionManager(
            ).check_transition(initial, state_value)
    return is_transition_valid


def as_filters_dict(**filters):
    filters_dict = {}
    for filter_name, filter_value in filters.items():
        if filter_value:
            filters_dict[filter_name] = filter_value

    return filters_dict


def get_resource(resource, resource_id, eager=False):
    """Get the resource from the uuid, id or logical name.

    :param resource: the resource type.
    :param resource_id: the UUID, ID or logical name of the resource.

    :returns: The resource.
    """
    resource = getattr(objects, resource)

    _get = None
    if utils.is_int_like(resource_id):
        resource_id = int(resource_id)
        _get = resource.get
    elif uuidutils.is_uuid_like(resource_id):
        _get = resource.get_by_uuid
    else:
        _get = resource.get_by_name

    method_signature = reflection.get_signature(_get)
    if 'eager' in method_signature.parameters:
        return _get(pecan.request.context, resource_id, eager=eager)

    return _get(pecan.request.context, resource_id)


def allow_start_end_audit_time():
    """Check if we should support optional start/end attributes for Audit.

    Version 1.1 of the API added support for start and end time of continuous
    audits.
    """
    return pecan.request.version.minor >= versions.MINOR_1_START_END_TIMING


def allow_force():
    """Check if we should support optional force attribute for Audit.

    Version 1.2 of the API added support for forced audits that allows to
    launch audit when other action plan is ongoing.
    """
    return pecan.request.version.minor >= versions.MINOR_2_FORCE
