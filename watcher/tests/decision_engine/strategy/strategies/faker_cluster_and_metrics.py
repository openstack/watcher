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

import mock

from watcher.decision_engine.model.collector import base
from watcher.decision_engine.model import element
from watcher.decision_engine.model import model_root as modelroot


class FakerModelCollector(base.BaseClusterDataModelCollector):

    def __init__(self, config=None, osc=None):
        if config is None:
            config = mock.Mock()
        super(FakerModelCollector, self).__init__(config)

    @property
    def notification_endpoints(self):
        return []

    def execute(self):
        return self.generate_scenario_1()

    def generate_scenario_1(self):
        """Simulates cluster with 2 nodes and 2 instances using 1:1 mapping"""

        current_state_cluster = modelroot.ModelRoot()
        count_node = 2
        count_instance = 2

        mem = element.Resource(element.ResourceType.memory)
        num_cores = element.Resource(element.ResourceType.cpu_cores)
        disk = element.Resource(element.ResourceType.disk)
        disk_capacity =\
            element.Resource(element.ResourceType.disk_capacity)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)
        current_state_cluster.create_resource(disk_capacity)

        for id_ in range(0, count_node):
            node_uuid = "Node_{0}".format(id_)
            node = element.ComputeNode(id_)
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(id_)
            node.state = 'enabled'

            mem.set_capacity(node, 64)
            disk_capacity.set_capacity(node, 250)
            num_cores.set_capacity(node, 40)
            current_state_cluster.add_node(node)

        for i in range(0, count_instance):
            instance_uuid = "INSTANCE_{0}".format(i)
            instance = element.Instance()
            instance.uuid = instance_uuid
            instance.state = element.InstanceState.ACTIVE.value
            mem.set_capacity(instance, 2)
            disk.set_capacity(instance, 20)
            num_cores.set_capacity(instance, 10)
            current_state_cluster.add_instance(instance)

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_node_by_uuid("Node_0"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_0"))

        current_state_cluster.get_mapping().map(
            current_state_cluster.get_node_by_uuid("Node_1"),
            current_state_cluster.get_instance_by_uuid("INSTANCE_1"))

        return current_state_cluster

    def generate_scenario_2(self):
        """Simulates a cluster

        With 4 nodes and 6 instances all mapped to a single node
        """

        current_state_cluster = modelroot.ModelRoot()
        count_node = 4
        count_instance = 6

        mem = element.Resource(element.ResourceType.memory)
        num_cores = element.Resource(element.ResourceType.cpu_cores)
        disk = element.Resource(element.ResourceType.disk)
        disk_capacity =\
            element.Resource(element.ResourceType.disk_capacity)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)
        current_state_cluster.create_resource(disk_capacity)

        for id_ in range(0, count_node):
            node_uuid = "Node_{0}".format(id_)
            node = element.ComputeNode(id_)
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(id_)
            node.state = 'up'

            mem.set_capacity(node, 64)
            disk_capacity.set_capacity(node, 250)
            num_cores.set_capacity(node, 16)
            current_state_cluster.add_node(node)

        for i in range(0, count_instance):
            instance_uuid = "INSTANCE_{0}".format(i)
            instance = element.Instance()
            instance.uuid = instance_uuid
            instance.state = element.InstanceState.ACTIVE.value
            mem.set_capacity(instance, 2)
            disk.set_capacity(instance, 20)
            num_cores.set_capacity(instance, 10)
            current_state_cluster.add_instance(instance)

            current_state_cluster.get_mapping().map(
                current_state_cluster.get_node_by_uuid("Node_0"),
                current_state_cluster.get_instance_by_uuid("INSTANCE_%s" % i))

        return current_state_cluster

    def generate_scenario_3(self):
        """Simulates a cluster

        With 4 nodes and 6 instances all mapped to one node
        """

        current_state_cluster = modelroot.ModelRoot()
        count_node = 2
        count_instance = 4

        mem = element.Resource(element.ResourceType.memory)
        num_cores = element.Resource(element.ResourceType.cpu_cores)
        disk = element.Resource(element.ResourceType.disk)
        disk_capacity =\
            element.Resource(element.ResourceType.disk_capacity)

        current_state_cluster.create_resource(mem)
        current_state_cluster.create_resource(num_cores)
        current_state_cluster.create_resource(disk)
        current_state_cluster.create_resource(disk_capacity)

        for id_ in range(0, count_node):
            node_uuid = "Node_{0}".format(id_)
            node = element.ComputeNode(id_)
            node.uuid = node_uuid
            node.hostname = "hostname_{0}".format(id_)
            node.state = 'up'

            mem.set_capacity(node, 64)
            disk_capacity.set_capacity(node, 250)
            num_cores.set_capacity(node, 10)
            current_state_cluster.add_node(node)

        for i in range(6, 6 + count_instance):
            instance_uuid = "INSTANCE_{0}".format(i)
            instance = element.Instance()
            instance.uuid = instance_uuid
            instance.state = element.InstanceState.ACTIVE.value
            mem.set_capacity(instance, 2)
            disk.set_capacity(instance, 20)
            num_cores.set_capacity(instance, 2 ** (i - 6))
            current_state_cluster.add_instance(instance)

            current_state_cluster.get_mapping().map(
                current_state_cluster.get_node_by_uuid("Node_0"),
                current_state_cluster.get_instance_by_uuid("INSTANCE_%s" % i))

        return current_state_cluster


