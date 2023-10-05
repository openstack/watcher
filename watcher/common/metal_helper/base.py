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

import abc

from watcher.common import exception
from watcher.common.metal_helper import constants as metal_constants


class BaseMetalNode(abc.ABC):
    hv_up_when_powered_off = False

    def __init__(self, nova_node=None):
        self._nova_node = nova_node

    def get_hypervisor_node(self):
        if not self._nova_node:
            raise exception.Invalid(message="No associated hypervisor.")
        return self._nova_node

    def get_hypervisor_hostname(self):
        return self.get_hypervisor_node().hypervisor_hostname

    @abc.abstractmethod
    def get_power_state(self):
        # TODO(lpetrut): document the following methods
        pass

    @abc.abstractmethod
    def get_id(self):
        """Return the node id provided by the bare metal service."""
        pass

    @abc.abstractmethod
    def power_on(self):
        pass

    @abc.abstractmethod
    def power_off(self):
        pass

    def set_power_state(self, state):
        state = metal_constants.PowerState(state)
        if state == metal_constants.PowerState.ON:
            self.power_on()
        elif state == metal_constants.PowerState.OFF:
            self.power_off()
        else:
            raise exception.UnsupportedActionType(
                "Cannot set power state: %s" % state)


class BaseMetalHelper(abc.ABC):
    def __init__(self, osc):
        self._osc = osc

    @property
    def nova_client(self):
        if not getattr(self, "_nova_client", None):
            self._nova_client = self._osc.nova()
        return self._nova_client

    @abc.abstractmethod
    def list_compute_nodes(self):
        pass

    @abc.abstractmethod
    def get_node(self, node_id):
        pass
