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

from lxml import etree
from oslo_utils import uuidutils
import six

from watcher.common import exception
from watcher.decision_engine.model import element
from watcher.decision_engine.model import model_root
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies \
    import faker_cluster_state


class TestModel(base.TestCase):

    def test_model_structure(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_1()

        self.assertEqual(5, len(model._nodes))
        self.assertEqual(35, len(model._instances))
        self.assertEqual(5, len(model.mapping.get_mapping()))

        expected_struct_str = """
        <ModelRoot>
            <ComputeNode ResourceType.cpu_cores="40" ResourceType.disk="250"
                ResourceType.disk_capacity="250" ResourceType.memory="132"
                hostname="hostname_0" human_id="" id="0" state="up"
                status="enabled" uuid="Node_0">
                <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                    ResourceType.disk_capacity="20" ResourceType.memory="2"
                    hostname="" human_id="" state="active" uuid="INSTANCE_0"/>
                <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                    ResourceType.disk_capacity="20" ResourceType.memory="2"
                    hostname="" human_id="" state="active" uuid="INSTANCE_1"/>
            </ComputeNode>
            <ComputeNode ResourceType.cpu_cores="40" ResourceType.disk="250"
                ResourceType.disk_capacity="250" ResourceType.memory="132"
                hostname="hostname_1" human_id="" id="1" state="up"
                status="enabled" uuid="Node_1">
                <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                    ResourceType.disk_capacity="20" ResourceType.memory="2"
                    hostname="" human_id="" state="active" uuid="INSTANCE_2"/>
            </ComputeNode>
            <ComputeNode ResourceType.cpu_cores="40" ResourceType.disk="250"
                ResourceType.disk_capacity="250" ResourceType.memory="132"
                hostname="hostname_2" human_id="" id="2" state="up"
                status="enabled" uuid="Node_2">
                <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                    ResourceType.disk_capacity="20" ResourceType.memory="2"
                    hostname="" human_id="" state="active" uuid="INSTANCE_3"/>
                <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                    ResourceType.disk_capacity="20" ResourceType.memory="2"
                    hostname="" human_id="" state="active" uuid="INSTANCE_4"/>
                <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                    ResourceType.disk_capacity="20" ResourceType.memory="2"
                    hostname="" human_id="" state="active" uuid="INSTANCE_5"/>
            </ComputeNode>
            <ComputeNode ResourceType.cpu_cores="40" ResourceType.disk="250"
                ResourceType.disk_capacity="250" ResourceType.memory="132"
                hostname="hostname_3" human_id="" id="3" state="up"
                status="enabled" uuid="Node_3">
                <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                    ResourceType.disk_capacity="20" ResourceType.memory="2"
                    hostname="" human_id="" state="active" uuid="INSTANCE_6"/>
            </ComputeNode>
            <ComputeNode ResourceType.cpu_cores="40" ResourceType.disk="250"
                ResourceType.disk_capacity="250" ResourceType.memory="132"
                hostname="hostname_4" human_id="" id="4" state="up"
                status="enabled" uuid="Node_4">
                <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                    ResourceType.disk_capacity="20" ResourceType.memory="2"
                    hostname="" human_id="" state="active" uuid="INSTANCE_7"/>
            </ComputeNode>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_10"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_11"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_12"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_13"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_14"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_15"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_16"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_17"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_18"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_19"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_20"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_21"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_22"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_23"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_24"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_25"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_26"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_27"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_28"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_29"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_30"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_31"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_32"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_33"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_34"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_8"/>
            <Instance ResourceType.cpu_cores="10" ResourceType.disk="20"
                ResourceType.disk_capacity="20" ResourceType.memory="2"
                hostname="" human_id="" state="active" uuid="INSTANCE_9"/>
        </ModelRoot>
        """
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
