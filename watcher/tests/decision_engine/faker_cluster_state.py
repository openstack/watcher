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

import random

from watcher.decision_engine.framework.model.hypervisor import Hypervisor
from watcher.decision_engine.framework.model.model_root import ModelRoot
from watcher.decision_engine.framework.model.resource import Resource
from watcher.decision_engine.framework.model.resource import ResourceType
from watcher.decision_engine.framework.model.vm import VM
from watcher.metrics_engine.api.cluster_state_collector import \
    ClusterStateCollector


class FakerStateCollector(ClusterStateCollector):
    def __init__(self):
        pass

    def get_latest_state_cluster(self):
        return self.generate_scenario_1()

    def generate_random(self, count_nodes, number_of_vm_per_node):
        vms = []

        current_state_cluster = ModelRoot()
        # number of nodes
        count_node = count_nodes
        # number max of vm per hypervisor
        node_count_vm = number_of_vm_per_node
        # total number of virtual machine
        count_vm = (count_node * node_count_vm)

        # define ressouce ( CPU, MEM disk, ... )
        mem = Resource(ResourceType.memory)
        # 2199.954 Mhz
        num_cores = Resource(ResourceType.cpu_cores)
        disk = Resource(ResourceType.disk)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_" + str(i)
            hypervisor = Hypervisor()
            hypervisor.uuid = node_uuid
            mem.set_capacity(hypervisor, 132)
            disk.set_capacity(hypervisor, 250)
            num_cores.set_capacity(hypervisor, 40)
            # print("create "+str(hypervisor))
            current_state_cluster.add_hypervisor(hypervisor)

        for i in range(0, count_vm):
            vm_uuid = "VM_" + str(i)
            vm = VM()
            vm.uuid = vm_uuid
            # print("create "+str(vm))
            mem.set_capacity(vm, 8)
            disk.set_capacity(vm, 10)
            num_cores.set_capacity(vm, 10)
            vms.append(vm)
            current_state_cluster.add_vm(vm)
        j = 0
        for node_id in current_state_cluster.get_all_hypervisors():
            for i in range(0, random.randint(0, node_count_vm)):
                # todo(jed) check if enough capacity
                current_state_cluster.get_mapping().map(
                    current_state_cluster.get_hypervisor_from_id(node_id),
                    vms[j])
                j += 1
        return current_state_cluster

    def generate_scenario_1(self):
        vms = []

        current_state_cluster = ModelRoot()
        # number of nodes
        count_node = 5
        # number max of vm per node
        node_count_vm = 7
        # total number of virtual machine
        count_vm = (count_node * node_count_vm)

        # define ressouce ( CPU, MEM disk, ... )
        mem = Resource(ResourceType.memory)
        # 2199.954 Mhz
        num_cores = Resource(ResourceType.cpu_cores)
        disk = Resource(ResourceType.disk)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_" + str(i)
            node = Hypervisor()
            node.uuid = node_uuid

            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            # print("create "+str(node))
            current_state_cluster.add_hypervisor(node)

        for i in range(0, count_vm):
            vm_uuid = "VM_" + str(i)
            vm = VM()
            vm.uuid = vm_uuid
            # print("create "+str(vm))
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

    def generate_scenario_2(self):
        current_state_cluster = ModelRoot()
        # number of nodes
        count_node = 5

        # define ressouce ( CPU, MEM disk, ... )
        mem = Resource(ResourceType.memory)
        # 2199.954 Mhz
        num_cores = Resource(ResourceType.cpu_cores)
        disk = Resource(ResourceType.disk)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_" + str(i)
            node = Hypervisor()
            node.uuid = node_uuid
            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            # print("create "+str(node))
            current_state_cluster.add_hypervisor(node)
        return current_state_cluster

    def map(self, model, h_id, vm_id):
        model.get_mapping().map(
            model.get_hypervisor_from_id(h_id),
            model.get_vm_from_id(vm_id))

    def generate_scenario_3(self):
        vms = []

        current_state_cluster = ModelRoot()
        # number of nodes
        count_node = 10
        # number max of vm per node
        node_count_vm = 7
        # total number of virtual machine
        count_vm = (count_node * node_count_vm)

        # define ressouce ( CPU, MEM disk, ... )
        mem = Resource(ResourceType.memory)
        # 2199.954 Mhz
        num_cores = Resource(ResourceType.cpu_cores)
        disk = Resource(ResourceType.disk)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_" + str(i)
            node = Hypervisor()
            node.uuid = node_uuid
            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            # print("create "+str(node))
            current_state_cluster.add_hypervisor(node)

        for i in range(0, count_vm):
            vm_uuid = "VM_" + str(i)
            vm = VM()
            vm.uuid = vm_uuid
            # print("create "+str(vm))
            mem.set_capacity(vm, 10)
            disk.set_capacity(vm, 25)
            num_cores.set_capacity(vm, 16)
            vms.append(vm)
            current_state_cluster.add_vm(vm)
        indice = 0
        for j in range(0, 2):
            node_uuid = "Node_" + str(j)
            for i in range(indice, 3):
                vm_uuid = "VM_" + str(i)
                self.map(current_state_cluster, node_uuid, vm_uuid)

        for j in range(2, 5):
            node_uuid = "Node_" + str(j)
            for i in range(indice, 4):
                vm_uuid = "VM_" + str(i)
                self.map(current_state_cluster, node_uuid, vm_uuid)

        for j in range(5, 10):
            node_uuid = "Node_" + str(j)
            for i in range(indice, 4):
                vm_uuid = "VM_" + str(i)
                self.map(current_state_cluster, node_uuid, vm_uuid)

        return current_state_cluster

    def generate_scenario_4_with_2_hypervisors(self):
        vms = []

        current_state_cluster = ModelRoot()
        # number of nodes
        count_node = 2
        # number max of vm per node
        node_count_vm = 1
        # total number of virtual machine
        count_vm = (count_node * node_count_vm)

        # define ressouce ( CPU, MEM disk, ... )
        mem = Resource(ResourceType.memory)
        # 2199.954 Mhz
        num_cores = Resource(ResourceType.cpu_cores)
        disk = Resource(ResourceType.disk)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_" + str(i)
            node = Hypervisor()
            node.uuid = node_uuid

            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            # print("create "+str(node))
            current_state_cluster.add_hypervisor(node)

        for i in range(0, count_vm):
            vm_uuid = "VM_" + str(i)
            vm = VM()
            vm.uuid = vm_uuid
            # print("create "+str(vm))
            mem.set_capacity(vm, 2)
            disk.set_capacity(vm, 20)
            num_cores.set_capacity(vm, 10)
            vms.append(vm)
            current_state_cluster.add_vm(vm)

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_0"),
            current_state_cluster.get_vm_from_id("VM_0"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_hypervisor_from_id("Node_1"),
            current_state_cluster.get_vm_from_id("VM_1"))

        return current_state_cluster

    def generate_scenario_5_with_1_hypervisor_no_vm(self):
        current_state_cluster = ModelRoot()
        # number of nodes
        count_node = 1

        # define ressouce ( CPU, MEM disk, ... )
        mem = Resource(ResourceType.memory)
        # 2199.954 Mhz
        num_cores = Resource(ResourceType.cpu_cores)
        disk = Resource(ResourceType.disk)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)

        for i in range(0, count_node):
            node_uuid = "Node_" + str(i)
            node = Hypervisor()
            node.uuid = node_uuid

            mem.set_capacity(node, 1)
            disk.set_capacity(node, 1)
            num_cores.set_capacity(node, 1)
            # print("create "+str(node))
            current_state_cluster.add_hypervisor(node)

        return current_state_cluster
