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

from watcher.decision_engine.model.element import baremetal_resource
from watcher.decision_engine.model.element import compute_resource
from watcher.decision_engine.model.element import storage_resource
from watcher.objects import base
from watcher.objects import fields as wfields


class ServiceState(enum.Enum):
    ONLINE = 'up'
    OFFLINE = 'down'
    ENABLED = 'enabled'
    DISABLED = 'disabled'


@base.WatcherObjectRegistry.register_if(False)
class ComputeNode(compute_resource.ComputeResource):

    fields = {
        "id": wfields.StringField(),
        "hostname": wfields.StringField(),
        "status": wfields.StringField(default=ServiceState.ENABLED.value),
        "disabled_reason": wfields.StringField(nullable=True),
        "state": wfields.StringField(default=ServiceState.ONLINE.value),
        "memory": wfields.NonNegativeIntegerField(),
        "disk": wfields.IntegerField(),
        "disk_capacity": wfields.NonNegativeIntegerField(),
        "vcpus": wfields.NonNegativeIntegerField(),
    }

    def accept(self, visitor):
        raise NotImplementedError()


@base.WatcherObjectRegistry.register_if(False)
class StorageNode(storage_resource.StorageResource):

    fields = {
        "host": wfields.StringField(),
        "zone": wfields.StringField(),
        "status": wfields.StringField(default=ServiceState.ENABLED.value),
        "state": wfields.StringField(default=ServiceState.ONLINE.value),
        "volume_type": wfields.ListOfStringsField()
    }

    def accept(self, visitor):
        raise NotImplementedError()


@base.WatcherObjectRegistry.register_if(False)
class Pool(storage_resource.StorageResource):

    fields = {
        "name": wfields.StringField(),
        "total_volumes": wfields.NonNegativeIntegerField(),
        "total_capacity_gb": wfields.NonNegativeIntegerField(),
        "free_capacity_gb": wfields.NonNegativeIntegerField(),
        "provisioned_capacity_gb": wfields.NonNegativeIntegerField(),
        "allocated_capacity_gb": wfields.NonNegativeIntegerField(),
        "virtual_free": wfields.NonNegativeIntegerField(default=0),
    }

    def accept(self, visitor):
        raise NotImplementedError()


@base.WatcherObjectRegistry.register_if(False)
class IronicNode(baremetal_resource.BaremetalResource):

    fields = {
        "power_state": wfields.StringField(),
        "maintenance": wfields.BooleanField(),
        "maintenance_reason": wfields.StringField(),
        "extra": wfields.DictField()
    }

    def accept(self, visitor):
        raise NotImplementedError()
