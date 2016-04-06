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
from watcher._i18n import _
from watcher.common import exception
from watcher.decision_engine.model import hypervisor
from watcher.decision_engine.model import mapping
from watcher.decision_engine.model import vm


class ModelRoot(object):
    def __init__(self):
        self._hypervisors = {}
        self._vms = {}
        self.mapping = mapping.Mapping(self)
        self.resource = {}

    def assert_hypervisor(self, obj):
        if not isinstance(obj, hypervisor.Hypervisor):
            raise exception.IllegalArgumentException(
                message=_("'obj' argument type is not valid"))

    def assert_vm(self, obj):
        if not isinstance(obj, vm.VM):
            raise exception.IllegalArgumentException(
                message=_("'obj' argument type is not valid"))

    def add_hypervisor(self, hypervisor):
        self.assert_hypervisor(hypervisor)
        self._hypervisors[hypervisor.uuid] = hypervisor

    def remove_hypervisor(self, hypervisor):
        self.assert_hypervisor(hypervisor)
        if str(hypervisor.uuid) not in self._hypervisors.keys():
            raise exception.HypervisorNotFound(hypervisor.uuid)
        else:
            del self._hypervisors[hypervisor.uuid]

    def add_vm(self, vm):
        self.assert_vm(vm)
        self._vms[vm.uuid] = vm

    def get_all_hypervisors(self):
        return self._hypervisors

    def get_hypervisor_from_id(self, hypervisor_uuid):
        if str(hypervisor_uuid) not in self._hypervisors.keys():
            raise exception.HypervisorNotFound(hypervisor_uuid)
        return self._hypervisors[str(hypervisor_uuid)]

    def get_vm_from_id(self, uuid):
        if str(uuid) not in self._vms.keys():
            raise exception.InstanceNotFound(name=uuid)
        return self._vms[str(uuid)]

    def get_all_vms(self):
        return self._vms

    def get_mapping(self):
        return self.mapping

    def create_resource(self, r):
        self.resource[str(r.name)] = r

    def get_resource_from_id(self, id):
        return self.resource[str(id)]
