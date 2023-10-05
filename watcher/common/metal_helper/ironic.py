# Copyright 2023 Cloudbase Solutions
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

from oslo_log import log

from watcher.common.metal_helper import base
from watcher.common.metal_helper import constants as metal_constants

LOG = log.getLogger(__name__)

POWER_STATES_MAP = {
    'power on': metal_constants.PowerState.ON,
    'power off': metal_constants.PowerState.OFF,
    # For now, we only use ON/OFF states
    'rebooting': metal_constants.PowerState.ON,
    'soft power off': metal_constants.PowerState.OFF,
    'soft reboot': metal_constants.PowerState.ON,
}


class IronicNode(base.BaseMetalNode):
    hv_up_when_powered_off = True

    def __init__(self, ironic_node, nova_node, ironic_client):
        super().__init__(nova_node)

        self._ironic_client = ironic_client
        self._ironic_node = ironic_node

    def get_power_state(self):
        return POWER_STATES_MAP.get(self._ironic_node.power_state,
                                    metal_constants.PowerState.UNKNOWN)

    def get_id(self):
        return self._ironic_node.uuid

    def power_on(self):
        self._ironic_client.node.set_power_state(self.get_id(), "on")

    def power_off(self):
        self._ironic_client.node.set_power_state(self.get_id(), "off")


class IronicHelper(base.BaseMetalHelper):
    @property
    def _client(self):
        if not getattr(self, "_cached_client", None):
            self._cached_client = self._osc.ironic()
        return self._cached_client

    def list_compute_nodes(self):
        out_list = []
        # TODO(lpetrut): consider using "detailed=True" instead of making
        # an additional GET request per node
        node_list = self._client.node.list()

        for node in node_list:
            node_info = self._client.node.get(node.uuid)
            hypervisor_id = node_info.extra.get('compute_node_id', None)
            if hypervisor_id is None:
                LOG.warning('Cannot find compute_node_id in extra '
                            'of ironic node %s', node.uuid)
                continue

            hypervisor_node = self.nova_client.hypervisors.get(hypervisor_id)
            if hypervisor_node is None:
                LOG.warning('Cannot find hypervisor %s', hypervisor_id)
                continue

            out_node = IronicNode(node, hypervisor_node, self._client)
            out_list.append(out_node)

        return out_list

    def get_node(self, node_id):
        ironic_node = self._client.node.get(node_id)
        compute_node_id = ironic_node.extra.get('compute_node_id')
        if compute_node_id:
            compute_node = self.nova_client.hypervisors.get(compute_node_id)
        else:
            compute_node = None
        return IronicNode(ironic_node, compute_node, self._client)
