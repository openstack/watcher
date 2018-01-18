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

from oslo_utils import uuidutils

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
        model1 = fake_cluster.build_scenario_1()

        self.assertEqual(5, len(model1.get_all_compute_nodes()))
        self.assertEqual(35, len(model1.get_all_instances()))
        self.assertEqual(8, len(model1.edges()))

        expected_struct_str = self.load_data('scenario_1.xml')
        model2 = model_root.ModelRoot.from_xml(expected_struct_str)

        self.assertTrue(model_root.ModelRoot.is_isomorphic(model2, model1))

    def test_build_model_from_xml(self):
        fake_cluster = faker_cluster_state.FakerModelCollector()

        expected_model = fake_cluster.generate_scenario_1()
        struct_str = self.load_data('scenario_1.xml')

        model = model_root.ModelRoot.from_xml(struct_str)
        self.assertEqual(expected_model.to_string(), model.to_string())

    def test_get_node_by_instance_uuid(self):
        model = model_root.ModelRoot()
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        node = element.ComputeNode(id=1)
        node.uuid = uuid_
        model.add_node(node)
        self.assertEqual(node, model.get_node_by_uuid(uuid_))
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        instance = element.Instance(id=1)
        instance.uuid = uuid_
        model.add_instance(instance)
        self.assertEqual(instance, model.get_instance_by_uuid(uuid_))
        model.map_instance(instance, node)
        self.assertEqual(node, model.get_node_by_instance_uuid(instance.uuid))

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


