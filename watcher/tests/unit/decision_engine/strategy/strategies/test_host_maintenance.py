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

from unittest import mock

from watcher.common import exception
from watcher.decision_engine.model import element
from watcher.decision_engine.strategy import strategies
from watcher.tests.unit.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy


class TestHostMaintenance(TestBaseStrategy):

    def setUp(self):
        super().setUp()
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

    def test_instance_handle(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        self.strategy.instance_handle(instance_0, node_0, node_1)
        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'destination_node': node_1.hostname,
                                          'source_node': node_0.hostname,
                                          'migration_type': 'live',
                                          'resource_id': instance_0.uuid,
                                          'resource_name': instance_0.name
                                          }}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_instance_handle_without_dest_node(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        self.strategy.instance_handle(instance_0, node_0)
        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'source_node': node_0.hostname,
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
                     'input_parameters': {'destination_node': node_1.hostname,
                                          'source_node': node_0.hostname,
                                          'migration_type': 'live',
                                          'resource_id': instance_0.uuid,
                                          'resource_name': instance_0.name
                                          }},
                    {'action_type': 'migrate',
                     'input_parameters': {'destination_node': node_1.hostname,
                                          'source_node': node_0.hostname,
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
        # It will return true, if backup node is passed
        self.assertTrue(self.strategy.safe_maintain(node_0, node_1))

        model = self.fake_c_cluster.\
            generate_scenario_1_with_all_nodes_disable()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        # It will return false, if there is no backup node
        self.assertFalse(self.strategy.safe_maintain(node_0))

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
                         'destination_node': node_3.hostname,
                         'source_node': node_2.hostname,
                         'migration_type': 'live',
                         'resource_id': instance_4.uuid,
                         'resource_name': instance_4.name}}]
        self.assertEqual(expected, self.strategy.solution.actions)

        result = self.strategy.post_execute()
        self.assertIsNone(result)

    def test_schema_default_values(self):
        """Test that disable_* parameters default to False when not provided"""
        parameters = {"maintenance_node": "hostname_0"}
        self.strategy.input_parameters = parameters

        # Parameters should default to False when not provided
        self.assertFalse(self.strategy.input_parameters.get(
            'disable_live_migration', False))
        self.assertFalse(self.strategy.input_parameters.get(
            'disable_cold_migration', False))

    def test_add_action_stop_instance(self):
        """Test add_action_stop_instance method"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")

        self.strategy.add_action_stop_instance(instance_0)

        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'stop', 'input_parameters': {
            'resource_id': instance_0.uuid}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_instance_handle_both_migrations_disabled_active_instance(self):
        """Test instance_handle with both migrations disabled on active"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'disable_live_migration': True,
            'disable_cold_migration': True
        }

        self.strategy.instance_handle(instance_0, node_0)

        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'stop', 'input_parameters': {
            'resource_id': instance_0.uuid}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_instance_handle_both_migrations_disabled_inactive_instance(self):
        """Test instance_handle with both migrations disabled on inactive"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        instance_1 = model.get_instance_by_uuid("INSTANCE_1")
        instance_1.state = "stopped"

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'disable_live_migration': True,
            'disable_cold_migration': True
        }

        self.strategy.instance_handle(instance_1, node_0)
        self.assertEqual(0, len(self.strategy.solution.actions))

    def test_instance_handle_live_migration_disabled_active_instance(self):
        """Test instance_handle with live migration disabled on active"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'disable_live_migration': True,
        }

        self.strategy.instance_handle(instance_0, node_0, node_1)

        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {
                         'destination_node': node_1.hostname,
                         'source_node': node_0.hostname,
                         'migration_type': 'cold',
                         'resource_id': instance_0.uuid,
                         'resource_name': instance_0.name
                     }}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_instance_handle_live_migration_disabled_inactive_instance(self):
        """Test instance_handle with live migration disabled on inactive"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_1 = model.get_instance_by_uuid("INSTANCE_1")
        instance_1.state = 'stopped'

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'disable_live_migration': True,
        }

        self.strategy.instance_handle(instance_1, node_0, node_1)

        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {
                         'destination_node': node_1.hostname,
                         'source_node': node_0.hostname,
                         'migration_type': 'cold',
                         'resource_id': instance_1.uuid,
                         'resource_name': instance_1.name
                     }}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_instance_handle_cold_migration_disabled_active_instance(self):
        """Test instance_handle with cold migration disabled on active"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'disable_cold_migration': True
        }

        self.strategy.instance_handle(instance_0, node_0, node_1)

        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {
                         'destination_node': node_1.hostname,
                         'source_node': node_0.hostname,
                         'migration_type': 'live',
                         'resource_id': instance_0.uuid,
                         'resource_name': instance_0.name
                     }}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_instance_handle_cold_migration_disabled_inactive_instance(self):
        """Test instance_handle with cold migration disabled on inactive"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_1 = model.get_instance_by_uuid("INSTANCE_1")
        instance_1.state = 'stopped'

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'disable_cold_migration': True
        }

        self.strategy.instance_handle(instance_1, node_0, node_1)

        # No actions should be generated
        self.assertEqual(0, len(self.strategy.solution.actions))

    def test_instance_handle_no_migrations_disabled_active_instance(self):
        """Test instance_handle with no migrations disabled on active"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
        }

        self.strategy.instance_handle(instance_0, node_0, node_1)

        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {
                         'destination_node': node_1.hostname,
                         'source_node': node_0.hostname,
                         'migration_type': 'live',
                         'resource_id': instance_0.uuid,
                         'resource_name': instance_0.name
                     }}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_instance_handle_no_migrations_disabled_inactive_instance(self):
        """Test instance_handle with no migrations disabled on inactive"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_1 = model.get_instance_by_uuid("INSTANCE_1")
        instance_1.state = 'stopped'

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
        }

        self.strategy.instance_handle(instance_1, node_0, node_1)

        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {
                         'destination_node': node_1.hostname,
                         'source_node': node_0.hostname,
                         'migration_type': 'cold',
                         'resource_id': instance_1.uuid,
                         'resource_name': instance_1.name
                     }}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_host_migration_with_both_migrations_disabled(self):
        """Test host_migration with both migrations disabled"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        instance_1 = model.get_instance_by_uuid("INSTANCE_1")

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'disable_live_migration': True,
            'disable_cold_migration': True
        }

        self.strategy.host_migration(node_0, node_1)

        # Should generate stop actions for all instances
        self.assertEqual(2, len(self.strategy.solution.actions))
        expected_actions = [
            {'action_type': 'stop', 'input_parameters': {
                'resource_id': instance_0.uuid}},
            {'action_type': 'stop', 'input_parameters': {
                'resource_id': instance_1.uuid}}
        ]
        for action in expected_actions:
            self.assertIn(action, self.strategy.solution.actions)

    def test_host_migration_with_live_migration_disabled(self):
        """Test host_migration with live migration disabled"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        instance_1 = model.get_instance_by_uuid("INSTANCE_1")

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'disable_live_migration': True,
        }

        self.strategy.host_migration(node_0, node_1)

        # Should generate cold migrate actions for all instances
        self.assertEqual(2, len(self.strategy.solution.actions))
        expected_actions = [
            {'action_type': 'migrate',
             'input_parameters': {
                 'destination_node': node_1.hostname,
                 'source_node': node_0.hostname,
                 'migration_type': 'cold',
                 'resource_id': instance_0.uuid,
                 'resource_name': instance_0.name
             }},
            {'action_type': 'migrate',
             'input_parameters': {
                 'destination_node': node_1.hostname,
                 'source_node': node_0.hostname,
                 'migration_type': 'cold',
                 'resource_id': instance_1.uuid,
                 'resource_name': instance_1.name
             }}
        ]
        for action in expected_actions:
            self.assertIn(action, self.strategy.solution.actions)

    def test_safe_maintain_with_both_migrations_disabled(self):
        """Test safe_maintain with both migrations disabled"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')  # maintenance node
        node_1 = model.get_node_by_uuid('Node_1')  # backup node
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        instance_1 = model.get_instance_by_uuid("INSTANCE_1")

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'backup_node': 'hostname_1',
            'disable_live_migration': True,
            'disable_cold_migration': True
        }

        result = self.strategy.safe_maintain(node_0, node_1)

        self.assertTrue(result)
        # Should have: maintain node + stop actions for all instances
        # (backup node is already enabled in scenario_1, so no enable action)
        self.assertEqual(3, len(self.strategy.solution.actions))

        expected_actions = [
            {'action_type': 'change_nova_service_state',
             'input_parameters': {
                 'resource_id': node_0.uuid,
                 'resource_name': node_0.hostname,
                 'state': 'disabled',
                 'disabled_reason': 'watcher_maintaining'
             }},
            {'action_type': 'stop', 'input_parameters': {
                'resource_id': instance_0.uuid}},
            {'action_type': 'stop', 'input_parameters': {
                'resource_id': instance_1.uuid}}
        ]
        for action in expected_actions:
            self.assertIn(action, self.strategy.solution.actions)

    def test_try_maintain_with_both_migrations_disabled(self):
        """Test try_maintain with both migrations disabled"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        instance_1 = model.get_instance_by_uuid("INSTANCE_1")

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'disable_live_migration': True,
            'disable_cold_migration': True
        }

        self.strategy.try_maintain(node_0)

        # Should have: maintain node + stop actions for all instances
        self.assertEqual(3, len(self.strategy.solution.actions))

        expected_actions = [
            {'action_type': 'change_nova_service_state',
             'input_parameters': {
                 'resource_id': node_0.uuid,
                 'resource_name': node_0.hostname,
                 'state': 'disabled',
                 'disabled_reason': 'watcher_maintaining'
             }},
            {'action_type': 'stop', 'input_parameters': {
                'resource_id': instance_0.uuid}},
            {'action_type': 'stop', 'input_parameters': {
                'resource_id': instance_1.uuid}}
        ]
        for action in expected_actions:
            self.assertIn(action, self.strategy.solution.actions)

    def test_strategy_with_both_migrations_disabled(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'backup_node': 'hostname_1',
            'disable_live_migration': True,
            'disable_cold_migration': True
        }

        self.strategy.do_execute()

        # Should have: maintain node + stop all instances
        self.assertEqual(3, len(self.strategy.solution.actions))

        # Check that we have stop actions
        stop_actions = [action for action in self.strategy.solution.actions
                        if action['action_type'] == 'stop']
        self.assertEqual(2, len(stop_actions))

    def test_strategy_with_live_migration_disabled(self):
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model

        self.strategy.input_parameters = {
            'maintenance_node': 'hostname_0',
            'backup_node': 'hostname_1',
            'disable_live_migration': True,
        }

        self.strategy.do_execute()

        # Should have: maintain node + cold migrate all instances
        self.assertEqual(3, len(self.strategy.solution.actions))

        # Check that we have cold migrate actions
        cold_migrate_actions = [
            action for action in self.strategy.solution.actions
            if action['action_type'] == 'migrate' and
            action['input_parameters']['migration_type'] == 'cold'
        ]
        self.assertEqual(2, len(cold_migrate_actions))

    def test_backward_compatibility_without_new_parameters(self):
        """Test that existing behavior is preserved when new params not used"""
        model = self.fake_c_cluster.generate_scenario_1()
        self.m_c_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        instance_1 = model.get_instance_by_uuid("INSTANCE_1")

        # Test without new parameters (should behave like original)
        self.strategy.input_parameters = {'maintenance_node': 'hostname_0'}
        self.strategy.do_execute()

        # Should have: maintain node + migrate all instances
        self.assertEqual(3, len(self.strategy.solution.actions))

        expected_actions = [
            {'action_type': 'change_nova_service_state',
             'input_parameters': {
                 'resource_id': node_0.uuid,
                 'resource_name': node_0.hostname,
                 'state': 'disabled',
                 'disabled_reason': 'watcher_maintaining'}},
            {'action_type': 'migrate',
             'input_parameters': {
                 'source_node': node_0.hostname,
                 'migration_type': 'live',
                 'resource_id': instance_0.uuid,
                 'resource_name': instance_0.name}},
            {'action_type': 'migrate',
             'input_parameters': {
                 'source_node': node_0.hostname,
                 'migration_type': 'live',
                 'resource_id': instance_1.uuid,
                 'resource_name': instance_1.name}}
        ]

        for action in expected_actions:
            self.assertIn(action, self.strategy.solution.actions)
