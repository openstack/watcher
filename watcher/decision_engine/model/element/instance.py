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
from watcher.objects import base
from watcher.objects import fields as wfields


class InstanceState(enum.Enum):
    ACTIVE = 'active'  # Instance is running
    BUILDING = 'building'  # Instance only exists in DB
    PAUSED = 'paused'
    SUSPENDED = 'suspended'  # Instance is suspended to disk.
    STOPPED = 'stopped'  # Instance is shut off, the disk image is still there.
    RESCUED = 'rescued'  # A rescue image is running with the original image
    # attached.
    RESIZED = 'resized'  # an Instance with the new size is active.
    SHELVED = 'shelved'

    SOFT_DELETED = 'soft-delete'
    # still available to restore.
    DELETED = 'deleted'  # Instance is permanently deleted.

    ERROR = 'error'


@base.WatcherObjectRegistry.register_if(False)
class Instance(compute_resource.ComputeResource):

    fields = {
        # If the resource is excluded by the scope,
        # 'watcher_exclude' property will be set True.
        "watcher_exclude": wfields.BooleanField(default=False),
        "name": wfields.StringField(),
        "state": wfields.StringField(default=InstanceState.ACTIVE.value),
        "memory": wfields.NonNegativeIntegerField(),
        "disk": wfields.NonNegativeIntegerField(),
        "vcpus": wfields.NonNegativeIntegerField(),
        "metadata": wfields.JsonField(),
        "project_id": wfields.UUIDField(),
        "locked": wfields.BooleanField(default=False),
    }

    def accept(self, visitor):
        raise NotImplementedError()
