# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

from watcher.common import exception
from watcher.common import nova_helper
from watcher.common import utils
from watcher.db import api as db_api
from watcher.decision_engine.planner import workload_stabilization as pbase
from watcher.decision_engine.solution import default as dsol
from watcher.decision_engine.strategy import strategies
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils as db_utils
from watcher.tests.decision_engine.model import ceilometer_metrics as fake
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.objects import utils as obj_utils


class SolutionFaker(object):
    @staticmethod
    def build():
        metrics = fake.FakerMetricsCollector()
        current_state_cluster = faker_cluster_state.FakerModelCollector()
        sercon = strategies.BasicConsolidation(config=mock.Mock())
        sercon._compute_model = current_state_cluster.generate_scenario_1()
        sercon.ceilometer = mock.MagicMock(
            get_statistics=metrics.mock_get_statistics)
        return sercon.execute()


class SolutionFakerSingleHyp(object):
    @staticmethod
    def build():
        metrics = fake.FakerMetricsCollector()
        current_state_cluster = faker_cluster_state.FakerModelCollector()
        sercon = strategies.BasicConsolidation(config=mock.Mock())
        sercon._compute_model = (
            current_state_cluster.generate_scenario_3_with_2_nodes())
        sercon.ceilometer = mock.MagicMock(
            get_statistics=metrics.mock_get_statistics)

        return sercon.execute()


