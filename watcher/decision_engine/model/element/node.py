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

from oslo_versionedobjects import fields as ovo_fields

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
        "hostname": ovo_fields.StringField(),
        "status": ovo_fields.StringField(default=ServiceState.ENABLED.value),
        "disabled_reason": ovo_fields.StringField(nullable=True),
        "state": ovo_fields.StringField(default=ServiceState.ONLINE.value),
        "memory": ovo_fields.NonNegativeIntegerField(),
        "memory_mb_reserved": ovo_fields.NonNegativeIntegerField(),
        "disk": ovo_fields.NonNegativeIntegerField(),
        "disk_gb_reserved": ovo_fields.NonNegativeIntegerField(),
        "vcpus": ovo_fields.NonNegativeIntegerField(),
        "vcpu_reserved": ovo_fields.NonNegativeIntegerField(),
        "memory_ratio": ovo_fields.NonNegativeFloatField(),
        "vcpu_ratio": ovo_fields.NonNegativeFloatField(),
        "disk_ratio": ovo_fields.NonNegativeFloatField(),
    }

    def accept(self, visitor):
        raise NotImplementedError()

    @property
    def memory_mb_capacity(self):
        return (self.memory - self.memory_mb_reserved) * self.memory_ratio

    @property
    def disk_gb_capacity(self):
        return (self.disk - self.disk_gb_reserved) * self.disk_ratio

    @property
    def vcpu_capacity(self):
        return (self.vcpus - self.vcpu_reserved) * self.vcpu_ratio


@base.WatcherObjectRegistry.register_if(False)
class StorageNode(storage_resource.StorageResource):
    fields = {
        "host": ovo_fields.StringField(),
        "zone": ovo_fields.StringField(),
        "status": ovo_fields.StringField(default=ServiceState.ENABLED.value),
        "state": ovo_fields.StringField(default=ServiceState.ONLINE.value),
        "volume_type": ovo_fields.ListOfStringsField(),
    }

    def accept(self, visitor):
        raise NotImplementedError()


@base.WatcherObjectRegistry.register_if(False)
class Pool(storage_resource.StorageResource):
    fields = {
        "name": ovo_fields.StringField(),
        "total_volumes": ovo_fields.NonNegativeIntegerField(),
        "total_capacity_gb": ovo_fields.NonNegativeIntegerField(),
        "free_capacity_gb": ovo_fields.NonNegativeIntegerField(),
        "provisioned_capacity_gb": ovo_fields.NonNegativeIntegerField(),
        "allocated_capacity_gb": ovo_fields.NonNegativeIntegerField(),
        "virtual_free": ovo_fields.NonNegativeIntegerField(default=0),
    }

    def accept(self, visitor):
        raise NotImplementedError()


@base.WatcherObjectRegistry.register_if(False)
class IronicNode(baremetal_resource.BaremetalResource):
    fields = {
        "power_state": ovo_fields.StringField(),
        "maintenance": ovo_fields.BooleanField(),
        "maintenance_reason": ovo_fields.StringField(),
        "extra": wfields.DictField(),
    }

    def accept(self, visitor):
        raise NotImplementedError()
