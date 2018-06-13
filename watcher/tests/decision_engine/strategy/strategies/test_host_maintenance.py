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
from watcher.decision_engine.model import model_root
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.model import faker_cluster_state


class TestHostMaintenance(base.TestCase):

    def setUp(self):
        super(TestHostMaintenance, self).setUp()

        # fake cluster
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

        p_model = mock.patch.object(
            strategies.HostMaintenance, "compute_model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        p_audit_scope = mock.patch.object(
            strategies.HostMaintenance, "audit_scope",
            new_callable=mock.PropertyMock
        )
        self.m_audit_scope = p_audit_scope.start()
        self.addCleanup(p_audit_scope.stop)

        self.m_audit_scope.return_value = mock.Mock()

        self.m_model.return_value = model_root.ModelRoot()
        self.strategy = strategies.HostMaintenance(config=mock.Mock())

    def test_exception_stale_cdm(self):
        self.fake_cluster.set_cluster_data_model_as_stale()
        self.m_model.return_value = self.fake_cluster.cluster_data_model

        self.assertRaises(
            exception.ClusterStateNotDefined,
            self.strategy.execute)

    def test_get_node_capacity(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_capacity = dict(cpu=40, ram=132, disk=250)
        self.assertEqual(node_capacity,
                         self.strategy.get_node_capacity(node_0))

    def test_get_node_used(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_used = dict(cpu=20, ram=4, disk=40)
        self.assertEqual(node_used,
                         self.strategy.get_node_used(node_0))

    def test_get_node_free(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_free = dict(cpu=20, ram=128, disk=210)
        self.assertEqual(node_free,
                         self.strategy.get_node_free(node_0))

    def test_host_fits(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_0 = model.get_node_by_uuid("Node_0")
        node_1 = model.get_node_by_uuid("Node_1")
        self.assertTrue(self.strategy.host_fits(node_0, node_1))

    def test_add_action_enable_compute_node(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        self.strategy.add_action_enable_compute_node(node_0)
        expected = [{'action_type': 'change_nova_service_state',
                     'input_parameters': {
                         'state': 'enabled',
                         'resource_id': 'Node_0'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_add_action_maintain_compute_node(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        self.strategy.add_action_maintain_compute_node(node_0)
        expected = [{'action_type': 'change_nova_service_state',
                     'input_parameters': {
                         'state': 'disabled',
                         'disabled_reason': 'watcher_maintaining',
                         'resource_id': 'Node_0'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_instance_migration(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        self.strategy.instance_migration(instance_0, node_0, node_1)
        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'destination_node': node_1.uuid,
                                          'source_node': node_0.uuid,
                                          'migration_type': 'live',
                                          'resource_id': instance_0.uuid}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_instance_migration_without_dest_node(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        self.strategy.instance_migration(instance_0, node_0)
        self.assertEqual(1, len(self.strategy.solution.actions))
        expected = [{'action_type': 'migrate',
                     'input_parameters': {'source_node': node_0.uuid,
                                          'migration_type': 'live',
                                          'resource_id': instance_0.uuid}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_host_migration(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
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
                                          'resource_id': instance_0.uuid}},
                    {'action_type': 'migrate',
                     'input_parameters': {'destination_node': node_1.uuid,
                                          'source_node': node_0.uuid,
                                          'migration_type': 'live',
                                          'resource_id': instance_1.uuid}}]
        self.assertIn(expected[0], self.strategy.solution.actions)
        self.assertIn(expected[1], self.strategy.solution.actions)

    def test_safe_maintain(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_0 = model.get_node_by_uuid('Node_0')
        node_1 = model.get_node_by_uuid('Node_1')
        self.assertFalse(self.strategy.safe_maintain(node_0))
        self.assertFalse(self.strategy.safe_maintain(node_1))

    def test_try_maintain(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_1 = model.get_node_by_uuid('Node_1')
        self.strategy.try_maintain(node_1)
        self.assertEqual(2, len(self.strategy.solution.actions))

    def test_strategy(self):
        model = self.fake_cluster. \
            generate_scenario_9_with_3_active_plus_1_disabled_nodes()
        self.m_model.return_value = model
        node_2 = model.get_node_by_uuid('Node_2')
        node_3 = model.get_node_by_uuid('Node_3')
        instance_4 = model.get_instance_by_uuid("INSTANCE_4")
        if not self.strategy.safe_maintain(node_2, node_3):
            self.strategy.try_maintain(node_2)
        expected = [{'action_type': 'change_nova_service_state',
                     'input_parameters': {
                         'resource_id': 'Node_3',
                         'state': 'enabled'}},
                    {'action_type': 'change_nova_service_state',
                     'input_parameters': {
                         'resource_id': 'Node_2',
                         'state': 'disabled',
                         'disabled_reason': 'watcher_maintaining'}},
                    {'action_type': 'migrate',
                     'input_parameters': {
                         'destination_node': node_3.uuid,
                         'source_node': node_2.uuid,
                         'migration_type': 'live',
                         'resource_id': instance_4.uuid}}]
        self.assertEqual(expected, self.strategy.solution.actions)