class TestActionScheduling(base.DbTestCase):

    def setUp(self):
        super(TestActionScheduling, self).setUp()
        self.goal = db_utils.create_test_goal(name="dummy")
        self.strategy = db_utils.create_test_strategy(name="dummy")
        self.audit = db_utils.create_test_audit(
            uuid=utils.generate_uuid(), strategy_id=self.strategy.id)
        self.planner = pbase.WorkloadStabilizationPlanner(mock.Mock())
        self.nova_helper = nova_helper.NovaHelper(mock.Mock())

    def test_schedule_actions(self):
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "source_node": "server1",
            "destination_node": "server2",
        }
        solution.add_action(action_type="migrate",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters=parameters)

        with mock.patch.object(
            pbase.WorkloadStabilizationPlanner, "create_action",
            wraps=self.planner.create_action
        ) as m_create_action:
            self.planner.config.weights = {'migrate': 3}
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)

        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(1, m_create_action.call_count)
        filters = {'action_plan_id': action_plan.id}
        actions = objects.Action.dbapi.get_action_list(self.context, filters)
        self.assertEqual("migrate", actions[0].action_type)

    def test_schedule_two_actions(self):
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "source_node": "server1",
            "destination_node": "server2",
        }
        solution.add_action(action_type="migrate",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters=parameters)

        solution.add_action(action_type="nop",
                            input_parameters={"message": "Hello world"})

        with mock.patch.object(
            pbase.WorkloadStabilizationPlanner, "create_action",
            wraps=self.planner.create_action
        ) as m_create_action:
            self.planner.config.weights = {'migrate': 3, 'nop': 5}
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(2, m_create_action.call_count)
        # check order
        filters = {'action_plan_id': action_plan.id}
        actions = objects.Action.dbapi.get_action_list(self.context, filters)
        self.assertEqual("nop", actions[0].action_type)
        self.assertEqual("migrate", actions[1].action_type)

    def test_schedule_actions_with_unknown_action(self):
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "src_uuid_node": "server1",
            "dst_uuid_node": "server2",
        }
        solution.add_action(action_type="migrate",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters=parameters)

        solution.add_action(action_type="new_action_type",
                            resource_id="",
                            input_parameters={})

        with mock.patch.object(
            pbase.WorkloadStabilizationPlanner, "create_action",
            wraps=self.planner.create_action
        ) as m_create_action:
            with mock.patch.object(nova_helper, 'NovaHelper') as m_nova:
                self.planner.config.weights = {'migrate': 0}
                self.assertRaises(KeyError, self.planner.schedule,
                                  self.context, self.audit.id, solution)
                assert not m_nova.called
        self.assertEqual(2, m_create_action.call_count)

    def test_schedule_actions_with_unsupported_action(self):
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "src_uuid_node": "server1",
            "dst_uuid_node": "server2",
        }
        solution.add_action(action_type="migrate",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters=parameters)

        solution.add_action(action_type="new_action_type",
                            resource_id="",
                            input_parameters={})
        with mock.patch.object(
            pbase.WorkloadStabilizationPlanner, "create_action",
            wraps=self.planner.create_action
        ) as m_create_action:
            with mock.patch.object(nova_helper, 'NovaHelper') as m_nova:
                self.planner.config.weights = {
                    'turn_host_to_acpi_s3_state': 0,
                    'resize': 1,
                    'migrate': 2,
                    'sleep': 3,
                    'change_nova_service_state': 4,
                    'nop': 5,
                    'new_action_type': 6}
                self.assertRaises(exception.UnsupportedActionType,
                                  self.planner.schedule,
                                  self.context, self.audit.id, solution)
                assert not m_nova.called
        self.assertEqual(2, m_create_action.call_count)

    @mock.patch.object(nova_helper.NovaHelper, 'get_instance_by_uuid')
    def test_schedule_migrate_resize_actions(self, mock_nova):
        mock_nova.return_value = 'server1'
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "source_node": "server1",
            "destination_node": "server2",
        }
        solution.add_action(action_type="migrate",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters=parameters)

        solution.add_action(action_type="resize",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters={"flavor": "x1"})

        with mock.patch.object(
                pbase.WorkloadStabilizationPlanner, "create_action",
                wraps=self.planner.create_action
        ) as m_create_action:
            with mock.patch.object(nova_helper, 'NovaHelper') as m_nova:
                self.planner.config.weights = {'migrate': 3, 'resize': 2}
                action_plan = self.planner.schedule(
                    self.context, self.audit.id, solution)
                self.assertEqual(1, m_nova.call_count)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(2, m_create_action.call_count)
        # check order
        filters = {'action_plan_id': action_plan.id}
        actions = objects.Action.dbapi.get_action_list(self.context, filters)
        self.assertEqual("migrate", actions[0].action_type)
        self.assertEqual("resize", actions[1].action_type)
        self.assertEqual(actions[0].uuid, actions[1].parents[0])

    def test_schedule_migrate_resize_acpi_s3_actions(self):
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "source_node": "server1",
            "destination_node": "server2",
        }
        parent_migration = "b199db0c-1408-4d52-b5a5-5ca14de0ff36"
        solution.add_action(action_type="migrate",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters=parameters)

        solution.add_action(action_type="resize",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters={'flavor': 'x1'})

        solution.add_action(action_type="migrate",
                            resource_id="f6416850-da28-4047-a547-8c49f53e95fe",
                            input_parameters={"source_node": "server1",
                                              "destination_node": "server2"})

        solution.add_action(action_type="migrate",
                            resource_id="bb404e74-2caf-447b-bd1e-9234db386ca5",
                            input_parameters={"source_node": "server2",
                                              "destination_node": "server3"})

        solution.add_action(action_type="turn_host_to_acpi_s3_state",
                            resource_id="server1",
                            input_parameters={})

        with mock.patch.object(
                pbase.WorkloadStabilizationPlanner, "create_action",
                wraps=self.planner.create_action
        ) as m_create_action:
            with mock.patch.object(
                    nova_helper, 'NovaHelper') as m_nova:
                m_nova().get_hostname.return_value = 'server1'
                m_nova().get_instance_by_uuid.return_value = ['uuid1']
                self.planner.config.weights = {
                    'turn_host_to_acpi_s3_state': 0,
                    'resize': 1,
                    'migrate': 2,
                    'sleep': 3,
                    'change_nova_service_state': 4,
                    'nop': 5}
                action_plan = self.planner.schedule(
                    self.context, self.audit.id, solution)
                self.assertEqual(3, m_nova.call_count)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(5, m_create_action.call_count)
        # check order
        filters = {'action_plan_id': action_plan.id}
        actions = objects.Action.dbapi.get_action_list(self.context, filters)
        self.assertEqual("migrate", actions[0].action_type)
        self.assertEqual("migrate", actions[1].action_type)
        self.assertEqual("migrate", actions[2].action_type)
        self.assertEqual("resize", actions[3].action_type)
        self.assertEqual("turn_host_to_acpi_s3_state", actions[4].action_type)
        for action in actions:
            if action.input_parameters['resource_id'] == parent_migration:
                parent_migration = action
                break
        self.assertEqual(parent_migration.uuid, actions[3].parents[0])


