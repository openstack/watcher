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

from oslo_log import log

from watcher.common import nova_helper
from watcher.decision_engine.model.collector import base
from watcher.decision_engine.model import hypervisor as obj_hypervisor
from watcher.decision_engine.model import model_root
from watcher.decision_engine.model import resource
from watcher.decision_engine.model import vm as obj_vm

LOG = log.getLogger(__name__)


class NovaClusterDataModelCollector(base.BaseClusterDataModelCollector):
    """nova

    *Description*

    This Nova cluster data model collector creates an in-memory representation
    of the resources exposed by the compute service.

    *Spec URL*

    <None>
    """

    def __init__(self, config, osc=None):
        super(NovaClusterDataModelCollector, self).__init__(config, osc)
        self.wrapper = nova_helper.NovaHelper(osc=self.osc)

    def execute(self):
        """Build the compute cluster data model"""
        LOG.debug("Building latest Nova cluster data model")

        model = model_root.ModelRoot()
        mem = resource.Resource(resource.ResourceType.memory)
        num_cores = resource.Resource(resource.ResourceType.cpu_cores)
        disk = resource.Resource(resource.ResourceType.disk)
        disk_capacity = resource.Resource(resource.ResourceType.disk_capacity)
        model.create_resource(mem)
        model.create_resource(num_cores)
        model.create_resource(disk)
        model.create_resource(disk_capacity)

        flavor_cache = {}
        hypervisors = self.wrapper.get_hypervisors_list()
        for h in hypervisors:
            service = self.wrapper.nova.services.find(id=h.service['id'])
            # create hypervisor in cluster_model_collector
            hypervisor = obj_hypervisor.Hypervisor()
            hypervisor.uuid = service.host
            hypervisor.hostname = h.hypervisor_hostname
            # set capacity
            mem.set_capacity(hypervisor, h.memory_mb)
            disk.set_capacity(hypervisor, h.free_disk_gb)
            disk_capacity.set_capacity(hypervisor, h.local_gb)
            num_cores.set_capacity(hypervisor, h.vcpus)
            hypervisor.state = h.state
            hypervisor.status = h.status
            model.add_hypervisor(hypervisor)
            vms = self.wrapper.get_vms_by_hypervisor(str(service.host))
            for v in vms:
                # create VM in cluster_model_collector
                vm = obj_vm.VM()
                vm.uuid = v.id
                # nova/nova/compute/vm_states.py
                vm.state = getattr(v, 'OS-EXT-STS:vm_state')

                # set capacity
                self.wrapper.get_flavor_instance(v, flavor_cache)
                mem.set_capacity(vm, v.flavor['ram'])
                disk.set_capacity(vm, v.flavor['disk'])
                num_cores.set_capacity(vm, v.flavor['vcpus'])

                model.get_mapping().map(hypervisor, vm)
                model.add_vm(vm)
        return model
