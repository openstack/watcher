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

import enum

from watcher._i18n import _
from watcher.applier.actions import base
from watcher.common import exception


class NodeState(enum.Enum):
    POWERON = 'on'
    POWEROFF = 'off'


class ChangeNodePowerState(base.BaseAction):
    """Compute node power on/off

    By using this action, you will be able to on/off the power of a
    compute node.

    The action schema is::

        schema = Schema({
         'resource_id': str,
         'state': str,
        })

    The `resource_id` references a ironic node id (list of available
    ironic node is returned by this command: ``ironic node-list``).
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
                'state': {
                    'type': 'string',
                    'enum': [NodeState.POWERON.value,
                             NodeState.POWEROFF.value]
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
        if self.state == NodeState.POWERON.value:
            target_state = NodeState.POWEROFF.value
        elif self.state == NodeState.POWEROFF.value:
            target_state = NodeState.POWERON.value
        return self._node_manage_power(target_state)

    def _node_manage_power(self, state):
        if state is None:
            raise exception.IllegalArgumentException(
                message=_("The target state is not defined"))

        result = False
        ironic_client = self.osc.ironic()
        nova_client = self.osc.nova()
        if state == NodeState.POWEROFF.value:
            node_info = ironic_client.node.get(self.node_uuid).to_dict()
            compute_node_id = node_info['extra']['compute_node_id']
            compute_node = nova_client.hypervisors.get(compute_node_id)
            compute_node = compute_node.to_dict()
            if (compute_node['running_vms'] == 0):
                result = ironic_client.node.set_power_state(
                    self.node_uuid, state)
        else:
            result = ironic_client.node.set_power_state(self.node_uuid, state)
        return result

    def pre_condition(self):
        pass

    def post_condition(self):
        pass

    def get_description(self):
        """Description of the action"""
        return ("Compute node power on/off through ironic.")
