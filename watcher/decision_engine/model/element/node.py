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


class ComputeNode(compute_resource.ComputeResource):

    def __init__(self, id):
        super(ComputeNode, self).__init__()
        self.id = id
        self._state = ServiceState.ONLINE.value
        self._status = ServiceState.ENABLED.value

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
