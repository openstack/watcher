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
from oslo_log import log
import threading

LOG = log.getLogger(__name__)


class Mapping(object):
    def __init__(self, model):
        self.model = model
        self._mapping_hypervisors = {}
        self.mapping_vm = {}
        self.lock = threading.Lock()

    def map(self, hypervisor, vm):
        """Select the hypervisor where the instance are launched

        :param hypervisor: the hypervisor
        :param vm: the virtual machine or instance
        """

        try:
            self.lock.acquire()

            # init first
            if hypervisor.uuid not in self._mapping_hypervisors.keys():
                self._mapping_hypervisors[hypervisor.uuid] = []

            # map node => vms
            self._mapping_hypervisors[hypervisor.uuid].append(
                vm.uuid)

            # map vm => node
            self.mapping_vm[vm.uuid] = hypervisor.uuid

        finally:
            self.lock.release()

    def unmap(self, hypervisor, vm):
        """Remove the instance from the hypervisor

        :param hypervisor: the hypervisor
        :param vm: the virtual machine or instance
        """

        self.unmap_from_id(hypervisor.uuid, vm.uuid)

    def unmap_from_id(self, node_uuid, vm_uuid):
        """Remove the instance (by id) from the hypervisor (by id)

        :rtype : object
        """

        try:
            self.lock.acquire()
            if str(node_uuid) in self._mapping_hypervisors:
                self._mapping_hypervisors[str(node_uuid)].remove(str(vm_uuid))
                # remove vm
                self.mapping_vm.pop(vm_uuid)
            else:
                LOG.warning(
                    "trying to delete the virtual machine {0}  but it was not "
                    "found on hypervisor {1}".format(
                        vm_uuid, node_uuid))
        finally:
            self.lock.release()

    def get_mapping(self):
        return self._mapping_hypervisors

    def get_mapping_vm(self):
        return self.mapping_vm

    def get_node_from_vm(self, vm):
        return self.get_node_from_vm_id(vm.uuid)

    def get_node_from_vm_id(self, vm_uuid):
        """Getting host information from the guest VM

        :param vm: the uuid of the instance
        :return: hypervisor
        """

        return self.model.get_hypervisor_from_id(
            self.get_mapping_vm()[str(vm_uuid)])

    def get_node_vms(self, hypervisor):
        """Get the list of instances running on the hypervisor

        :param hypervisor:
        :return:
        """
        return self.get_node_vms_from_id(hypervisor.uuid)

    def get_node_vms_from_id(self, node_uuid):
        if str(node_uuid) in self._mapping_hypervisors.keys():
            return self._mapping_hypervisors[str(node_uuid)]
        else:
            # empty
            return []

    def migrate_vm(self, vm, src_hypervisor, dest_hypervisor):
        """Migrate single instance from src_hypervisor to dest_hypervisor

        :param vm:
        :param src_hypervisor:
        :param dest_hypervisor:
        :return:
        """

        if src_hypervisor == dest_hypervisor:
            return False
        # unmap
        self.unmap(src_hypervisor, vm)
        # map
        self.map(dest_hypervisor, vm)
        return True