class TestDefaultPlanner(base.DbTestCase):

    def setUp(self):
        super(TestDefaultPlanner, self).setUp()
        self.planner = pbase.WorkloadStabilizationPlanner(mock.Mock())
        self.planner.config.weights = {
            'nop': 0,
            'sleep': 1,
            'change_nova_service_state': 2,
            'migrate': 3
        }

        self.goal = obj_utils.create_test_goal(self.context)
        self.strategy = obj_utils.create_test_strategy(
            self.context, goal_id=self.goal.id)
        obj_utils.create_test_audit_template(
            self.context, goal_id=self.goal.id, strategy_id=self.strategy.id)

        p = mock.patch.object(db_api.BaseConnection, 'create_action_plan')
        self.mock_create_action_plan = p.start()
        self.mock_create_action_plan.side_effect = (
            self._simulate_action_plan_create)
        self.addCleanup(p.stop)

        q = mock.patch.object(db_api.BaseConnection, 'create_action')
        self.mock_create_action = q.start()
        self.mock_create_action.side_effect = (
            self._simulate_action_create)
        self.addCleanup(q.stop)

    def _simulate_action_plan_create(self, action_plan):
        action_plan.create()
        return action_plan

    def _simulate_action_create(self, action):
        action.create()
        return action

    @mock.patch.object(objects.Strategy, 'get_by_name')
    def test_scheduler_warning_empty_action_plan(self, m_get_by_name):
        m_get_by_name.return_value = self.strategy
        audit = db_utils.create_test_audit(
            goal_id=self.goal.id, strategy_id=self.strategy.id)
        fake_solution = mock.MagicMock(efficacy_indicators=[],
                                       actions=[])
        action_plan = self.planner.schedule(
            self.context, audit.id, fake_solution)
        self.assertIsNotNone(action_plan.uuid)


class TestActionValidator(base.DbTestCase):
    INSTANCE_UUID = "94ae2f92-b7fd-4da7-9e97-f13504ae98c4"

    def setUp(self):
        super(TestActionValidator, self).setUp()
        self.r_osc_cls = mock.Mock()
        self.r_helper_cls = mock.Mock()
        self.r_helper = mock.Mock(spec=nova_helper.NovaHelper)
        self.r_helper_cls.return_value = self.r_helper
        r_nova_helper = mock.patch.object(
            nova_helper, "NovaHelper", self.r_helper_cls)

        r_nova_helper.start()

        self.addCleanup(r_nova_helper.stop)

    def test_resize_validate_parents(self):
        resize_object = pbase.ResizeActionValidator()
        action = {'uuid': 'fcec56cd-74c1-406b-a7c1-81ef9f0c1393',
                  'input_parameters': {'resource_id': self.INSTANCE_UUID}}
        resource_action_map = {self.INSTANCE_UUID: [
            ('action_uuid', 'migrate')]}
        self.r_helper.get_hostname.return_value = 'server1'
        self.r_helper.get_instance_by_uuid.return_value = ['instance']
        result = resize_object.validate_parents(resource_action_map, action)
        self.assertEqual('action_uuid', result[0])

    def test_migrate_validate_parents(self):
        migrate_object = pbase.MigrationActionValidator()
        action = {'uuid': '712f1701-4c1b-4076-bfcf-3f23cfec6c3b',
                  'input_parameters': {'source_node': 'server1',
                                       'resource_id': self.INSTANCE_UUID}}
        resource_action_map = {}
        expected_map = {
            '94ae2f92-b7fd-4da7-9e97-f13504ae98c4': [
                ('712f1701-4c1b-4076-bfcf-3f23cfec6c3b', 'migrate')],
            'server1': [
                ('712f1701-4c1b-4076-bfcf-3f23cfec6c3b', 'migrate')]}
        migrate_object.validate_parents(resource_action_map, action)
        self.assertEqual(resource_action_map, expected_map)
