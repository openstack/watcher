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
import uuid

from watcher.common import exception
from watcher.decision_engine.model import element
from watcher.decision_engine.model import model_root
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies \
    import faker_cluster_state


class TestModel(base.TestCase):
    def test_model(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_1()

        self.assertEqual(5, len(model._nodes))
        self.assertEqual(35, len(model._instances))
        self.assertEqual(5, len(model.mapping.get_mapping()))

    def test_add_node(self):
        model = model_root.ModelRoot()
        id_ = "{0}".format(uuid.uuid4())
        node = element.ComputeNode()
        node.uuid = id_
        model.add_node(node)
        self.assertEqual(node, model.get_node_from_id(id_))

    def test_delete_node(self):
        model = model_root.ModelRoot()
        id_ = "{0}".format(uuid.uuid4())
        node = element.ComputeNode()
        node.uuid = id_
        model.add_node(node)
        self.assertEqual(node, model.get_node_from_id(id_))
        model.remove_node(node)
        self.assertRaises(exception.ComputeNodeNotFound,
                          model.get_node_from_id, id_)

    def test_get_all_compute_nodes(self):
        model = model_root.ModelRoot()
        for _ in range(10):
            id_ = "{0}".format(uuid.uuid4())
            node = element.ComputeNode()
            node.uuid = id_
            model.add_node(node)
        all_nodes = model.get_all_compute_nodes()
        for id_ in all_nodes:
            node = model.get_node_from_id(id_)
            model.assert_node(node)

    def test_set_get_state_nodes(self):
        model = model_root.ModelRoot()
        id_ = "{0}".format(uuid.uuid4())
        node = element.ComputeNode()
        node.uuid = id_
        model.add_node(node)

        self.assertIn(node.state, [el.value for el in element.ServiceState])

        node = model.get_node_from_id(id_)
        node.state = element.ServiceState.OFFLINE.value
        self.assertIn(node.state, [el.value for el in element.ServiceState])

    def test_node_from_id_raise(self):
        model = model_root.ModelRoot()
        id_ = "{0}".format(uuid.uuid4())
        node = element.ComputeNode()
        node.uuid = id_
        model.add_node(node)

        id2 = "{0}".format(uuid.uuid4())
        self.assertRaises(exception.ComputeNodeNotFound,
                          model.get_node_from_id, id2)

    def test_remove_node_raise(self):
        model = model_root.ModelRoot()
        id_ = "{0}".format(uuid.uuid4())
        node = element.ComputeNode()
        node.uuid = id_
        model.add_node(node)

        id2 = "{0}".format(uuid.uuid4())
        node2 = element.ComputeNode()
        node2.uuid = id2

        self.assertRaises(exception.ComputeNodeNotFound,
                          model.remove_node, node2)

    def test_assert_node_raise(self):
        model = model_root.ModelRoot()
        id_ = "{0}".format(uuid.uuid4())
        node = element.ComputeNode()
        node.uuid = id_
        model.add_node(node)
        self.assertRaises(exception.IllegalArgumentException,
                          model.assert_node, "objet_qcq")

    def test_instance_from_id_raise(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_1()
        self.assertRaises(exception.InstanceNotFound,
                          model.get_instance_from_id, "valeur_qcq")

    def test_assert_instance_raise(self):
        model = model_root.ModelRoot()
        self.assertRaises(exception.IllegalArgumentException,
                          model.assert_instance, "valeur_qcq")
