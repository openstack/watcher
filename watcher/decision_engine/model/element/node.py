# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

import enum

from watcher.decision_engine.model.element import compute_resource


class ServiceState(enum.Enum):
    ONLINE = 'up'
    OFFLINE = 'down'
    ENABLED = 'enabled'
    DISABLED = 'disabled'


class PowerState(enum.Enum):
    # away mode
    g0 = "g0"
    # power on suspend (processor caches are flushed)
    # The power to the CPU(s) and RAM is maintained
    g1_S1 = "g1_S1"
    # CPU powered off. Dirty cache is flushed to RAM
    g1_S2 = "g1_S2"
    # Suspend to RAM
    g1_S3 = "g1_S3"
    # Suspend to Disk
    g1_S4 = "g1_S4"
    # switch outlet X OFF on the PDU (Power Distribution Unit)
    switch_off = "switch_off"
    # switch outlet X ON on the PDU (Power Distribution Unit)
    switch_on = "switch_on"


class ComputeNode(compute_resource.ComputeResource):

    def __init__(self):
        super(ComputeNode, self).__init__()
        self._state = ServiceState.ONLINE
        self._status = ServiceState.ENABLED
        self._power_state = PowerState.g0

    def accept(self, visitor):
        raise NotImplementedError()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state

    @property
    def status(self):
        return self._status

    @status.setter
    def status(self, s):
        self._status = s

    @property
    def powerstate(self):
        return self._power_state

    @powerstate.setter
    def powerstate(self, p):
        self._power_state = p
