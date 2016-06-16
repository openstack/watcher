# -*- encoding: utf-8 -*-
#
# Authors: Vojtech CIMA <cima@zhaw.ch>
#          Bruno GRAZIOLI <gaea@zhaw.ch>
#          Sean MURPHY <murp@zhaw.ch>
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
from watcher.decision_engine.model import hypervisor
from watcher.decision_engine.model import model_root as modelroot
from watcher.decision_engine.model import resource
from watcher.decision_engine.model import vm as modelvm
from watcher.decision_engine.model import vm_state
from watcher.metrics_engine.cluster_model_collector import base


class FakerModelCollector(base.BaseClusterModelCollector):

    def __init__(self):
        pass

    def get_latest_cluster_data_model(self):
        return self.generate_scenario_1()

    def generate_scenario_1(self):
        """Simulates cluster with 2 hypervisors and 2 VMs using 1:1 mapping"""

        current_state_cluster = modelroot.ModelRoot()
        count_node = 2
        count_vm = 2

        mem = resource.Resource(resource.ResourceType.memory)
        num_cores = resource.Resource(resource.ResourceType.cpu_cores)
        disk = resource.Resource(resource.ResourceType.disk)
        disk_capacity =\
            resource.Resource(resource.ResourceType.disk_capacity)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)
        current_state_cluster.create_resource(disk_capacity)

        for i in range(0, count_node):
            node_uuid = "Node_{0}".format(i)
            node = hypervisor.Hypervisor()
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(i)
            node.state = 'enabled'

            mem.set_capacity(node, 64)
            disk_capacity.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            current_state_cluster.add_hypervisor(node)

        for i in range(0, count_vm):
            vm_uuid = "VM_{0}".format(i)
            vm = modelvm.VM()
            vm.uuid = vm_uuid
            vm.state = vm_state.VMState.ACTIVE
            mem.set_capacity(vm, 2)
            disk.set_capacity(vm, 20)
            num_cores.set_capacity(vm, 10)
            current_state_cluster.add_vm(vm)

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_0"),
            current_state_cluster.get_vm_from_id("VM_0"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_1"),
            current_state_cluster.get_vm_from_id("VM_1"))

        return current_state_cluster

    def generate_scenario_2(self):
        """Simulates a cluster

        With 4 hypervisors and  6 VMs all mapped to one hypervisor
        """

        current_state_cluster = modelroot.ModelRoot()
        count_node = 4
        count_vm = 6

        mem = resource.Resource(resource.ResourceType.memory)
        num_cores = resource.Resource(resource.ResourceType.cpu_cores)
        disk = resource.Resource(resource.ResourceType.disk)
        disk_capacity =\
            resource.Resource(resource.ResourceType.disk_capacity)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)
        current_state_cluster.create_resource(disk_capacity)

        for i in range(0, count_node):
            node_uuid = "Node_{0}".format(i)
            node = hypervisor.Hypervisor()
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(i)
            node.state = 'up'

            mem.set_capacity(node, 64)
            disk_capacity.set_capacity(node, 250)
            num_cores.set_capacity(node, 16)
            current_state_cluster.add_hypervisor(node)

        for i in range(0, count_vm):
            vm_uuid = "VM_{0}".format(i)
            vm = modelvm.VM()
            vm.uuid = vm_uuid
            vm.state = vm_state.VMState.ACTIVE
            mem.set_capacity(vm, 2)
            disk.set_capacity(vm, 20)
            num_cores.set_capacity(vm, 10)
            current_state_cluster.add_vm(vm)

            current_state_cluster.get_mapping().map(
                current_state_cluster.get_hypervisor_from_id("Node_0"),
                current_state_cluster.get_vm_from_id("VM_%s" % str(i)))

        return current_state_cluster

    def generate_scenario_3(self):
        """Simulates a cluster

        With 4 hypervisors and 6 VMs all mapped to one hypervisor
        """

        current_state_cluster = modelroot.ModelRoot()
        count_node = 2
        count_vm = 4

        mem = resource.Resource(resource.ResourceType.memory)
        num_cores = resource.Resource(resource.ResourceType.cpu_cores)
        disk = resource.Resource(resource.ResourceType.disk)
        disk_capacity =\
            resource.Resource(resource.ResourceType.disk_capacity)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)
        current_state_cluster.create_resource(disk_capacity)

        for i in range(0, count_node):
            node_uuid = "Node_{0}".format(i)
            node = hypervisor.Hypervisor()
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(i)
            node.state = 'up'

            mem.set_capacity(node, 64)
            disk_capacity.set_capacity(node, 250)
            num_cores.set_capacity(node, 10)
            current_state_cluster.add_hypervisor(node)

        for i in range(6, 6 + count_vm):
            vm_uuid = "VM_{0}".format(i)
            vm = modelvm.VM()
            vm.uuid = vm_uuid
            vm.state = vm_state.VMState.ACTIVE
            mem.set_capacity(vm, 2)
            disk.set_capacity(vm, 20)
            num_cores.set_capacity(vm, 2 ** (i-6))
            current_state_cluster.add_vm(vm)

            current_state_cluster.get_mapping().map(
                current_state_cluster.get_hypervisor_from_id("Node_0"),
                current_state_cluster.get_vm_from_id("VM_%s" % str(i)))

        return current_state_cluster


