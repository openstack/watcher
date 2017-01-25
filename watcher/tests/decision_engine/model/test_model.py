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

from lxml import etree
from oslo_utils import uuidutils
import six

from watcher.common import exception
from watcher.decision_engine.model import element
from watcher.decision_engine.model import model_root
from watcher.tests import base
from watcher.tests.decision_engine.model import faker_cluster_state


class TestModel(base.TestCase):

    def load_data(self, filename):
        cwd = os.path.abspath(os.path.dirname(__file__))
        data_folder = os.path.join(cwd, "data")

        with open(os.path.join(data_folder, filename), 'rb') as xml_file:
            xml_data = xml_file.read()

        return xml_data

    def load_model(self, filename):
        return model_root.ModelRoot.from_xml(self.load_data(filename))

    def test_model_structure(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.build_scenario_1()

        self.assertEqual(5, len(model.get_all_compute_nodes()))
        self.assertEqual(35, len(model.get_all_instances()))
        self.assertEqual(8, len(model.edges()))

        expected_struct_str = self.load_data('scenario_1.xml')
        parser = etree.XMLParser(remove_blank_text=True)
        expected_struct = etree.fromstring(expected_struct_str, parser)
        model_structure = etree.fromstring(model.to_string(), parser)

        normalized_expected_output = six.BytesIO()
        normalized_model_output = six.BytesIO()
        expected_struct.getroottree().write_c14n(normalized_expected_output)
        model_structure.getroottree().write_c14n(normalized_model_output)

        normalized_expected_struct = normalized_expected_output.getvalue()
        normalized_model_struct = normalized_model_output.getvalue()

        self.assertEqual(normalized_expected_struct, normalized_model_struct)

    def test_build_model_from_xml(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()

        expected_model = fake_cluster.generate_scenario_1()
        struct_str = self.load_data('scenario_1.xml')

        model = model_root.ModelRoot.from_xml(struct_str)
        self.assertEqual(expected_model.to_string(), model.to_string())

    def test_add_node(self):
        model = model_root.ModelRoot()
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        node = element.ComputeNode(id=1)
        node.uuid = uuid_
        model.add_node(node)
        self.assertEqual(node, model.get_node_by_uuid(uuid_))

    def test_delete_node(self):
        model = model_root.ModelRoot()
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        node = element.ComputeNode(id=1)
        node.uuid = uuid_
        model.add_node(node)
        self.assertEqual(node, model.get_node_by_uuid(uuid_))
        model.remove_node(node)
        self.assertRaises(exception.ComputeNodeNotFound,
                          model.get_node_by_uuid, uuid_)

    def test_get_all_compute_nodes(self):
        model = model_root.ModelRoot()
        for id_ in range(10):
            uuid_ = "{0}".format(uuidutils.generate_uuid())
            node = element.ComputeNode(id_)
            node.uuid = uuid_
            model.add_node(node)
        all_nodes = model.get_all_compute_nodes()
        for uuid_ in all_nodes:
            node = model.get_node_by_uuid(uuid_)
            model.assert_node(node)

    def test_set_get_state_nodes(self):
        model = model_root.ModelRoot()
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        node = element.ComputeNode(id=1)
        node.uuid = uuid_
        model.add_node(node)

        self.assertIn(node.state, [el.value for el in element.ServiceState])

        node = model.get_node_by_uuid(uuid_)
        node.state = element.ServiceState.OFFLINE.value
        self.assertIn(node.state, [el.value for el in element.ServiceState])

    def test_node_from_uuid_raise(self):
        model = model_root.ModelRoot()
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        node = element.ComputeNode(id=1)
        node.uuid = uuid_
        model.add_node(node)

        uuid2 = "{0}".format(uuidutils.generate_uuid())
        self.assertRaises(exception.ComputeNodeNotFound,
                          model.get_node_by_uuid, uuid2)

    def test_remove_node_raise(self):
        model = model_root.ModelRoot()
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        node = element.ComputeNode(id=1)
        node.uuid = uuid_
        model.add_node(node)

        uuid2 = "{0}".format(uuidutils.generate_uuid())
        node2 = element.ComputeNode(id=2)
        node2.uuid = uuid2

        self.assertRaises(exception.ComputeNodeNotFound,
                          model.remove_node, node2)

    def test_assert_node_raise(self):
        model = model_root.ModelRoot()
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        node = element.ComputeNode(id=1)
        node.uuid = uuid_
        model.add_node(node)
        self.assertRaises(exception.IllegalArgumentException,
                          model.assert_node, "objet_qcq")

    def test_instance_from_uuid_raise(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_1()
        self.assertRaises(exception.InstanceNotFound,
                          model.get_instance_by_uuid, "valeur_qcq")

    def test_assert_instance_raise(self):
        model = model_root.ModelRoot()
        self.assertRaises(exception.IllegalArgumentException,
                          model.assert_instance, "valeur_qcq")
