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
from oslo_utils import uuidutils

from watcher.decision_engine.model import element
from watcher.tests import base
from watcher.tests.decision_engine.model import faker_cluster_state


class TestMapping(base.TestCase):

    INST1_UUID = "73b09e16-35b7-4922-804e-e8f5d9b740fc"
    INST2_UUID = "a4cab39b-9828-413a-bf88-f76921bf1517"

    def setUp(self):
        super(TestMapping, self).setUp()
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

    def test_get_node_from_instance(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()

        instances = model.get_all_instances()
        keys = list(instances.keys())
        instance = instances[keys[0]]
        if instance.uuid != self.INST1_UUID:
            instance = instances[keys[1]]
        node = model.mapping.get_node_from_instance(instance)
        self.assertEqual('Node_0', node.uuid)

    def test_get_node_by_instance_uuid(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()

        nodes = model.mapping.get_node_instances_by_uuid("BLABLABLA")
        self.assertEqual(0, len(nodes))

    def test_get_all_instances(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()

        instances = model.get_all_instances()
        self.assertEqual(2, len(instances))
        self.assertEqual(element.InstanceState.ACTIVE.value,
                         instances[self.INST1_UUID].state)
        self.assertEqual(self.INST1_UUID, instances[self.INST1_UUID].uuid)
        self.assertEqual(element.InstanceState.ACTIVE.value,
                         instances[self.INST2_UUID].state)
        self.assertEqual(self.INST2_UUID, instances[self.INST2_UUID].uuid)

    def test_get_mapping(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        instance_mapping = model.mapping.instance_mapping
        self.assertEqual(2, len(instance_mapping))
        self.assertEqual('Node_0', instance_mapping[self.INST1_UUID])
        self.assertEqual('Node_1', instance_mapping[self.INST2_UUID])

    def test_migrate_instance(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        instances = model.get_all_instances()
        keys = list(instances.keys())
        instance0 = instances[keys[0]]
        node0 = model.mapping.get_node_by_instance_uuid(instance0.uuid)
        instance1 = instances[keys[1]]
        node1 = model.mapping.get_node_by_instance_uuid(instance1.uuid)

        self.assertEqual(
            False,
            model.migrate_instance(instance1, node1, node1))
        self.assertEqual(
            False,
            model.migrate_instance(instance1, node0, node0))
        self.assertEqual(
            True,
            model.migrate_instance(instance1, node1, node0))
        self.assertEqual(
            True,
            model.migrate_instance(instance1, node0, node1))

    def test_unmap_by_uuid_log_warning(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        instances = model.get_all_instances()
        keys = list(instances.keys())
        instance0 = instances[keys[0]]
        uuid_ = uuidutils.generate_uuid()
        node = element.ComputeNode(id=1)
        node.uuid = uuid_

        model.mapping.unmap_by_uuid(node.uuid, instance0.uuid)

    def test_unmap_by_uuid(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        instances = model.get_all_instances()
        keys = list(instances.keys())
        instance0 = instances[keys[0]]
        node0 = model.mapping.get_node_by_instance_uuid(instance0.uuid)

        model.mapping.unmap_by_uuid(node0.uuid, instance0.uuid)
        self.assertEqual(0, len(model.mapping.get_node_instances_by_uuid(
            node0.uuid)))
