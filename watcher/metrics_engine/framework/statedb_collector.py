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


from oslo_config import cfg
from watcher.decision_engine.framework.model.hypervisor import Hypervisor
from watcher.decision_engine.framework.model.model_root import ModelRoot
from watcher.decision_engine.framework.model.resource import Resource
from watcher.decision_engine.framework.model.resource import ResourceType
from watcher.decision_engine.framework.model.vm import VM
from watcher.metrics_engine.api.cluster_state_collector import \
    ClusterStateCollector
from watcher.openstack.common import log

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class NovaCollector(ClusterStateCollector):
    def __init__(self, wrapper):
        self.wrapper = wrapper

    def get_latest_state_cluster(self):

        cluster = ModelRoot()
        mem = Resource(ResourceType.memory)
        num_cores = Resource(ResourceType.cpu_cores)
        disk = Resource(ResourceType.disk)
        cluster.create_resource(mem)
        cluster.create_resource(num_cores)
        cluster.create_resource(disk)

        flavor_cache = {}
        hypervisors = self.wrapper.get_hypervisors_list()
        for h in hypervisors:
            service = self.wrapper.nova.services.find(id=h.service['id'])
            # create hypervisor in stateDB
            hypervisor = Hypervisor()
            hypervisor.uuid = service.host
            # set capacity
            mem.set_capacity(hypervisor, h.memory_mb)
            disk.set_capacity(hypervisor, h.free_disk_gb)
            num_cores.set_capacity(hypervisor, h.vcpus)
            hypervisor.state = h.state
            hypervisor.status = h.status
            cluster.add_hypervisor(hypervisor)
            vms = self.wrapper.get_vms_by_hypervisor(str(service.host))
            for v in vms:
                # create VM in stateDB
                vm = VM()
                vm.uuid = v.id
                # nova/nova/compute/vm_states.py
                vm.state = getattr(v, 'OS-EXT-STS:vm_state')

                # set capacity
                self.wrapper.get_flavor_instance(v, flavor_cache)
                mem.set_capacity(vm, v.flavor['ram'])
                disk.set_capacity(vm, v.flavor['disk'])
                num_cores.set_capacity(vm, v.flavor['vcpus'])
                # print(dir(v))
                cluster.get_mapping().map(hypervisor, vm)
                cluster.add_vm(vm)
        return cluster