class TestStorageModel(base.TestCase):

    def load_data(self, filename):
        cwd = os.path.abspath(os.path.dirname(__file__))
        data_folder = os.path.join(cwd, "data")

        with open(os.path.join(data_folder, filename), 'rb') as xml_file:
            xml_data = xml_file.read()

        return xml_data

    def load_model(self, filename):
        return model_root.StorageModelRoot.from_xml(self.load_data(filename))

    def test_model_structure(self):
        fake_cluster = faker_cluster_state.FakerStorageModelCollector()
        model1 = fake_cluster.build_scenario_1()

        self.assertEqual(2, len(model1.get_all_storage_nodes()))
        self.assertEqual(9, len(model1.get_all_volumes()))
        self.assertEqual(12, len(model1.edges()))

        expected_struct_str = self.load_data('storage_scenario_1.xml')
        model2 = model_root.StorageModelRoot.from_xml(expected_struct_str)
        self.assertTrue(
            model_root.StorageModelRoot.is_isomorphic(model2, model1))

    def test_build_model_from_xml(self):
        fake_cluster = faker_cluster_state.FakerStorageModelCollector()

        expected_model = fake_cluster.generate_scenario_1()
        struct_str = self.load_data('storage_scenario_1.xml')

        model = model_root.StorageModelRoot.from_xml(struct_str)
        self.assertEqual(expected_model.to_string(), model.to_string())

    def test_assert_node_raise(self):
        model = model_root.StorageModelRoot()
        node = element.StorageNode(host="host@backend")
        model.add_node(node)
        self.assertRaises(exception.IllegalArgumentException,
                          model.assert_node, "obj")

    def test_assert_pool_raise(self):
        model = model_root.StorageModelRoot()
        pool = element.Pool(name="host@backend#pool")
        model.add_pool(pool)
        self.assertRaises(exception.IllegalArgumentException,
                          model.assert_pool, "obj")

    def test_assert_volume_raise(self):
        model = model_root.StorageModelRoot()
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        volume = element.Volume(uuid=uuid_)
        model.add_volume(volume)
        self.assertRaises(exception.IllegalArgumentException,
                          model.assert_volume, "obj")

    def test_add_node(self):
        model = model_root.StorageModelRoot()
        hostname = "host@backend"
        node = element.StorageNode(host=hostname)
        model.add_node(node)
        self.assertEqual(node, model.get_node_by_name(hostname))

    def test_add_pool(self):
        model = model_root.StorageModelRoot()
        pool_name = "host@backend#pool"
        pool = element.Pool(name=pool_name)
        model.add_pool(pool)
        self.assertEqual(pool, model.get_pool_by_pool_name(pool_name))

    def test_remove_node(self):
        model = model_root.StorageModelRoot()
        hostname = "host@backend"
        node = element.StorageNode(host=hostname)
        model.add_node(node)
        self.assertEqual(node, model.get_node_by_name(hostname))
        model.remove_node(node)
        self.assertRaises(exception.StorageNodeNotFound,
                          model.get_node_by_name, hostname)

    def test_remove_pool(self):
        model = model_root.StorageModelRoot()
        pool_name = "host@backend#pool"
        pool = element.Pool(name=pool_name)
        model.add_pool(pool)
        self.assertEqual(pool, model.get_pool_by_pool_name(pool_name))
        model.remove_pool(pool)
        self.assertRaises(exception.PoolNotFound,
                          model.get_pool_by_pool_name, pool_name)

    def test_map_unmap_pool(self):
        model = model_root.StorageModelRoot()
        hostname = "host@backend"
        node = element.StorageNode(host=hostname)
        model.add_node(node)
        self.assertEqual(node, model.get_node_by_name(hostname))
        pool_name = "host@backend#pool"
        pool = element.Pool(name=pool_name)
        model.add_pool(pool)
        self.assertEqual(pool, model.get_pool_by_pool_name(pool_name))
        model.map_pool(pool, node)
        self.assertTrue(pool.name in model.predecessors(node.host))
        model.unmap_pool(pool, node)
        self.assertFalse(pool.name in model.predecessors(node.host))

    def test_add_volume(self):
        model = model_root.StorageModelRoot()
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        volume = element.Volume(uuid=uuid_)
        model.add_volume(volume)
        self.assertEqual(volume, model.get_volume_by_uuid(uuid_))

    def test_remove_volume(self):
        model = model_root.StorageModelRoot()
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        volume = element.Volume(uuid=uuid_)
        model.add_volume(volume)
        self.assertEqual(volume, model.get_volume_by_uuid(uuid_))
        model.remove_volume(volume)
        self.assertRaises(exception.VolumeNotFound,
                          model.get_volume_by_uuid, uuid_)

    def test_map_unmap_volume(self):
        model = model_root.StorageModelRoot()
        pool_name = "host@backend#pool"
        pool = element.Pool(name=pool_name)
        model.add_pool(pool)
        self.assertEqual(pool, model.get_pool_by_pool_name(pool_name))
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        volume = element.Volume(uuid=uuid_)
        model.add_volume(volume)
        self.assertEqual(volume, model.get_volume_by_uuid(uuid_))
        model.map_volume(volume, pool)
        self.assertTrue(volume.uuid in model.predecessors(pool.name))
        model.unmap_volume(volume, pool)
        self.assertFalse(volume.uuid in model.predecessors(pool.name))

    def test_get_all_storage_nodes(self):
        model = model_root.StorageModelRoot()
        for i in range(10):
            hostname = "host_{0}".format(i)
            node = element.StorageNode(host=hostname)
            model.add_node(node)
        all_nodes = model.get_all_storage_nodes()
        for hostname in all_nodes:
            node = model.get_node_by_name(hostname)
            model.assert_node(node)

    def test_get_all_volumes(self):
        model = model_root.StorageModelRoot()
        for id_ in range(10):
            uuid_ = "{0}".format(uuidutils.generate_uuid())
            volume = element.Volume(uuid=uuid_)
            model.add_volume(volume)
        all_volumes = model.get_all_volumes()
        for vol in all_volumes:
            volume = model.get_volume_by_uuid(vol)
            model.assert_volume(volume)

    def test_get_node_pools(self):
        model = model_root.StorageModelRoot()
        hostname = "host@backend"
        node = element.StorageNode(host=hostname)
        model.add_node(node)
        self.assertEqual(node, model.get_node_by_name(hostname))
        pool_name = "host@backend#pool"
        pool = element.Pool(name=pool_name)
        model.add_pool(pool)
        self.assertEqual(pool, model.get_pool_by_pool_name(pool_name))
        model.map_pool(pool, node)
        self.assertEqual([pool], model.get_node_pools(node))

    def test_get_pool_by_volume(self):
        model = model_root.StorageModelRoot()
        pool_name = "host@backend#pool"
        pool = element.Pool(name=pool_name)
        model.add_pool(pool)
        self.assertEqual(pool, model.get_pool_by_pool_name(pool_name))
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        volume = element.Volume(uuid=uuid_)
        model.add_volume(volume)
        self.assertEqual(volume, model.get_volume_by_uuid(uuid_))
        model.map_volume(volume, pool)
        self.assertEqual(pool, model.get_pool_by_volume(volume))

    def test_get_pool_volumes(self):
        model = model_root.StorageModelRoot()
        pool_name = "host@backend#pool"
        pool = element.Pool(name=pool_name)
        model.add_pool(pool)
        self.assertEqual(pool, model.get_pool_by_pool_name(pool_name))
        uuid_ = "{0}".format(uuidutils.generate_uuid())
        volume = element.Volume(uuid=uuid_)
        model.add_volume(volume)
        self.assertEqual(volume, model.get_volume_by_uuid(uuid_))
        model.map_volume(volume, pool)
        self.assertEqual([volume], model.get_pool_volumes(pool))


