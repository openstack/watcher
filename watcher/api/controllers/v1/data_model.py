# -*- encoding: utf-8 -*-
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
from watcher.common import exception
from watcher.common import policy
from watcher.decision_engine import rpcapi


class DataModelController(rest.RestController):
    """REST controller for data model"""
    def __init__(self):
        super(DataModelController, self).__init__()

    from_data_model = False
    """A flag to indicate if the requests to this controller are coming
    from the top-level resource DataModel."""

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
        if self.from_data_model:
            raise exception.OperationNotPermitted
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
        return rpc_all_data_model
