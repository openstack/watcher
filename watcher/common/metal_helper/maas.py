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

from oslo_config import cfg
from oslo_log import log

from watcher.common import exception
from watcher.common.metal_helper import base
from watcher.common.metal_helper import constants as metal_constants
from watcher.common import utils

CONF = cfg.CONF
LOG = log.getLogger(__name__)

try:
    from maas.client import enum as maas_enum
except ImportError:
    maas_enum = None


class MaasNode(base.BaseMetalNode):
    hv_up_when_powered_off = False

    def __init__(self, maas_node, nova_node, maas_client):
        super().__init__(nova_node)

        self._maas_client = maas_client
        self._maas_node = maas_node

    def get_power_state(self):
        maas_state = utils.async_compat_call(
            self._maas_node.query_power_state,
            timeout=CONF.maas_client.timeout)

        # python-libmaas may not be available, so we'll avoid a global
        # variable.
        power_states_map = {
            maas_enum.PowerState.ON: metal_constants.PowerState.ON,
            maas_enum.PowerState.OFF: metal_constants.PowerState.OFF,
            maas_enum.PowerState.ERROR: metal_constants.PowerState.ERROR,
            maas_enum.PowerState.UNKNOWN: metal_constants.PowerState.UNKNOWN,
        }
        return power_states_map.get(maas_state,
                                    metal_constants.PowerState.UNKNOWN)

    def get_id(self):
        return self._maas_node.system_id

    def power_on(self):
        LOG.info("Powering on MAAS node: %s %s",
                 self._maas_node.fqdn,
                 self._maas_node.system_id)
        utils.async_compat_call(
            self._maas_node.power_on,
            timeout=CONF.maas_client.timeout)

    def power_off(self):
        LOG.info("Powering off MAAS node: %s %s",
                 self._maas_node.fqdn,
                 self._maas_node.system_id)
        utils.async_compat_call(
            self._maas_node.power_off,
            timeout=CONF.maas_client.timeout)


class MaasHelper(base.BaseMetalHelper):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not maas_enum:
            raise exception.UnsupportedError(
                "MAAS client unavailable. Please install python-libmaas.")

    @property
    def _client(self):
        if not getattr(self, "_cached_client", None):
            self._cached_client = self._osc.maas()
        return self._cached_client

    def list_compute_nodes(self):
        out_list = []
        node_list = utils.async_compat_call(
            self._client.machines.list,
            timeout=CONF.maas_client.timeout)

        compute_nodes = self.nova_client.hypervisors.list()
        compute_node_map = dict()
        for compute_node in compute_nodes:
            compute_node_map[compute_node.hypervisor_hostname] = compute_node

        for node in node_list:
            hypervisor_node = compute_node_map.get(node.fqdn)
            if not hypervisor_node:
                LOG.info('Cannot find hypervisor %s', node.fqdn)
                continue

            out_node = MaasNode(node, hypervisor_node, self._client)
            out_list.append(out_node)

        return out_list

    def _get_compute_node_by_hostname(self, hostname):
        compute_nodes = self.nova_client.hypervisors.search(
            hostname, detailed=True)
        for compute_node in compute_nodes:
            if compute_node.hypervisor_hostname == hostname:
                return compute_node

    def get_node(self, node_id):
        maas_node = utils.async_compat_call(
            self._client.machines.get, node_id,
            timeout=CONF.maas_client.timeout)
        compute_node = self._get_compute_node_by_hostname(maas_node.fqdn)
        return MaasNode(maas_node, compute_node, self._client)
