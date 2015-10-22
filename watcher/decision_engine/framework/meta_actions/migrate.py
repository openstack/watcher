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

from watcher.decision_engine.api.strategy.meta_action import MetaAction


class MigrationType(Enum):
    # Total migration time and downtime depend on memory dirtying speed
    pre_copy = 0
    # Postcopy transfer a page only once reliability
    post_copy = 1


class Migrate(MetaAction):
    def __init__(self, vm, source_hypervisor, dest_hypervisor):
        MetaAction.__init__(self)
        """Request Migrate
        :param bandwidth the bandwidth reserved for the migration
        :param vm:       the virtual machine to migrate
        :param source_hypervisor:
        :param dest_hypervisor:
        :return:
        """
        self.bandwidth = 0
        self.reservedDiskIOPS = 0
        self.remainingDirtyPages = 0
        self.vm = vm
        self.migration_type = MigrationType.pre_copy
        self.source_hypervisor = source_hypervisor
        self.dest_hypervisor = dest_hypervisor

    def set_migration_type(self, type):
        self.migration_type = type

    def set_bandwidth(self, bw):
        """Set the bandwidth reserved for the migration

        :param bw: bandwidth
        """
        self.bandwidth = bw

    def get_bandwidth(self):
        return self.bandwidth

    def get_vm(self):
        return self.vm

    def get_source_hypervisor(self):
        return self.source_hypervisor

    def get_dest_hypervisor(self):
        return self.dest_hypervisor

    def __str__(self):
        return MetaAction.__str__(self) + " Migrate " + str(
            self.vm) + " from " + str(
            self.source_hypervisor) + " to " + str(self.dest_hypervisor)