class FakeCeilometerMetrics(object):
    def __init__(self, model):
        self.model = model

    def mock_get_statistics(self, resource_id, meter_name, period=3600,
                            aggregate='avg'):
        if meter_name == "compute.node.cpu.percent":
            return self.get_node_cpu_util(resource_id)
        elif meter_name == "cpu_util":
            return self.get_instance_cpu_util(resource_id)
        elif meter_name == "memory.usage":
            return self.get_instance_ram_util(resource_id)
        elif meter_name == "disk.root.size":
            return self.get_instance_disk_root_size(resource_id)

    def get_node_cpu_util(self, r_id):
        """Calculates node utilization dynamicaly.

        node CPU utilization should consider
        and corelate with actual instance-node mappings
        provided within a cluster model.
        Returns relative node CPU utilization <0, 100>.
        :param r_id: resource id
        """

        id = '%s_%s' % (r_id.split('_')[0], r_id.split('_')[1])
        instances = self.model.get_mapping().get_node_instances_by_uuid(id)
        util_sum = 0.0
        node_cpu_cores = self.model.get_resource_by_uuid(
            element.ResourceType.cpu_cores).get_capacity_by_uuid(id)
        for instance_uuid in instances:
            instance_cpu_cores = self.model.get_resource_by_uuid(
                element.ResourceType.cpu_cores).\
                get_capacity(self.model.get_instance_by_uuid(instance_uuid))
            total_cpu_util = instance_cpu_cores * self.get_instance_cpu_util(
                instance_uuid)
            util_sum += total_cpu_util / 100.0
        util_sum /= node_cpu_cores
        return util_sum * 100.0

    def get_instance_cpu_util(self, r_id):
        instance_cpu_util = dict()
        instance_cpu_util['INSTANCE_0'] = 10
        instance_cpu_util['INSTANCE_1'] = 30
        instance_cpu_util['INSTANCE_2'] = 60
        instance_cpu_util['INSTANCE_3'] = 20
        instance_cpu_util['INSTANCE_4'] = 40
        instance_cpu_util['INSTANCE_5'] = 50
        instance_cpu_util['INSTANCE_6'] = 100
        instance_cpu_util['INSTANCE_7'] = 100
        instance_cpu_util['INSTANCE_8'] = 100
        instance_cpu_util['INSTANCE_9'] = 100
        return instance_cpu_util[str(r_id)]

    def get_instance_ram_util(self, r_id):
        instance_ram_util = dict()
        instance_ram_util['INSTANCE_0'] = 1
        instance_ram_util['INSTANCE_1'] = 2
        instance_ram_util['INSTANCE_2'] = 4
        instance_ram_util['INSTANCE_3'] = 8
        instance_ram_util['INSTANCE_4'] = 3
        instance_ram_util['INSTANCE_5'] = 2
        instance_ram_util['INSTANCE_6'] = 1
        instance_ram_util['INSTANCE_7'] = 2
        instance_ram_util['INSTANCE_8'] = 4
        instance_ram_util['INSTANCE_9'] = 8
        return instance_ram_util[str(r_id)]

    def get_instance_disk_root_size(self, r_id):
        instance_disk_util = dict()
        instance_disk_util['INSTANCE_0'] = 10
        instance_disk_util['INSTANCE_1'] = 15
        instance_disk_util['INSTANCE_2'] = 30
        instance_disk_util['INSTANCE_3'] = 35
        instance_disk_util['INSTANCE_4'] = 20
        instance_disk_util['INSTANCE_5'] = 25
        instance_disk_util['INSTANCE_6'] = 25
        instance_disk_util['INSTANCE_7'] = 25
        instance_disk_util['INSTANCE_8'] = 25
        instance_disk_util['INSTANCE_9'] = 25
        return instance_disk_util[str(r_id)]
