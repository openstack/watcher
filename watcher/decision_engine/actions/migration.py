# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
#

from enum import Enum

from watcher.decision_engine.actions.base import BaseAction


class MigrationType(Enum):
    # Total migration time and downtime depend on memory dirtying speed
    pre_copy = 0
    # Postcopy transfer a page only once reliability
    post_copy = 1


class Migrate(BaseAction):
    def __init__(self, vm, src_hypervisor, dest_hypervisor):
        """Request to migrate a virtual machine from a host to another
        :param vm: the virtual machine uuid to migrate
        :param src_hypervisor: uuid
        :param dest_hypervisor: uuid
        """
        super(Migrate, self).__init__()
        self._reserved_disk_iops = 0
        self._remaining_dirty_pages = 0
        self._vm = vm
        self._migration_type = MigrationType.pre_copy
        self._src_hypervisor = src_hypervisor
        self._dest_hypervisor = dest_hypervisor

    @property
    def migration_type(self):
        return self._migration_type

    @migration_type.setter
    def migration_type(self, type):
        self._migration_type = type

    @property
    def vm(self):
        return self._vm

    @property
    def src_hypervisor(self):
        return self._src_hypervisor

    @property
    def dest_hypervisor(self):
        return self._dest_hypervisor

    def __str__(self):
        return "Migrate {} from {} to {}".format(
            self.vm,
            self.src_hypervisor,
            self.dest_hypervisor)
