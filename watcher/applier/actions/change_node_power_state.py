# -*- encoding: utf-8 -*-
# Copyright (c) 2017 ZTE
#
# Authors: Li Canwei
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

import time

from oslo_log import log

from watcher._i18n import _
from watcher.applier.actions import base
from watcher.common import exception
from watcher.common.metal_helper import constants as metal_constants
from watcher.common.metal_helper import factory as metal_helper_factory

LOG = log.getLogger(__name__)


class ChangeNodePowerState(base.BaseAction):
    """Compute node power on/off

    By using this action, you will be able to on/off the power of a
    compute node.

    The action schema is::

        schema = Schema({
         'resource_id': str,
         'state': str,
        })

    The `resource_id` references a baremetal node id (list of available
    ironic nodes is returned by this command: ``ironic node-list``).
    The `state` value should either be `on` or `off`.
    """

    STATE = 'state'

    @property
    def schema(self):
        return {
            'type': 'object',
            'properties': {
                'resource_id': {
                    'type': 'string',
                    "minlength": 1
                },
                'resource_name': {
                    'type': 'string',
                    "minlength": 1
                },
                'state': {
                    'type': 'string',
                    'enum': [metal_constants.PowerState.ON.value,
                             metal_constants.PowerState.OFF.value]
                }
            },
            'required': ['resource_id', 'state'],
            'additionalProperties': False,
        }

    @property
    def node_uuid(self):
        return self.resource_id

    @property
    def state(self):
        return self.input_parameters.get(self.STATE)

    def execute(self):
        target_state = self.state
        return self._node_manage_power(target_state)

    def revert(self):
        if self.state == metal_constants.PowerState.ON.value:
            target_state = metal_constants.PowerState.OFF.value
        elif self.state == metal_constants.PowerState.OFF.value:
            target_state = metal_constants.PowerState.ON.value
        return self._node_manage_power(target_state)

    def _node_manage_power(self, state, retry=60):
        if state is None:
            raise exception.IllegalArgumentException(
                message=_("The target state is not defined"))

        metal_helper = metal_helper_factory.get_helper(self.osc)
        node = metal_helper.get_node(self.node_uuid)
        current_state = node.get_power_state()

        if state == current_state.value:
            return True

        if state == metal_constants.PowerState.OFF.value:
            compute_node = node.get_hypervisor_node().to_dict()
            if (compute_node['running_vms'] == 0):
                node.set_power_state(state)
            else:
                LOG.warning(
                    "Compute node %s has %s running vms and will "
                    "NOT be shut off.",
                    compute_node["hypervisor_hostname"],
                    compute_node['running_vms'])
                return False
        else:
            node.set_power_state(state)

        node = metal_helper.get_node(self.node_uuid)
        while node.get_power_state() == current_state and retry:
            time.sleep(10)
            retry -= 1
            node = metal_helper.get_node(self.node_uuid)
        if retry > 0:
            return True
        else:
            return False

    def pre_condition(self):
        pass

    def post_condition(self):
        pass

    def get_description(self):
        """Description of the action"""
        return ("Compute node power on/off through Ironic or MaaS.")
