# Copyright (c) 2019 ZTE Corporation
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
An Interface for users and admin to List Data Model.
"""

import pecan
from pecan import rest
from wsme import types as wtypes
import wsmeext.pecan as wsme_pecan

from watcher.api.controllers.v1 import types
from watcher.api.controllers.v1 import utils
from watcher.common import exception
from watcher.common import policy
from watcher.decision_engine import rpcapi


def hide_fields_in_newer_versions(obj):
    """This method hides fields that were added in newer API versions.

    Certain node fields were introduced at certain API versions.
    These fields are only made available when the request's API version
    matches or exceeds the versions when these fields were introduced.
    """
    if not utils.allow_list_extend_compute_model():
        # NOTE(dviroel): the content returned by the rpc is
        # a list of dicts, so we need to remove the elements based
        # on the api version.
        for elem in obj.get('context', []):
            elem.pop('server_pinned_az', None)
            elem.pop('server_flavor_extra_specs', None)


class DataModelController(rest.RestController):
    """REST controller for data model"""

    def __init__(self):
        super().__init__()

    @wsme_pecan.wsexpose(wtypes.text, wtypes.text, types.uuid)
    def get_all(self, data_model_type='compute', audit_uuid=None):
        """Retrieve information about the given data model.

        :param data_model_type: The type of data model user wants to list.
                                Supported values: compute.
                                Future support values: storage, baremetal.
                                The default value is compute.
        :param audit_uuid: The UUID of the audit,  used to filter data model
                           by the scope in audit.
        """
        if not utils.allow_list_datamodel():
            raise exception.NotAcceptable
        allowed_data_model_type = [
            'compute',
            ]
        if data_model_type not in allowed_data_model_type:
            raise exception.DataModelTypeNotFound(
                data_model_type=data_model_type)
        context = pecan.request.context
        de_client = rpcapi.DecisionEngineAPI()
        policy.enforce(context, 'data_model:get_all',
                       action='data_model:get_all')
        rpc_all_data_model = de_client.get_data_model_info(
            context,
            data_model_type,
            audit_uuid)
        hide_fields_in_newer_versions(rpc_all_data_model)
        return rpc_all_data_model
