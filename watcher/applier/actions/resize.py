# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica
#
# Authors: Alexander Chadin <a.chadin@servionica.ru>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.
#

from oslo_log import log

from watcher.applier.actions import base
from watcher.common import nova_helper

LOG = log.getLogger(__name__)


class Resize(base.BaseAction):
    """Resizes a server with specified flavor.

    This action will allow you to resize a server to another flavor.

    The action schema is::

        schema = Schema({
         'resource_id': str,  # should be a UUID
         'flavor': str,  # should be either ID or Name of Flavor
        })

    The `resource_id` is the UUID of the server to resize.
    The `flavor` is the ID or Name of Flavor (Nova accepts either ID or Name
    of Flavor to resize() function).
    """

    # input parameters constants
    FLAVOR = 'flavor'

    @property
    def schema(self):
        return {
            'type': 'object',
            'properties': {
                'resource_id': {
                    'type': 'string',
                    'minlength': 1,
                    'pattern': ('^([a-fA-F0-9]){8}-([a-fA-F0-9]){4}-'
                                '([a-fA-F0-9]){4}-([a-fA-F0-9]){4}-'
                                '([a-fA-F0-9]){12}$')
                },
                'flavor': {
                    'type': 'string',
                    'minlength': 1,
                },
            },
            'required': ['resource_id', 'flavor'],
            'additionalProperties': False,
        }

    @property
    def instance_uuid(self):
        return self.resource_id

    @property
    def flavor(self):
        return self.input_parameters.get(self.FLAVOR)

    def resize(self):
        nova = nova_helper.NovaHelper(osc=self.osc)
        LOG.debug("Resize instance %s to %s flavor", self.instance_uuid,
                  self.flavor)
        instance = nova.find_instance(self.instance_uuid)
        result = None
        if instance:
            try:
                result = nova.resize_instance(
                    instance_id=self.instance_uuid, flavor=self.flavor)
            except Exception as exc:
                LOG.exception(exc)
                LOG.critical(
                    "Unexpected error occurred. Resizing failed for "
                    "instance %s.", self.instance_uuid)
        return result

    def execute(self):
        return self.resize()

    def revert(self):
        LOG.warning("revert not supported")

    def pre_condition(self):
        # TODO(jed): check if the instance exists / check if the instance is on
        # the source_node
        pass

    def post_condition(self):
        # TODO(jed): check extra parameters (network response, etc.)
        pass

    def get_description(self):
        """Description of the action"""
        return "Resize a server with specified flavor."