class TestBaremetalModel(base.TestCase):

    def load_data(self, filename):
        cwd = os.path.abspath(os.path.dirname(__file__))
        data_folder = os.path.join(cwd, "data")

        with open(os.path.join(data_folder, filename), 'rb') as xml_file:
            xml_data = xml_file.read()

        return xml_data

    def load_model(self, filename):
        return model_root.StorageModelRoot.from_xml(self.load_data(filename))

    def test_model_structure(self):
        fake_cluster = faker_cluster_state.FakerBaremetalModelCollector()
        model1 = fake_cluster.build_scenario_1()
        self.assertEqual(2, len(model1.get_all_ironic_nodes()))

        expected_struct_str = self.load_data('ironic_scenario_1.xml')
        model2 = model_root.BaremetalModelRoot.from_xml(expected_struct_str)
        self.assertTrue(
            model_root.BaremetalModelRoot.is_isomorphic(model2, model1))

    def test_build_model_from_xml(self):
        fake_cluster = faker_cluster_state.FakerBaremetalModelCollector()

        expected_model = fake_cluster.generate_scenario_1()
        struct_str = self.load_data('ironic_scenario_1.xml')

        model = model_root.BaremetalModelRoot.from_xml(struct_str)
        self.assertEqual(expected_model.to_string(), model.to_string())

    def test_assert_node_raise(self):
        model = model_root.BaremetalModelRoot()
        node_uuid = uuidutils.generate_uuid()
        node = element.IronicNode(uuid=node_uuid)
        model.add_node(node)
        self.assertRaises(exception.IllegalArgumentException,
                          model.assert_node, "obj")

    def test_add_node(self):
        model = model_root.BaremetalModelRoot()
        node_uuid = uuidutils.generate_uuid()
        node = element.IronicNode(uuid=node_uuid)
        model.add_node(node)
        self.assertEqual(node, model.get_node_by_uuid(node_uuid))

    def test_remove_node(self):
        model = model_root.BaremetalModelRoot()
        node_uuid = uuidutils.generate_uuid()
        node = element.IronicNode(uuid=node_uuid)
        model.add_node(node)
        self.assertEqual(node, model.get_node_by_uuid(node_uuid))
        model.remove_node(node)
        self.assertRaises(exception.IronicNodeNotFound,
                          model.get_node_by_uuid, node_uuid)

    def test_get_all_ironic_nodes(self):
        model = model_root.BaremetalModelRoot()
        for i in range(10):
            node_uuid = uuidutils.generate_uuid()
            node = element.IronicNode(uuid=node_uuid)
            model.add_node(node)
        all_nodes = model.get_all_ironic_nodes()
        for node_uuid in all_nodes:
            node = model.get_node_by_uuid(node_uuid)
            model.assert_node(node)
