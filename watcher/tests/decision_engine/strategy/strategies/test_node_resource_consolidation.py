# -*- encoding: utf-8 -*-
# Copyright (c) 2019 ZTE Corporation
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
from watcher import objects
from watcher.tests.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy
from watcher.tests.objects import utils as obj_utils


class TestNodeResourceConsolidation(TestBaseStrategy):

    def setUp(self):
        super(TestNodeResourceConsolidation, self).setUp()
        self.strategy = strategies.NodeResourceConsolidation(
            config=mock.Mock())
        self.model = self.fake_c_cluster.generate_scenario_10()
        self.m_c_model.return_value = self.model
        self.strategy.input_parameters = {'host_choice': 'auto'}

    def test_pre_execute(self):
        planner = 'node_resource_consolidation'
        self.assertEqual('auto', self.strategy.host_choice)
        self.assertNotEqual(planner, self.strategy.planner)
        self.strategy.input_parameters.update(
            {'host_choice': 'specify'})
        self.strategy.pre_execute()
        self.assertEqual(planner, self.strategy.planner)
        self.assertEqual('specify', self.strategy.host_choice)

    def test_check_resources(self):
        instance = [self.model.get_instance_by_uuid(
            "6ae05517-a512-462d-9d83-90c313b5a8ff")]
        dest = self.model.get_node_by_uuid(
            "89dce55c-8e74-4402-b23f-32aaf216c972")
        # test destination is null
        result = self.strategy.check_resources(instance, [])
        self.assertFalse(result)

        result = self.strategy.check_resources(instance, dest)
        self.assertTrue(result)
        self.assertEqual([], instance)

    def test_select_destination(self):
        instance0 = self.model.get_instance_by_uuid(
            "6ae05517-a512-462d-9d83-90c313b5a8ff")
        source = self.model.get_node_by_instance_uuid(
            "6ae05517-a512-462d-9d83-90c313b5a8ff")
        expected = self.model.get_node_by_uuid(
            "89dce55c-8e74-4402-b23f-32aaf216c972")
        # test destination is null
        result = self.strategy.select_destination(instance0, source, [])
        self.assertIsNone(result)

        nodes = list(self.model.get_all_compute_nodes().values())
        nodes.remove(source)
        result = self.strategy.select_destination(instance0, source, nodes)
        self.assertEqual(expected, result)

    def test_add_migrate_actions_with_null(self):
        self.strategy.add_migrate_actions([], [])
        self.assertEqual([], self.strategy.solution.actions)
        self.strategy.add_migrate_actions(None, None)
        self.assertEqual([], self.strategy.solution.actions)

    def test_add_migrate_actions_with_auto(self):
        self.strategy.host_choice = 'auto'
        source = self.model.get_node_by_instance_uuid(
            "6ae05517-a512-462d-9d83-90c313b5a8ff")
        nodes = list(self.model.get_all_compute_nodes().values())
        nodes.remove(source)
        self.strategy.add_migrate_actions([source], nodes)
        expected = [{'action_type': 'migrate',
                     'input_parameters': {
                         'migration_type': 'live',
                         'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8f1',
                         'resource_name': 'INSTANCE_1',
                         'source_node': 'hostname_0'}},
                    {'action_type': 'migrate',
                     'input_parameters': {
                         'migration_type': 'live',
                         'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8ff',
                         'resource_name': 'INSTANCE_0',
                         'source_node': 'hostname_0'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_add_migrate_actions_with_specify(self):
        self.strategy.host_choice = 'specify'
        source = self.model.get_node_by_instance_uuid(
            "6ae05517-a512-462d-9d83-90c313b5a8ff")
        nodes = list(self.model.get_all_compute_nodes().values())
        nodes.remove(source)
        self.strategy.add_migrate_actions([source], nodes)
        expected = [{'action_type': 'migrate',
                     'input_parameters': {
                         'destination_node': 'hostname_1',
                         'migration_type': 'live',
                         'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8f1',
                         'resource_name': 'INSTANCE_1',
                         'source_node': 'hostname_0'}},
                    {'action_type': 'migrate',
                     'input_parameters': {
                         'destination_node': 'hostname_2',
                         'migration_type': 'live',
                         'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8ff',
                         'resource_name': 'INSTANCE_0',
                         'source_node': 'hostname_0'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_add_migrate_actions_with_no_action(self):
        self.strategy.host_choice = 'specify'
        source = self.model.get_node_by_uuid(
            "89dce55c-8e74-4402-b23f-32aaf216c971")
        dest = self.model.get_node_by_uuid(
            "89dce55c-8e74-4402-b23f-32aaf216c972")
        self.strategy.add_migrate_actions([source], [dest])
        self.assertEqual([], self.strategy.solution.actions)

    def test_add_change_node_state_actions_with_exeception(self):
        self.assertRaises(exception.IllegalArgumentException,
                          self.strategy.add_change_node_state_actions,
                          [], 'down')

    def test_add_change_node_state_actions(self):
        node1 = self.model.get_node_by_uuid(
            "89dce55c-8e74-4402-b23f-32aaf216c972")
        node2 = self.model.get_node_by_uuid(
            "89dce55c-8e74-4402-b23f-32aaf216c97f")
        # disable two nodes
        status = element.ServiceState.DISABLED.value
        result = self.strategy.add_change_node_state_actions(
            [node1, node2], status)
        self.assertEqual([node1, node2], result)
        expected = [{
            'action_type': 'change_nova_service_state',
            'input_parameters': {
                'disabled_reason': 'Watcher node resource '
                                   'consolidation strategy',
                'resource_id': '89dce55c-8e74-4402-b23f-32aaf216c972',
                'resource_name': 'hostname_2',
                'state': 'disabled'}},
            {
            'action_type': 'change_nova_service_state',
            'input_parameters': {
                'disabled_reason': 'Watcher node resource consolidation '
                                   'strategy',
                'resource_id': '89dce55c-8e74-4402-b23f-32aaf216c97f',
                'resource_name': 'hostname_0',
                'state': 'disabled'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_add_change_node_state_actions_one_disabled(self):
        node1 = self.model.get_node_by_uuid(
            "89dce55c-8e74-4402-b23f-32aaf216c972")
        node2 = self.model.get_node_by_uuid(
            "89dce55c-8e74-4402-b23f-32aaf216c97f")
        # disable two nodes
        status = element.ServiceState.DISABLED.value

        # one enable, one disable
        node1.status = element.ServiceState.DISABLED.value
        result = self.strategy.add_change_node_state_actions(
            [node1, node2], status)
        self.assertEqual([node2], result)
        expected = [{
            'action_type': 'change_nova_service_state',
            'input_parameters': {
                'disabled_reason': 'Watcher node resource consolidation '
                                   'strategy',
                'resource_id': '89dce55c-8e74-4402-b23f-32aaf216c97f',
                'resource_name': 'hostname_0',
                'state': 'disabled'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_get_nodes_migrate_failed_return_null(self):
        self.strategy.audit = None
        result = self.strategy.get_nodes_migrate_failed()
        self.assertEqual([], result)
        self.strategy.audit = mock.Mock(
            audit_type=objects.audit.AuditType.ONESHOT.value)
        result = self.strategy.get_nodes_migrate_failed()
        self.assertEqual([], result)

    @mock.patch.object(objects.action.Action, 'list')
    def test_get_nodes_migrate_failed(self, mock_list):
        self.strategy.audit = mock.Mock(
            audit_type=objects.audit.AuditType.CONTINUOUS.value)
        fake_action = obj_utils.get_test_action(
            self.context,
            state=objects.action.State.FAILED,
            action_type='migrate',
            input_parameters={
                'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8f1'})
        mock_list.return_value = [fake_action]
        result = self.strategy.get_nodes_migrate_failed()
        expected = self.model.get_node_by_uuid(
            '89dce55c-8e74-4402-b23f-32aaf216c97f')
        self.assertEqual([expected], result)

    def test_group_nodes_with_ONESHOT(self):
        self.strategy.audit = mock.Mock(
            audit_type=objects.audit.AuditType.ONESHOT.value)
        nodes = list(self.model.get_all_compute_nodes().values())
        result = self.strategy.group_nodes(nodes)
        node0 = self.model.get_node_by_name('hostname_0')
        node1 = self.model.get_node_by_name('hostname_1')
        node2 = self.model.get_node_by_name('hostname_2')
        node3 = self.model.get_node_by_name('hostname_3')
        node4 = self.model.get_node_by_name('hostname_4')
        node5 = self.model.get_node_by_name('hostname_5')
        node6 = self.model.get_node_by_name('hostname_6')
        node7 = self.model.get_node_by_name('hostname_7')
        source_nodes = [node3, node4, node7]
        dest_nodes = [node2, node0, node1]
        self.assertIn(node5, result[0])
        self.assertIn(node6, result[0])
        self.assertEqual(source_nodes, result[1])
        self.assertEqual(dest_nodes, result[2])

    @mock.patch.object(objects.action.Action, 'list')
    def test_group_nodes_with_CONTINUOUS(self, mock_list):
        self.strategy.audit = mock.Mock(
            audit_type=objects.audit.AuditType.CONTINUOUS.value)
        fake_action = obj_utils.get_test_action(
            self.context,
            state=objects.action.State.FAILED,
            action_type='migrate',
            input_parameters={
                'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8f6'})
        mock_list.return_value = [fake_action]
        nodes = list(self.model.get_all_compute_nodes().values())
        result = self.strategy.group_nodes(nodes)
        node0 = self.model.get_node_by_name('hostname_0')
        node1 = self.model.get_node_by_name('hostname_1')
        node2 = self.model.get_node_by_name('hostname_2')
        node3 = self.model.get_node_by_name('hostname_3')
        node4 = self.model.get_node_by_name('hostname_4')
        node5 = self.model.get_node_by_name('hostname_5')
        node6 = self.model.get_node_by_name('hostname_6')
        node7 = self.model.get_node_by_name('hostname_7')
        source_nodes = [node4, node7]
        dest_nodes = [node3, node2, node0, node1]
        self.assertIn(node5, result[0])
        self.assertIn(node6, result[0])
        self.assertEqual(source_nodes, result[1])
        self.assertEqual(dest_nodes, result[2])

    @mock.patch.object(objects.action.Action, 'list')
    def test_execute_with_auto(self, mock_list):
        fake_action = obj_utils.get_test_action(
            self.context,
            state=objects.action.State.FAILED,
            action_type='migrate',
            input_parameters={
                'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8f6'})
        mock_list.return_value = [fake_action]
        mock_audit = mock.Mock(
            audit_type=objects.audit.AuditType.CONTINUOUS.value)
        self.strategy.host_choice = 'auto'
        self.strategy.do_execute(mock_audit)
        expected = [
            {'action_type': 'change_nova_service_state',
             'input_parameters': {
                 'disabled_reason': 'Watcher node resource consolidation '
                                    'strategy',
                 'resource_id': '89dce55c-8e74-4402-b23f-32aaf216c975',
                 'resource_name': 'hostname_5',
                 'state': 'disabled'}},
            {'action_type': 'change_nova_service_state',
             'input_parameters': {
                 'disabled_reason': 'Watcher node resource consolidation '
                                    'strategy',
                 'resource_id': '89dce55c-8e74-4402-b23f-32aaf216c974',
                 'resource_name': 'hostname_4',
                 'state': 'disabled'}},
            {'action_type': 'migrate',
             'input_parameters': {
                 'migration_type': 'live',
                 'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8f7',
                 'resource_name': 'INSTANCE_7',
                 'source_node': 'hostname_4'}},
            {'action_type': 'migrate',
             'input_parameters': {
                 'migration_type': 'live',
                 'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8f8',
                 'resource_name': 'INSTANCE_8',
                 'source_node': 'hostname_7'}},
            {'action_type': 'change_nova_service_state',
             'input_parameters': {
                 'resource_id': '89dce55c-8e74-4402-b23f-32aaf216c975',
                 'resource_name': 'hostname_5',
                 'state': 'enabled'}},
            {'action_type': 'change_nova_service_state',
             'input_parameters': {
                 'resource_id': '89dce55c-8e74-4402-b23f-32aaf216c974',
                 'resource_name': 'hostname_4',
                 'state': 'enabled'}}]
        self.assertEqual(expected, self.strategy.solution.actions)

    def test_execute_with_specify(self):
        mock_audit = mock.Mock(
            audit_type=objects.audit.AuditType.ONESHOT.value)
        self.strategy.host_choice = 'specify'
        self.strategy.do_execute(mock_audit)
        expected = [
            {'action_type': 'migrate',
             'input_parameters': {
                 'destination_node': 'hostname_2',
                 'migration_type': 'live',
                 'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8f6',
                 'resource_name': 'INSTANCE_6',
                 'source_node': 'hostname_3'}},
            {'action_type': 'migrate',
             'input_parameters': {
                 'destination_node': 'hostname_0',
                 'migration_type': 'live',
                 'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8f7',
                 'resource_name': 'INSTANCE_7',
                 'source_node': 'hostname_4'}},
            {'action_type': 'migrate',
             'input_parameters': {
                 'destination_node': 'hostname_1',
                 'migration_type': 'live',
                 'resource_id': '6ae05517-a512-462d-9d83-90c313b5a8f8',
                 'resource_name': 'INSTANCE_8',
                 'source_node': 'hostname_7'}}]
        self.assertEqual(expected, self.strategy.solution.actions)
