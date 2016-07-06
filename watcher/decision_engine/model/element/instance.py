# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

import enum

from watcher.decision_engine.model.element import compute_resource


class InstanceState(enum.Enum):
    ACTIVE = 'active'  # Instance is running
    BUILDING = 'building'  # Instance only exists in DB
    PAUSED = 'paused'
    SUSPENDED = 'suspended'  # Instance is suspended to disk.
    STOPPED = 'stopped'  # Instance is shut off, the disk image is still there.
    RESCUED = 'rescued'  # A rescue image is running with the original image
    # attached.
    RESIZED = 'resized'  # a Instance with the new size is active.

    SOFT_DELETED = 'soft-delete'
    # still available to restore.
    DELETED = 'deleted'  # Instance is permanently deleted.

    ERROR = 'error'


class Instance(compute_resource.ComputeResource):

    def __init__(self):
        super(Instance, self).__init__()
        self._state = InstanceState.ACTIVE.value

    def accept(self, visitor):
        raise NotImplementedError()

    @property
    def state(self):
        return self._state

    @state.setter
    def state(self, state):
        self._state = state
