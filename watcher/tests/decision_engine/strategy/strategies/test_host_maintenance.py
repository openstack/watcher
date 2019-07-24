# -*- encoding: utf-8 -*-
# Copyright (c) 2017 chinac.com
#
# Authors: suzhengwei<suzhengwei@chinac.com>
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

import mock

from watcher.common import exception
from watcher.decision_engine.model import element
from watcher.decision_engine.strategy import strategies
from watcher.tests.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy


class TestHostMaintenance(TestBaseStrategy):

    def setUp(self):
        super(TestHostMaintenance, self).setUp()
        self.strategy = strategies.HostMaintenance(config=mock.Mock())

    def test_get_instance_state_str(self):
        mock_instance = mock.MagicMock(state="active")
        self.assertEqual("active",
                         self.strategy.get_instance_state_str(mock_instance))

        mock_instance.state = element.InstanceState("active")
        self.assertEqual("active",
                         self.strategy.get_instance_state_str(mock_instance))

        mock_instance.state = None
        self.assertRaises(
            exception.WatcherException,
            self.strategy.get_instance_state_str,
            mock_instance)

    def test_get_node_status_str(self):
        mock_node = mock.MagicMock(status="enabled")
        self.assertEqual("enabled",
                         self.strategy.get_node_status_str(mock_node))

        mock_node.status = element.ServiceState("enabled")
        self.assertEqual("enabled",
                         self.strategy.get_node_status_str(mock_node))

        mock_node.status = None
        self.assertRaises(
            exception.WatcherException,
            self.strategy.get_node_status_str,
            mock_node)

    def test_get_node_capacity(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_capacity = dict(cpu=40, ram=132, disk=250)
        self.assertEqual(node_capacity,
                         self.strategy.get_node_capacity(node_0))

    def test_get_node_used(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_used = dict(cpu=20, ram=4, disk=40)
        self.assertEqual(node_used,
                         self.strategy.get_node_used(node_0))

    def test_get_node_free(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_free = dict(cpu=20, ram=128, disk=210)
        self.assertEqual(node_free,
                         self.strategy.get_node_free(node_0))

    def test_host_fits(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_1 = model.get_node_by_uuid("Node_1")
        self.assertTrue(self.strategy.host_fits(node_0, node_1))

    def test_add_action_enable_compute_node(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        self.strategy.add_action_enable_compute_node(node_0)
        expected = [{'action_type': 'change_nova_service_state',
                     'input_parameters': {
                         'state': 'enabled',
                         'resource_id': 'Node_0',
                         'resource_name': 'hostname_0'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_add_action_maintain_compute_node(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        self.strategy.add_action_maintain_compute_node(node_0)
        expected = [{'action_type': 'change_nova_service_state',
                     'input_parameters': {
                         'state': 'disabled',
                         'disabled_reason': 'watcher_maintaining',
                         'resource_id': 'Node_0',
                         'resource_name': 'hostname_0'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_instance_migration(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        self.strategy.instance_migration(instance_0, node_0, node_1)
        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'destination_node': node_1.uuid,
                                          'source_node': node_0.uuid,
                                          'migration_type': 'live',
                                          'resource_id': instance_0.uuid,
                                          'resource_name': instance_0.name
                                          }}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_instance_migration_without_dest_node(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        self.strategy.instance_migration(instance_0, node_0)
        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'source_node': node_0.uuid,
                                          'migration_type': 'live',
                                          'resource_id': instance_0.uuid,
                                          'resource_name': instance_0.name
                                          }}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_host_migration(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        instance_1 = model.get_instance_by_uuid("INSTANCE_1")
        self.strategy.host_migration(node_0, node_1)
        self.assertEqual(2, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'destination_node': node_1.uuid,
                                          'source_node': node_0.uuid,
                                          'migration_type': 'live',
                                          'resource_id': instance_0.uuid,
                                          'resource_name': instance_0.name
                                          }},
                    {'action_type': 'migrate',
                     'input_parameters': {'destination_node': node_1.uuid,
                                          'source_node': node_0.uuid,
                                          'migration_type': 'live',
                                          'resource_id': instance_1.uuid,
                                          'resource_name': instance_1.name
                                          }}]
        self.assertIn(expected[0], self.strategy.solution.actions)
        self.assertIn(expected[1], self.strategy.solution.actions)

    def test_safe_maintain(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        self.assertFalse(self.strategy.safe_maintain(node_0))
        self.assertFalse(self.strategy.safe_maintain(node_1))

        model = self.fake_c_cluster.\
            generate_scenario_1_with_all_nodes_disable()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        self.assertTrue(self.strategy.safe_maintain(node_0))

    def test_try_maintain(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_1 = model.get_node_by_uuid('Node_1')
        self.strategy.try_maintain(node_1)
        self.assertEqual(2, len(self.strategy.solution.actions))

    def test_exception_compute_node_not_found(self):
        self.m_c_model.return_value = self.fake_c_cluster.build_scenario_1()
        self.assertRaises(exception.ComputeNodeNotFound, self.strategy.execute)

    def test_strategy(self):
        model = self.fake_c_cluster. \
            generate_scenario_9_with_3_active_plus_1_disabled_nodes()
        self.m_c_model.return_value = model
        node_2 = model.get_node_by_uuid('Node_2')
        node_3 = model.get_node_by_uuid('Node_3')
        instance_4 = model.get_instance_by_uuid("INSTANCE_4")

        result = self.strategy.pre_execute()
        self.assertIsNone(result)

        self.strategy.input_parameters = {"maintenance_node": 'hostname_2',
                                          "backup_node": 'hostname_3'}
        self.strategy.do_execute()

        expected = [{'action_type': 'change_nova_service_state',
                     'input_parameters': {
                         'resource_id': 'Node_3',
                         'resource_name': 'hostname_3',
                         'state': 'enabled'}},
                    {'action_type': 'change_nova_service_state',
                     'input_parameters': {
                         'resource_id': 'Node_2',
                         'resource_name': 'hostname_2',
                         'state': 'disabled',
                         'disabled_reason': 'watcher_maintaining'}},
                    {'action_type': 'migrate',
                     'input_parameters': {
                         'destination_node': node_3.uuid,
                         'source_node': node_2.uuid,
                         'migration_type': 'live',
                         'resource_id': instance_4.uuid,
                         'resource_name': instance_4.name}}]
        self.assertEqual(expected, self.strategy.solution.actions)

        result = self.strategy.post_execute()
        self.assertIsNone(result)
