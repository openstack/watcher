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

import os

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

    def load_data(self, filename):
        cwd = os.path.abspath(os.path.dirname(__file__))
        data_folder = os.path.join(cwd, "data")

        with open(os.path.join(data_folder, filename), 'rb') as xml_file:
            xml_data = xml_file.read()

        return xml_data

    def load_model(self, filename):
        return modelroot.ModelRoot.from_xml(self.load_data(filename))

    def execute(self):
        return self._cluster_data_model or self.build_scenario_1()

    def build_scenario_1(self):
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

        current_state_cluster.mapping.map(
            current_state_cluster.get_node_by_uuid("Node_0"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_0"))

        current_state_cluster.mapping.map(
            current_state_cluster.get_node_by_uuid("Node_0"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_1"))

        current_state_cluster.mapping.map(
            current_state_cluster.get_node_by_uuid("Node_1"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_2"))

        current_state_cluster.mapping.map(
            current_state_cluster.get_node_by_uuid("Node_2"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_3"))

        current_state_cluster.mapping.map(
            current_state_cluster.get_node_by_uuid("Node_2"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_4"))

        current_state_cluster.mapping.map(
            current_state_cluster.get_node_by_uuid("Node_2"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_5"))

        current_state_cluster.mapping.map(
            current_state_cluster.get_node_by_uuid("Node_3"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_6"))

        current_state_cluster.mapping.map(
            current_state_cluster.get_node_by_uuid("Node_4"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_7"))

        return current_state_cluster

    def generate_scenario_1(self):
        return self.load_model('scenario_1.xml')

    def generate_scenario_3_with_2_nodes(self):
        return self.load_model('scenario_3_with_2_nodes.xml')

    def generate_scenario_4_with_1_node_no_instance(self):
        return self.load_model('scenario_4_with_1_node_no_instance.xml')

    def generate_scenario_5_with_instance_disk_0(self):
        return self.load_model('scenario_5_with_instance_disk_0.xml')

    def generate_scenario_6_with_2_nodes(self):
        return self.load_model('scenario_6_with_2_nodes.xml')

    def generate_scenario_7_with_2_nodes(self):
        return self.load_model('scenario_7_with_2_nodes.xml')

    def generate_scenario_8_with_4_nodes(self):
        return self.load_model('scenario_8_with_4_nodes.xml')

    def generate_scenario_9_with_3_active_plus_1_disabled_nodes(self):
        return self.load_model(
            'scenario_9_with_3_active_plus_1_disabled_nodes.xml')