class FakeCeilometerMetrics(object):
    def __init__(self, model):
        self.model = model

    def mock_get_statistics(self, resource_id, meter_name, period=3600,
                            aggregate='avg'):
        if meter_name == "compute.node.cpu.percent":
            return self.get_hypervisor_cpu_util(resource_id)
        elif meter_name == "cpu_util":
            return self.get_vm_cpu_util(resource_id)
        elif meter_name == "memory.usage":
            return self.get_vm_ram_util(resource_id)
        elif meter_name == "disk.root.size":
            return self.get_vm_disk_root_size(resource_id)

    def get_hypervisor_cpu_util(self, r_id):
        """Calculates hypervisor utilization dynamicaly.

        Hypervisor CPU utilization should consider
        and corelate with actual VM-hypervisor mappings
        provided within a cluster model.
        Returns relative hypervisor CPU utilization <0, 100>.
        :param r_id: resource id
        """

        id = '%s_%s' % (r_id.split('_')[0], r_id.split('_')[1])
        vms = self.model.get_mapping().get_node_vms_from_id(id)
        util_sum = 0.0
        hypervisor_cpu_cores = self.model.get_resource_from_id(
            resource.ResourceType.cpu_cores).get_capacity_from_id(id)
        for vm_uuid in vms:
            vm_cpu_cores = self.model.get_resource_from_id(
                resource.ResourceType.cpu_cores).\
                get_capacity(self.model.get_vm_from_id(vm_uuid))
            total_cpu_util = vm_cpu_cores * self.get_vm_cpu_util(vm_uuid)
            util_sum += total_cpu_util / 100.0
        util_sum /= hypervisor_cpu_cores
        return util_sum * 100.0

    def get_vm_cpu_util(self, r_id):
        vm_cpu_util = dict()
        vm_cpu_util['VM_0'] = 10
        vm_cpu_util['VM_1'] = 30
        vm_cpu_util['VM_2'] = 60
        vm_cpu_util['VM_3'] = 20
        vm_cpu_util['VM_4'] = 40
        vm_cpu_util['VM_5'] = 50
        vm_cpu_util['VM_6'] = 100
        vm_cpu_util['VM_7'] = 100
        vm_cpu_util['VM_8'] = 100
        vm_cpu_util['VM_9'] = 100
        return vm_cpu_util[str(r_id)]

    def get_vm_ram_util(self, r_id):
        vm_ram_util = dict()
        vm_ram_util['VM_0'] = 1
        vm_ram_util['VM_1'] = 2
        vm_ram_util['VM_2'] = 4
        vm_ram_util['VM_3'] = 8
        vm_ram_util['VM_4'] = 3
        vm_ram_util['VM_5'] = 2
        vm_ram_util['VM_6'] = 1
        vm_ram_util['VM_7'] = 2
        vm_ram_util['VM_8'] = 4
        vm_ram_util['VM_9'] = 8
        return vm_ram_util[str(r_id)]

    def get_vm_disk_root_size(self, r_id):
        vm_disk_util = dict()
        vm_disk_util['VM_0'] = 10
        vm_disk_util['VM_1'] = 15
        vm_disk_util['VM_2'] = 30
        vm_disk_util['VM_3'] = 35
        vm_disk_util['VM_4'] = 20
        vm_disk_util['VM_5'] = 25
        vm_disk_util['VM_6'] = 25
        vm_disk_util['VM_7'] = 25
        vm_disk_util['VM_8'] = 25
        vm_disk_util['VM_9'] = 25
        return vm_disk_util[str(r_id)]
