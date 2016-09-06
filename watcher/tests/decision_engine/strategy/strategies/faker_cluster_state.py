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

import mock

from watcher.decision_engine.model.collector import base
from watcher.decision_engine.model import element
from watcher.decision_engine.model import model_root as modelroot


class FakerModelCollector(base.BaseClusterDataModelCollector):

    def __init__(self, config=None, osc=None):
        if config is None:
            config = mock.Mock(period=777)
        super(FakerModelCollector, self).__init__(config)

    @property
    def notification_endpoints(self):
        return []

    def execute(self):
        return self._cluster_data_model or self.generate_scenario_1()

    def generate_scenario_1(self):
        instances = []

        current_state_cluster = modelroot.ModelRoot()
        # number of nodes
        node_count = 5
        # number max of instance per node
        node_instance_count = 7
        # total number of virtual machine
        instance_count = (node_count * node_instance_count)

        # define ressouce ( CPU, MEM disk, ... )
        mem = element.Resource(element.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = element.Resource(element.ResourceType.cpu_cores)
        disk = element.Resource(element.ResourceType.disk)
        disk_capacity = element.Resource(element.ResourceType.disk_capacity)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)
        current_state_cluster.create_resource(disk_capacity)

        for id_ in range(0, node_count):
            node_uuid = "Node_{0}".format(id_)
            node = element.ComputeNode(id_)
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(id_)

            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            disk_capacity.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            current_state_cluster.add_node(node)

        for i in range(0, instance_count):
            instance_uuid = "INSTANCE_{0}".format(i)
            instance = element.Instance()
            instance.uuid = instance_uuid
            mem.set_capacity(instance, 2)
            disk.set_capacity(instance, 20)
            disk_capacity.set_capacity(instance, 20)
            num_cores.set_capacity(instance, 10)
            instances.append(instance)
            current_state_cluster.add_instance(instance)

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_node_by_uuid("Node_0"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_0"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_node_by_uuid("Node_0"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_1"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_node_by_uuid("Node_1"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_2"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_node_by_uuid("Node_2"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_3"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_node_by_uuid("Node_2"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_4"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_node_by_uuid("Node_2"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_5"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_node_by_uuid("Node_3"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_6"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_node_by_uuid("Node_4"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_7"))

        return current_state_cluster

    def map(self, model, h_id, instance_id):
        model.get_mapping().map(
            model.get_node_by_uuid(h_id),
            model.get_instance_by_uuid(instance_id))

    def generate_scenario_3_with_2_nodes(self):
        instances = []

        root = modelroot.ModelRoot()
        # number of nodes
        node_count = 2

        # define ressouce ( CPU, MEM disk, ... )
        mem = element.Resource(element.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = element.Resource(element.ResourceType.cpu_cores)
        disk = element.Resource(element.ResourceType.disk)
        disk_capacity = element.Resource(element.ResourceType.disk_capacity)

        root.create_resource(mem)
        root.create_resource(num_cores)
        root.create_resource(disk)
        root.create_resource(disk_capacity)

        for id_ in range(0, node_count):
            node_uuid = "Node_{0}".format(id_)
            node = element.ComputeNode(id_)
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(id_)

            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            disk_capacity.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            root.add_node(node)

        instance1 = element.Instance()
        instance1.uuid = "73b09e16-35b7-4922-804e-e8f5d9b740fc"
        mem.set_capacity(instance1, 2)
        disk.set_capacity(instance1, 20)
        disk_capacity.set_capacity(instance1, 20)
        num_cores.set_capacity(instance1, 10)
        instances.append(instance1)
        root.add_instance(instance1)

        instance2 = element.Instance()
        instance2.uuid = "a4cab39b-9828-413a-bf88-f76921bf1517"
        mem.set_capacity(instance2, 2)
        disk.set_capacity(instance2, 20)
        disk_capacity.set_capacity(instance2, 20)
        num_cores.set_capacity(instance2, 10)
        instances.append(instance2)
        root.add_instance(instance2)

        root.get_mapping().map(root.get_node_by_uuid("Node_0"),
                               root.get_instance_by_uuid(str(instance1.uuid)))

        root.get_mapping().map(root.get_node_by_uuid("Node_1"),
                               root.get_instance_by_uuid(str(instance2.uuid)))

        return root

    def generate_scenario_4_with_1_node_no_instance(self):
        current_state_cluster = modelroot.ModelRoot()
        # number of nodes
        node_count = 1

        # define ressouce ( CPU, MEM disk, ... )
        mem = element.Resource(element.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = element.Resource(element.ResourceType.cpu_cores)
        disk = element.Resource(element.ResourceType.disk)
        disk_capacity = element.Resource(element.ResourceType.disk_capacity)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)
        current_state_cluster.create_resource(disk_capacity)

        for id_ in range(0, node_count):
            node_uuid = "Node_{0}".format(id_)
            node = element.ComputeNode(id_)
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(id_)

            mem.set_capacity(node, 1)
            disk.set_capacity(node, 1)
            disk_capacity.set_capacity(node, 1)
            num_cores.set_capacity(node, 1)
            current_state_cluster.add_node(node)

        return current_state_cluster

    def generate_scenario_5_with_instance_disk_0(self):
        instances = []
        current_state_cluster = modelroot.ModelRoot()
        # number of nodes
        node_count = 1
        # number of instances
        instance_count = 1

        # define ressouce ( CPU, MEM disk, ... )
        mem = element.Resource(element.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = element.Resource(element.ResourceType.cpu_cores)
        disk = element.Resource(element.ResourceType.disk)
        disk_capacity = element.Resource(element.ResourceType.disk_capacity)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)
        current_state_cluster.create_resource(disk_capacity)

        for id_ in range(0, node_count):
            node_uuid = "Node_{0}".format(id_)
            node = element.ComputeNode(id_)
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(id_)

            mem.set_capacity(node, 4)
            disk.set_capacity(node, 4)
            disk_capacity.set_capacity(node, 4)
            num_cores.set_capacity(node, 4)
            current_state_cluster.add_node(node)

        for i in range(0, instance_count):
            instance_uuid = "INSTANCE_{0}".format(i)
            instance = element.Instance()
            instance.uuid = instance_uuid
            mem.set_capacity(instance, 2)
            disk.set_capacity(instance, 0)
            disk_capacity.set_capacity(instance, 0)
            num_cores.set_capacity(instance, 4)
            instances.append(instance)
            current_state_cluster.add_instance(instance)

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_node_by_uuid("Node_0"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_0"))

        return current_state_cluster

    def generate_scenario_6_with_2_nodes(self):
        instances = []
        root = modelroot.ModelRoot()
        # number of nodes
        node_count = 2

        # define ressouce ( CPU, MEM disk, ... )
        mem = element.Resource(element.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = element.Resource(element.ResourceType.cpu_cores)
        disk = element.Resource(element.ResourceType.disk)
        disk_capacity = element.Resource(element.ResourceType.disk_capacity)

        root.create_resource(mem)
        root.create_resource(num_cores)
        root.create_resource(disk)
        root.create_resource(disk_capacity)

        for id_ in range(0, node_count):
            node_uuid = "Node_{0}".format(id_)
            node = element.ComputeNode(id_)
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(id_)

            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            disk_capacity.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            root.add_node(node)

        instance1 = element.Instance()
        instance1.uuid = "INSTANCE_1"
        mem.set_capacity(instance1, 2)
        disk.set_capacity(instance1, 20)
        disk_capacity.set_capacity(instance1, 20)
        num_cores.set_capacity(instance1, 10)
        instances.append(instance1)
        root.add_instance(instance1)

        instance11 = element.Instance()
        instance11.uuid = "73b09e16-35b7-4922-804e-e8f5d9b740fc"
        mem.set_capacity(instance11, 2)
        disk.set_capacity(instance11, 20)
        disk_capacity.set_capacity(instance11, 20)
        num_cores.set_capacity(instance11, 10)
        instances.append(instance11)
        root.add_instance(instance11)

        instance2 = element.Instance()
        instance2.uuid = "INSTANCE_3"
        mem.set_capacity(instance2, 2)
        disk.set_capacity(instance2, 20)
        disk_capacity.set_capacity(instance2, 20)
        num_cores.set_capacity(instance2, 10)
        instances.append(instance2)
        root.add_instance(instance2)

        instance21 = element.Instance()
        instance21.uuid = "INSTANCE_4"
        mem.set_capacity(instance21, 2)
        disk.set_capacity(instance21, 20)
        disk_capacity.set_capacity(instance21, 20)
        num_cores.set_capacity(instance21, 10)
        instances.append(instance21)
        root.add_instance(instance21)

        root.get_mapping().map(root.get_node_by_uuid("Node_0"),
                               root.get_instance_by_uuid(str(instance1.uuid)))
        root.get_mapping().map(root.get_node_by_uuid("Node_0"),
                               root.get_instance_by_uuid(str(instance11.uuid)))

        root.get_mapping().map(root.get_node_by_uuid("Node_1"),
                               root.get_instance_by_uuid(str(instance2.uuid)))
        root.get_mapping().map(root.get_node_by_uuid("Node_1"),
                               root.get_instance_by_uuid(str(instance21.uuid)))
        return root

    def generate_scenario_7_with_2_nodes(self):
        instances = []
        root = modelroot.ModelRoot()
        # number of nodes
        count_node = 2

        # define ressouce ( CPU, MEM disk, ... )
        mem = element.Resource(element.ResourceType.memory)
        # 2199.954 Mhz
        num_cores = element.Resource(element.ResourceType.cpu_cores)
        disk = element.Resource(element.ResourceType.disk)
        disk_capacity = element.Resource(element.ResourceType.disk_capacity)

        root.create_resource(mem)
        root.create_resource(num_cores)
        root.create_resource(disk)
        root.create_resource(disk_capacity)

        for id_ in range(0, count_node):
            node_uuid = "Node_{0}".format(id_)
            node = element.ComputeNode(id_)
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(id_)

            mem.set_capacity(node, 132)
            disk.set_capacity(node, 250)
            disk_capacity.set_capacity(node, 250)
            num_cores.set_capacity(node, 50)
            root.add_node(node)

        instance1 = element.Instance()
        instance1.uuid = "cae81432-1631-4d4e-b29c-6f3acdcde906"
        mem.set_capacity(instance1, 2)
        disk.set_capacity(instance1, 20)
        disk_capacity.set_capacity(instance1, 20)
        num_cores.set_capacity(instance1, 15)
        instances.append(instance1)
        root.add_instance(instance1)

        instance11 = element.Instance()
        instance11.uuid = "73b09e16-35b7-4922-804e-e8f5d9b740fc"
        mem.set_capacity(instance11, 2)
        disk.set_capacity(instance11, 20)
        disk_capacity.set_capacity(instance11, 20)
        num_cores.set_capacity(instance11, 10)
        instances.append(instance11)
        root.add_instance(instance11)

        instance2 = element.Instance()
        instance2.uuid = "INSTANCE_3"
        mem.set_capacity(instance2, 2)
        disk.set_capacity(instance2, 20)
        disk_capacity.set_capacity(instance2, 20)
        num_cores.set_capacity(instance2, 10)
        instances.append(instance2)
        root.add_instance(instance2)

        instance21 = element.Instance()
        instance21.uuid = "INSTANCE_4"
        mem.set_capacity(instance21, 2)
        disk.set_capacity(instance21, 20)
        disk_capacity.set_capacity(instance21, 20)
        num_cores.set_capacity(instance21, 10)
        instances.append(instance21)
        root.add_instance(instance21)

        root.get_mapping().map(root.get_node_by_uuid("Node_0"),
                               root.get_instance_by_uuid(str(instance1.uuid)))
        root.get_mapping().map(root.get_node_by_uuid("Node_0"),
                               root.get_instance_by_uuid(str(instance11.uuid)))

        root.get_mapping().map(root.get_node_by_uuid("Node_1"),
                               root.get_instance_by_uuid(str(instance2.uuid)))
        root.get_mapping().map(root.get_node_by_uuid("Node_1"),
                               root.get_instance_by_uuid(str(instance21.uuid)))
        return root
