# -*- encoding: utf-8 -*-
# Copyright 2017 NEC Corporation
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

from watcher.decision_engine.model.element import storage_resource
from watcher.objects import base
from watcher.objects import fields as wfields


class VolumeState(enum.Enum):
    # https://docs.openstack.org/api-ref/block-storage/v3/#volumes-volumes

    CREATING = 'creating'
    AVAILABLE = 'available'
    ATTACHING = 'attaching'
    IN_USE = 'in-use'
    DELETING = 'deleting'
    ERROR = 'error'
    ERROR_DELETING = 'error_deleting'
    BACKING_UP = 'backing-up'
    RESTORING_BACKUP = 'restoring-backup'
    ERROR_RESTORING = 'error_restoring'
    ERROR_EXTENDING = 'error_extending'


@base.WatcherObjectRegistry.register_if(False)
class Volume(storage_resource.StorageResource):

    fields = {
        "size": wfields.NonNegativeIntegerField(),
        "status": wfields.StringField(default=VolumeState.AVAILABLE.value),
        "attachments": wfields.FlexibleListOfDictField(),
        "name": wfields.StringField(),
        "multiattach": wfields.BooleanField(),
        "snapshot_id": wfields.UUIDField(nullable=True),
        "project_id": wfields.UUIDField(),
        "metadata": wfields.JsonField(),
        "bootable": wfields.BooleanField()
    }

    def accept(self, visitor):
        raise NotImplementedError()
