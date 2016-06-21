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


class VMState(enum.Enum):
    ACTIVE = 'active'  # VM is running
    BUILDING = 'building'  # VM only exists in DB
    PAUSED = 'paused'
    SUSPENDED = 'suspended'  # VM is suspended to disk.
    STOPPED = 'stopped'  # VM is powered off, the disk image is still there.
    RESCUED = 'rescued'  # A rescue image is running with the original VM image
    # attached.
    RESIZED = 'resized'  # a VM with the new size is active.

    SOFT_DELETED = 'soft-delete'
    # still available to restore.
    DELETED = 'deleted'  # VM is permanently deleted.

    ERROR = 'error'
