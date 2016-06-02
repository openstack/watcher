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
from watcher.decision_engine.model import hypervisor
from watcher.decision_engine.model import model_root as modelroot
from watcher.decision_engine.model import resource
from watcher.decision_engine.model import vm as modelvm
from watcher.metrics_engine.cluster_model_collector import base


class FakerModelCollector(base.BaseClusterModelCollector):
    def __init__(self):
        pass

    def get_latest_cluster_data_model(self):
        return self.generate_scenario_1()

    def generate_scenario_1(self):
        vms = []

        current_state_cluster = modelroot.ModelRoot()
        # number of nodes
        count_node = 5
        # number max of vm per node
        node_count_vm = 7
        # total number of virtual machine
        count_vm = (count_node * node_count_vm)

        # define ressouce ( CPU, MEM disk, ... )
        mem = resource.Resource(resource.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = resource.Resource(resource.ResourceType.cpu_cores)
        disk = resource.Resource(resource.ResourceType.disk)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_{0}".format(i)
            node = hypervisor.Hypervisor()
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(i)

            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            current_state_cluster.add_hypervisor(node)

        for i in range(0, count_vm):
            vm_uuid = "VM_{0}".format(i)
            vm = modelvm.VM()
            vm.uuid = vm_uuid
            mem.set_capacity(vm, 2)
            disk.set_capacity(vm, 20)
            num_cores.set_capacity(vm, 10)
            vms.append(vm)
            current_state_cluster.add_vm(vm)

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_0"),
            current_state_cluster.get_vm_from_id("VM_0"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_0"),
            current_state_cluster.get_vm_from_id("VM_1"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_1"),
            current_state_cluster.get_vm_from_id("VM_2"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_2"),
            current_state_cluster.get_vm_from_id("VM_3"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_2"),
            current_state_cluster.get_vm_from_id("VM_4"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_2"),
            current_state_cluster.get_vm_from_id("VM_5"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_3"),
            current_state_cluster.get_vm_from_id("VM_6"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_4"),
            current_state_cluster.get_vm_from_id("VM_7"))

        return current_state_cluster

    def map(self, model, h_id, vm_id):
        model.get_mapping().map(
            model.get_hypervisor_from_id(h_id),
            model.get_vm_from_id(vm_id))

    def generate_scenario_3_with_2_hypervisors(self):
        vms = []

        root = modelroot.ModelRoot()
        # number of nodes
        count_node = 2

        # define ressouce ( CPU, MEM disk, ... )
        mem = resource.Resource(resource.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = resource.Resource(resource.ResourceType.cpu_cores)
        disk = resource.Resource(resource.ResourceType.disk)

        root.create_resource(mem)
        root.create_resource(num_cores)
        root.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_{0}".format(i)
            node = hypervisor.Hypervisor()
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(i)

            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            root.add_hypervisor(node)

        vm1 = modelvm.VM()
        vm1.uuid = "73b09e16-35b7-4922-804e-e8f5d9b740fc"
        mem.set_capacity(vm1, 2)
        disk.set_capacity(vm1, 20)
        num_cores.set_capacity(vm1, 10)
        vms.append(vm1)
        root.add_vm(vm1)

        vm2 = modelvm.VM()
        vm2.uuid = "a4cab39b-9828-413a-bf88-f76921bf1517"
        mem.set_capacity(vm2, 2)
        disk.set_capacity(vm2, 20)
        num_cores.set_capacity(vm2, 10)
        vms.append(vm2)
        root.add_vm(vm2)

        root.get_mapping().map(root.get_hypervisor_from_id("Node_0"),
                               root.get_vm_from_id(str(vm1.uuid)))

        root.get_mapping().map(root.get_hypervisor_from_id("Node_1"),
                               root.get_vm_from_id(str(vm2.uuid)))

        return root

    def generate_scenario_4_with_1_hypervisor_no_vm(self):
        current_state_cluster = modelroot.ModelRoot()
        # number of nodes
        count_node = 1

        # define ressouce ( CPU, MEM disk, ... )
        mem = resource.Resource(resource.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = resource.Resource(resource.ResourceType.cpu_cores)
        disk = resource.Resource(resource.ResourceType.disk)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_{0}".format(i)
            node = hypervisor.Hypervisor()
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(i)

            mem.set_capacity(node, 1)
            disk.set_capacity(node, 1)
            num_cores.set_capacity(node, 1)
            current_state_cluster.add_hypervisor(node)

        return current_state_cluster

    def generate_scenario_5_with_vm_disk_0(self):
        vms = []
        current_state_cluster = modelroot.ModelRoot()
        # number of nodes
        count_node = 1
        # number of vms
        count_vm = 1

        # define ressouce ( CPU, MEM disk, ... )
        mem = resource.Resource(resource.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = resource.Resource(resource.ResourceType.cpu_cores)
        disk = resource.Resource(resource.ResourceType.disk)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_{0}".format(i)
            node = hypervisor.Hypervisor()
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(i)

            mem.set_capacity(node, 4)
            disk.set_capacity(node, 4)
            num_cores.set_capacity(node, 4)
            current_state_cluster.add_hypervisor(node)

        for i in range(0, count_vm):
            vm_uuid = "VM_{0}".format(i)
            vm = modelvm.VM()
            vm.uuid = vm_uuid
            mem.set_capacity(vm, 2)
            disk.set_capacity(vm, 0)
            num_cores.set_capacity(vm, 4)
            vms.append(vm)
            current_state_cluster.add_vm(vm)

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_0"),
            current_state_cluster.get_vm_from_id("VM_0"))

        return current_state_cluster

    def generate_scenario_6_with_2_hypervisors(self):
        vms = []
        root = modelroot.ModelRoot()
        # number of nodes
        count_node = 2

        # define ressouce ( CPU, MEM disk, ... )
        mem = resource.Resource(resource.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = resource.Resource(resource.ResourceType.cpu_cores)
        disk = resource.Resource(resource.ResourceType.disk)

        root.create_resource(mem)
        root.create_resource(num_cores)
        root.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_{0}".format(i)
            node = hypervisor.Hypervisor()
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(i)

            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            root.add_hypervisor(node)

        vm1 = modelvm.VM()
        vm1.uuid = "VM_1"
        mem.set_capacity(vm1, 2)
        disk.set_capacity(vm1, 20)
        num_cores.set_capacity(vm1, 10)
        vms.append(vm1)
        root.add_vm(vm1)

        vm11 = modelvm.VM()
        vm11.uuid = "73b09e16-35b7-4922-804e-e8f5d9b740fc"
        mem.set_capacity(vm11, 2)
        disk.set_capacity(vm11, 20)
        num_cores.set_capacity(vm11, 10)
        vms.append(vm11)
        root.add_vm(vm11)

        vm2 = modelvm.VM()
        vm2.uuid = "VM_3"
        mem.set_capacity(vm2, 2)
        disk.set_capacity(vm2, 20)
        num_cores.set_capacity(vm2, 10)
        vms.append(vm2)
        root.add_vm(vm2)

        vm21 = modelvm.VM()
        vm21.uuid = "VM_4"
        mem.set_capacity(vm21, 2)
        disk.set_capacity(vm21, 20)
        num_cores.set_capacity(vm21, 10)
        vms.append(vm21)
        root.add_vm(vm21)

        root.get_mapping().map(root.get_hypervisor_from_id("Node_0"),
                               root.get_vm_from_id(str(vm1.uuid)))
        root.get_mapping().map(root.get_hypervisor_from_id("Node_0"),
                               root.get_vm_from_id(str(vm11.uuid)))

        root.get_mapping().map(root.get_hypervisor_from_id("Node_1"),
                               root.get_vm_from_id(str(vm2.uuid)))
        root.get_mapping().map(root.get_hypervisor_from_id("Node_1"),
                               root.get_vm_from_id(str(vm21.uuid)))
        return root

    def generate_scenario_7_with_2_hypervisors(self):
        vms = []
        root = modelroot.ModelRoot()
        # number of nodes
        count_node = 2

        # define ressouce ( CPU, MEM disk, ... )
        mem = resource.Resource(resource.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = resource.Resource(resource.ResourceType.cpu_cores)
        disk = resource.Resource(resource.ResourceType.disk)

        root.create_resource(mem)
        root.create_resource(num_cores)
        root.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_{0}".format(i)
            node = hypervisor.Hypervisor()
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(i)

            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            num_cores.set_capacity(node, 50)
            root.add_hypervisor(node)

        vm1 = modelvm.VM()
        vm1.uuid = "cae81432-1631-4d4e-b29c-6f3acdcde906"
        mem.set_capacity(vm1, 2)
        disk.set_capacity(vm1, 20)
        num_cores.set_capacity(vm1, 15)
        vms.append(vm1)
        root.add_vm(vm1)

        vm11 = modelvm.VM()
        vm11.uuid = "73b09e16-35b7-4922-804e-e8f5d9b740fc"
        mem.set_capacity(vm11, 2)
        disk.set_capacity(vm11, 20)
        num_cores.set_capacity(vm11, 10)
        vms.append(vm11)
        root.add_vm(vm11)

        vm2 = modelvm.VM()
        vm2.uuid = "VM_3"
        mem.set_capacity(vm2, 2)
        disk.set_capacity(vm2, 20)
        num_cores.set_capacity(vm2, 10)
        vms.append(vm2)
        root.add_vm(vm2)

        vm21 = modelvm.VM()
        vm21.uuid = "VM_4"
        mem.set_capacity(vm21, 2)
        disk.set_capacity(vm21, 20)
        num_cores.set_capacity(vm21, 10)
        vms.append(vm21)
        root.add_vm(vm21)

        root.get_mapping().map(root.get_hypervisor_from_id("Node_0"),
                               root.get_vm_from_id(str(vm1.uuid)))
        root.get_mapping().map(root.get_hypervisor_from_id("Node_0"),
                               root.get_vm_from_id(str(vm11.uuid)))

        root.get_mapping().map(root.get_hypervisor_from_id("Node_1"),
                               root.get_vm_from_id(str(vm2.uuid)))
        root.get_mapping().map(root.get_hypervisor_from_id("Node_1"),
                               root.get_vm_from_id(str(vm21.uuid)))
        return root
