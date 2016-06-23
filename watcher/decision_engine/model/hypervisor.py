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

from watcher.decision_engine.model import compute_resource
from watcher.decision_engine.model import hypervisor_state
from watcher.decision_engine.model import power_state


class Hypervisor(compute_resource.ComputeResource):
    def __init__(self):
        super(Hypervisor, self).__init__()
        self._state = hypervisor_state.HypervisorState.ONLINE
        self._status = hypervisor_state.HypervisorState.ENABLED
        self._power_state = power_state.PowerState.g0

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
