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

from unittest import mock

from watcher.common import nova_helper
from watcher.common import utils
from watcher.db import api as db_api
from watcher.decision_engine.planner import weight as pbase
from watcher.decision_engine.solution import default as dsol
from watcher.decision_engine.strategy import strategies
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils as db_utils
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.decision_engine.model import gnocchi_metrics as fake
from watcher.tests.objects import utils as obj_utils


class SolutionFaker(object):
    @staticmethod
    def build():
        metrics = fake.FakerMetricsCollector()
        current_state_cluster = faker_cluster_state.FakerModelCollector()
        sercon = strategies.BasicConsolidation(config=mock.Mock())
        sercon.compute_model = current_state_cluster.generate_scenario_1()
        sercon.gnocchi = mock.MagicMock(
            get_statistics=metrics.mock_get_statistics)
        return sercon.execute()


class SolutionFakerSingleHyp(object):
    @staticmethod
    def build():
        metrics = fake.FakerMetricsCollector()
        current_state_cluster = faker_cluster_state.FakerModelCollector()
        sercon = strategies.BasicConsolidation(config=mock.Mock())
        sercon.compute_model = (
            current_state_cluster.generate_scenario_3_with_2_nodes())
        sercon.gnocchi = mock.MagicMock(
            get_statistics=metrics.mock_get_statistics)

        return sercon.execute()


class TestActionScheduling(base.DbTestCase):

    def setUp(self):
        super(TestActionScheduling, self).setUp()
        self.goal = db_utils.create_test_goal(name="dummy")
        self.strategy = db_utils.create_test_strategy(name="dummy")
        self.audit = db_utils.create_test_audit(
            uuid=utils.generate_uuid(), strategy_id=self.strategy.id)
        self.planner = pbase.WeightPlanner(
            mock.Mock(
                weights={
                    'turn_host_to_acpi_s3_state': 10,
                    'resize': 20,
                    'migrate': 30,
                    'sleep': 40,
                    'change_nova_service_state': 50,
                    'nop': 60,
                    'new_action_type': 70,
                },
                parallelization={
                    'turn_host_to_acpi_s3_state': 2,
                    'resize': 2,
                    'migrate': 2,
                    'sleep': 1,
                    'change_nova_service_state': 1,
                    'nop': 1,
                    'new_action_type': 70,
                }))

    @mock.patch.object(utils, "generate_uuid")
    def test_schedule_actions(self, m_generate_uuid):
        m_generate_uuid.side_effect = [
            "00000000-0000-0000-0000-000000000000",  # Action plan
            "11111111-1111-1111-1111-111111111111",  # Migrate 1
            "22222222-2222-2222-2222-222222222222",
            "33333333-3333-3333-3333-333333333333",
            # "44444444-4444-4444-4444-444444444444",
            # "55555555-5555-5555-5555-555555555555",
            # "66666666-6666-6666-6666-666666666666",
            # "77777777-7777-7777-7777-777777777777",
            # "88888888-8888-8888-8888-888888888888",
            # "99999999-9999-9999-9999-999999999999",
        ]
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server1",
                                              "destination_node": "server2"})

        self.planner.config.weights = {'migrate': 3}
        action_plan = self.planner.schedule(
            self.context, self.audit.id, solution)

        self.assertIsNotNone(action_plan.uuid)
        with mock.patch.object(
            pbase.WeightPlanner, "create_scheduled_actions",
            wraps=self.planner.create_scheduled_actions
        ) as m_create_scheduled_actions:
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(1, m_create_scheduled_actions.call_count)
        action_graph = m_create_scheduled_actions.call_args[0][0]

        expected_edges = []

        edges = sorted([(src.as_dict(), dst.as_dict())
                        for src, dst in action_graph.edges()],
                       key=lambda pair: pair[0]['uuid'])
        for src, dst in edges:
            for key in ('id', 'action_plan', 'action_plan_id', 'created_at',
                        'input_parameters', 'deleted_at', 'updated_at',
                        'state'):
                del src[key]
                del dst[key]

        self.assertEqual(len(expected_edges), len(edges))
        for pair in expected_edges:
            self.assertIn(pair, edges)

    @mock.patch.object(utils, "generate_uuid")
    def test_schedule_two_actions(self, m_generate_uuid):
        m_generate_uuid.side_effect = [
            "00000000-0000-0000-0000-000000000000",  # Action plan
            "11111111-1111-1111-1111-111111111111",
            "22222222-2222-2222-2222-222222222222",
            "33333333-3333-3333-3333-333333333333",
            "44444444-4444-4444-4444-444444444444",  # Migrate 1
            "55555555-5555-5555-5555-555555555555",  # Nop 1
        ]
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        # We create the migrate action before but we then schedule
        # after the nop action
        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server1",
                                              "destination_node": "server2"})

        solution.add_action(action_type="nop",
                            input_parameters={"message": "Hello world"})

        self.planner.config.weights = {'migrate': 3, 'nop': 5}

        action_plan = self.planner.schedule(
            self.context, self.audit.id, solution)

        self.assertIsNotNone(action_plan.uuid)
        with mock.patch.object(
            pbase.WeightPlanner, "create_scheduled_actions",
            wraps=self.planner.create_scheduled_actions
        ) as m_create_scheduled_actions:
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(1, m_create_scheduled_actions.call_count)
        action_graph = m_create_scheduled_actions.call_args[0][0]

        expected_edges = \
            [({'action_type': 'nop',
               'parents': [],
               'uuid': '55555555-5555-5555-5555-555555555555'},
              {'action_type': 'migrate',
               'parents': ['55555555-5555-5555-5555-555555555555'],
               'uuid': '44444444-4444-4444-4444-444444444444'})]

        edges = sorted([(src.as_dict(), dst.as_dict())
                        for src, dst in action_graph.edges()],
                       key=lambda pair: pair[0]['uuid'])
        for src, dst in edges:
            for key in ('id', 'action_plan', 'action_plan_id', 'created_at',
                        'input_parameters', 'deleted_at', 'updated_at',
                        'state'):
                del src[key]
                del dst[key]

        self.assertEqual(len(expected_edges), len(edges))
        for pair in expected_edges:
            self.assertIn(pair, edges)

    @mock.patch.object(utils, "generate_uuid")
    def test_schedule_actions_with_unknown_action(self, m_generate_uuid):
        m_generate_uuid.side_effect = [
            "00000000-0000-0000-0000-000000000000",  # Action plan
            "11111111-1111-1111-1111-111111111111",  # Migrate 1
            "22222222-2222-2222-2222-222222222222",  # new_action_type
            "33333333-3333-3333-3333-333333333333",

        ]
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "src_uuid_node": "server1",
            "dst_uuid_node": "server2",
        }
        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters=parameters)

        solution.add_action(action_type="new_action_type",
                            resource_id="",
                            input_parameters={})

        with mock.patch.object(
            pbase.WeightPlanner, "create_scheduled_actions",
            wraps=self.planner.create_scheduled_actions
        ) as m_create_scheduled_actions:
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(1, m_create_scheduled_actions.call_count)
        action_graph = m_create_scheduled_actions.call_args[0][0]

        expected_edges = \
            [({'action_type': 'new_action_type',
               'parents': [],
               'uuid': '22222222-2222-2222-2222-222222222222'},
              {'action_type': 'migrate',
               'parents': ['22222222-2222-2222-2222-222222222222'],
               'uuid': '11111111-1111-1111-1111-111111111111'})]

        edges = sorted([(src.as_dict(), dst.as_dict())
                        for src, dst in action_graph.edges()],
                       key=lambda pair: pair[0]['uuid'])
        for src, dst in edges:
            for key in ('id', 'action_plan', 'action_plan_id', 'created_at',
                        'input_parameters', 'deleted_at', 'updated_at',
                        'state'):
                del src[key]
                del dst[key]

        self.assertEqual(len(expected_edges), len(edges))
        for pair in expected_edges:
            self.assertIn(pair, edges)

    @mock.patch.object(utils, "generate_uuid")
    @mock.patch.object(nova_helper.NovaHelper, 'get_instance_by_uuid')
    def test_schedule_migrate_resize_actions(self, m_nova, m_generate_uuid):
        m_generate_uuid.side_effect = [
            "00000000-0000-0000-0000-000000000000",  # Action plan
            "11111111-1111-1111-1111-111111111111",  # Migrate 1
            "22222222-2222-2222-2222-222222222222",  # Migrate 2
            "33333333-3333-3333-3333-333333333333",  # Migrate 3
            "44444444-4444-4444-4444-444444444444",  # Migrate 4
            "55555555-5555-5555-5555-555555555555",  # Migrate 5
            "66666666-6666-6666-6666-666666666666",  # Resize 1
            "77777777-7777-7777-7777-777777777777",  # Resize 2
            "88888888-8888-8888-8888-888888888888",  # Nop
            "99999999-9999-9999-9999-999999999999",
        ]
        m_nova.return_value = 'server1'
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "source_node": "server1",
            "destination_node": "server2",
        }
        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters=parameters)

        solution.add_action(action_type="resize",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"flavor": "x1"})

        with mock.patch.object(
            pbase.WeightPlanner, "create_scheduled_actions",
            wraps=self.planner.create_scheduled_actions
        ) as m_create_scheduled_actions:
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(1, m_create_scheduled_actions.call_count)
        action_graph = m_create_scheduled_actions.call_args[0][0]

        expected_edges = \
            [({'action_type': 'migrate',
               'parents': [],
               'uuid': '11111111-1111-1111-1111-111111111111'},
              {'action_type': 'resize',
               'parents': ['11111111-1111-1111-1111-111111111111'],
               'uuid': '22222222-2222-2222-2222-222222222222'})]

        edges = sorted([(src.as_dict(), dst.as_dict())
                        for src, dst in action_graph.edges()],
                       key=lambda pair: pair[0]['uuid'])
        for src, dst in edges:
            for key in ('id', 'action_plan', 'action_plan_id', 'created_at',
                        'input_parameters', 'deleted_at', 'updated_at',
                        'state'):
                del src[key]
                del dst[key]

        self.assertEqual(len(expected_edges), len(edges))
        for pair in expected_edges:
            self.assertIn(pair, edges)

    @mock.patch.object(utils, "generate_uuid")
    def test_schedule_3_migrate_1_resize_1_acpi_actions_1_swimlane(
            self, m_generate_uuid):
        self.planner.config.parallelization["migrate"] = 1
        m_generate_uuid.side_effect = [
            "00000000-0000-0000-0000-000000000000",  # Action plan
            "11111111-1111-1111-1111-111111111111",  # Migrate 1
            "22222222-2222-2222-2222-222222222222",  # Migrate 2
            "33333333-3333-3333-3333-333333333333",  # Migrate 3
            "44444444-4444-4444-4444-444444444444",  # Resize
            "55555555-5555-5555-5555-555555555555",  # ACPI
            "66666666-6666-6666-6666-666666666666",
            "77777777-7777-7777-7777-777777777777",
            "88888888-8888-8888-8888-888888888888",
            "99999999-9999-9999-9999-999999999999",
        ]

        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "source_node": "server0",
            "destination_node": "server1",
        }
        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters=parameters)

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server1",
                                              "destination_node": "server2"})

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server2",
                                              "destination_node": "server3"})

        solution.add_action(action_type="resize",
                            resource_id="DOESNOTMATTER",
                            input_parameters={'flavor': 'x1'})

        solution.add_action(action_type="turn_host_to_acpi_s3_state",
                            resource_id="server1",
                            input_parameters={})

        with mock.patch.object(
            pbase.WeightPlanner, "create_scheduled_actions",
            wraps=self.planner.create_scheduled_actions
        ) as m_create_scheduled_actions:
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(1, m_create_scheduled_actions.call_count)
        action_graph = m_create_scheduled_actions.call_args[0][0]

        expected_edges = \
            [({'action_type': 'migrate',
               'parents': ['11111111-1111-1111-1111-111111111111'],
               'uuid': '22222222-2222-2222-2222-222222222222'},
              {'action_type': 'migrate',
               'parents': ['22222222-2222-2222-2222-222222222222'],
               'uuid': '33333333-3333-3333-3333-333333333333'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '11111111-1111-1111-1111-111111111111'},
              {'action_type': 'migrate',
               'parents': ['11111111-1111-1111-1111-111111111111'],
               'uuid': '22222222-2222-2222-2222-222222222222'}),
             ({'action_type': 'resize',
               'parents': ['33333333-3333-3333-3333-333333333333'],
               'uuid': '44444444-4444-4444-4444-444444444444'},
              {'action_type': 'turn_host_to_acpi_s3_state',
               'parents': ['44444444-4444-4444-4444-444444444444'],
               'uuid': '55555555-5555-5555-5555-555555555555'}),
             ({'action_type': 'migrate',
               'parents': ['22222222-2222-2222-2222-222222222222'],
               'uuid': '33333333-3333-3333-3333-333333333333'},
              {'action_type': 'resize',
               'parents': ['33333333-3333-3333-3333-333333333333'],
               'uuid': '44444444-4444-4444-4444-444444444444'})]

        edges = sorted([(src.as_dict(), dst.as_dict())
                        for src, dst in action_graph.edges()],
                       key=lambda pair: pair[0]['uuid'])
        for src, dst in edges:
            for key in ('id', 'action_plan', 'action_plan_id', 'created_at',
                        'input_parameters', 'deleted_at', 'updated_at',
                        'state'):
                del src[key]
                del dst[key]

        self.assertEqual(len(expected_edges), len(edges))
        for pair in expected_edges:
            self.assertIn(pair, edges)

    @mock.patch.object(utils, "generate_uuid")
    def test_schedule_migrate_resize_acpi_actions_2_swimlanes(
            self, m_generate_uuid):
        self.planner.config.parallelization["migrate"] = 2
        m_generate_uuid.side_effect = [
            "00000000-0000-0000-0000-000000000000",  # Action plan
            "11111111-1111-1111-1111-111111111111",  # Migrate 1
            "22222222-2222-2222-2222-222222222222",  # Migrate 2
            "33333333-3333-3333-3333-333333333333",  # Migrate 3
            "44444444-4444-4444-4444-444444444444",  # Resize
            "55555555-5555-5555-5555-555555555555",  # ACPI
            "66666666-6666-6666-6666-666666666666",
            "77777777-7777-7777-7777-777777777777",
            "88888888-8888-8888-8888-888888888888",
            "99999999-9999-9999-9999-999999999999",
        ]

        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "source_node": "server0",
            "destination_node": "server1",
        }
        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters=parameters)

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server1",
                                              "destination_node": "server2"})

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server2",
                                              "destination_node": "server3"})

        solution.add_action(action_type="resize",
                            resource_id="DOESNOTMATTER",
                            input_parameters={'flavor': 'x1'})

        solution.add_action(action_type="turn_host_to_acpi_s3_state",
                            resource_id="server1",
                            input_parameters={})

        with mock.patch.object(
            pbase.WeightPlanner, "create_scheduled_actions",
            wraps=self.planner.create_scheduled_actions
        ) as m_create_scheduled_actions:
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(1, m_create_scheduled_actions.call_count)
        action_graph = m_create_scheduled_actions.call_args[0][0]

        expected_edges = \
            [({'action_type': 'migrate',
               'parents': [],
               'uuid': '11111111-1111-1111-1111-111111111111'},
              {'action_type': 'migrate',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222'],
               'uuid': '33333333-3333-3333-3333-333333333333'}),
             ({'action_type': 'resize',
               'parents': ['33333333-3333-3333-3333-333333333333'],
               'uuid': '44444444-4444-4444-4444-444444444444'},
              {'action_type': 'turn_host_to_acpi_s3_state',
               'parents': ['44444444-4444-4444-4444-444444444444'],
               'uuid': '55555555-5555-5555-5555-555555555555'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '22222222-2222-2222-2222-222222222222'},
              {'action_type': 'migrate',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222'],
               'uuid': '33333333-3333-3333-3333-333333333333'}),
             ({'action_type': 'migrate',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222'],
               'uuid': '33333333-3333-3333-3333-333333333333'},
              {'action_type': 'resize',
               'parents': ['33333333-3333-3333-3333-333333333333'],
               'uuid': '44444444-4444-4444-4444-444444444444'})]

        edges = sorted([(src.as_dict(), dst.as_dict())
                        for src, dst in action_graph.edges()],
                       key=lambda pair: pair[0]['uuid'])
        for src, dst in edges:
            for key in ('id', 'action_plan', 'action_plan_id', 'created_at',
                        'input_parameters', 'deleted_at', 'updated_at',
                        'state'):
                del src[key]
                del dst[key]

        self.assertEqual(len(expected_edges), len(edges))
        for pair in expected_edges:
            self.assertIn(pair, edges)

    @mock.patch.object(utils, "generate_uuid")
    def test_schedule_migrate_resize_acpi_actions_3_swimlanes(
            self, m_generate_uuid):
        self.planner.config.parallelization["migrate"] = 3
        m_generate_uuid.side_effect = [
            "00000000-0000-0000-0000-000000000000",  # Action plan
            "11111111-1111-1111-1111-111111111111",  # Migrate 1
            "22222222-2222-2222-2222-222222222222",  # Migrate 2
            "33333333-3333-3333-3333-333333333333",  # Migrate 3
            "44444444-4444-4444-4444-444444444444",  # Resize
            "55555555-5555-5555-5555-555555555555",  # ACPI
            "66666666-6666-6666-6666-666666666666",
            "77777777-7777-7777-7777-777777777777",
            "88888888-8888-8888-8888-888888888888",
            "99999999-9999-9999-9999-999999999999",
        ]

        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "source_node": "server0",
            "destination_node": "server1",
        }
        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters=parameters)

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server1",
                                              "destination_node": "server2"})

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server2",
                                              "destination_node": "server3"})

        solution.add_action(action_type="resize",
                            resource_id="DOESNOTMATTER",
                            input_parameters={'flavor': 'x1'})

        solution.add_action(action_type="turn_host_to_acpi_s3_state",
                            resource_id="server1",
                            input_parameters={})

        with mock.patch.object(
            pbase.WeightPlanner, "create_scheduled_actions",
            wraps=self.planner.create_scheduled_actions
        ) as m_create_scheduled_actions:
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(1, m_create_scheduled_actions.call_count)
        action_graph = m_create_scheduled_actions.call_args[0][0]

        expected_edges = \
            [({'action_type': 'resize',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222',
                           '33333333-3333-3333-3333-333333333333'],
               'uuid': '44444444-4444-4444-4444-444444444444'},
              {'action_type': 'turn_host_to_acpi_s3_state',
               'parents': ['44444444-4444-4444-4444-444444444444'],
               'uuid': '55555555-5555-5555-5555-555555555555'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '11111111-1111-1111-1111-111111111111'},
              {'action_type': 'resize',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222',
                           '33333333-3333-3333-3333-333333333333'],
               'uuid': '44444444-4444-4444-4444-444444444444'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '22222222-2222-2222-2222-222222222222'},
              {'action_type': 'resize',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222',
                           '33333333-3333-3333-3333-333333333333'],
               'uuid': '44444444-4444-4444-4444-444444444444'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '33333333-3333-3333-3333-333333333333'},
              {'action_type': 'resize',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222',
                           '33333333-3333-3333-3333-333333333333'],
               'uuid': '44444444-4444-4444-4444-444444444444'})]

        edges = sorted([(src.as_dict(), dst.as_dict())
                        for src, dst in action_graph.edges()],
                       key=lambda pair: pair[0]['uuid'])
        for src, dst in edges:
            for key in ('id', 'action_plan', 'action_plan_id', 'created_at',
                        'input_parameters', 'deleted_at', 'updated_at',
                        'state'):
                del src[key]
                del dst[key]

        self.assertEqual(len(expected_edges), len(edges))
        for pair in expected_edges:
            self.assertIn(pair, edges)

    @mock.patch.object(utils, "generate_uuid")
    def test_schedule_three_migrate_two_resize_actions(
            self, m_generate_uuid):
        self.planner.config.parallelization["migrate"] = 3
        self.planner.config.parallelization["resize"] = 2
        m_generate_uuid.side_effect = [
            "00000000-0000-0000-0000-000000000000",  # Action plan
            "11111111-1111-1111-1111-111111111111",  # Migrate 1
            "22222222-2222-2222-2222-222222222222",  # Migrate 2
            "33333333-3333-3333-3333-333333333333",  # Migrate 3
            "44444444-4444-4444-4444-444444444444",  # Resize
            "55555555-5555-5555-5555-555555555555",  # ACPI
            "66666666-6666-6666-6666-666666666666",
            "77777777-7777-7777-7777-777777777777",
            "88888888-8888-8888-8888-888888888888",
            "99999999-9999-9999-9999-999999999999",
        ]

        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "source_node": "server0",
            "destination_node": "server1",
        }
        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters=parameters)

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server1",
                                              "destination_node": "server2"})

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server2",
                                              "destination_node": "server3"})

        solution.add_action(action_type="resize",
                            resource_id="DOESNOTMATTER",
                            input_parameters={'flavor': 'x1'})

        solution.add_action(action_type="resize",
                            resource_id="b189db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters={'flavor': 'x1'})

        with mock.patch.object(
            pbase.WeightPlanner, "create_scheduled_actions",
            wraps=self.planner.create_scheduled_actions
        ) as m_create_scheduled_actions:
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(1, m_create_scheduled_actions.call_count)
        action_graph = m_create_scheduled_actions.call_args[0][0]

        expected_edges = \
            [({'action_type': 'migrate',
               'parents': [],
               'uuid': '11111111-1111-1111-1111-111111111111'},
              {'action_type': 'resize',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222',
                           '33333333-3333-3333-3333-333333333333'],
               'uuid': '55555555-5555-5555-5555-555555555555'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '11111111-1111-1111-1111-111111111111'},
              {'action_type': 'resize',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222',
                           '33333333-3333-3333-3333-333333333333'],
               'uuid': '55555555-5555-5555-5555-555555555555'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '22222222-2222-2222-2222-222222222222'},
              {'action_type': 'resize',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222',
                           '33333333-3333-3333-3333-333333333333'],
               'uuid': '55555555-5555-5555-5555-555555555555'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '22222222-2222-2222-2222-222222222222'},
              {'action_type': 'resize',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222',
                           '33333333-3333-3333-3333-333333333333'],
               'uuid': '55555555-5555-5555-5555-555555555555'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '33333333-3333-3333-3333-333333333333'},
              {'action_type': 'resize',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222',
                           '33333333-3333-3333-3333-333333333333'],
               'uuid': '55555555-5555-5555-5555-555555555555'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '33333333-3333-3333-3333-333333333333'},
              {'action_type': 'resize',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222',
                           '33333333-3333-3333-3333-333333333333'],
               'uuid': '55555555-5555-5555-5555-555555555555'})]

        edges = sorted([(src.as_dict(), dst.as_dict())
                        for src, dst in action_graph.edges()],
                       key=lambda pair: pair[0]['uuid'])
        for src, dst in edges:
            for key in ('id', 'action_plan', 'action_plan_id', 'created_at',
                        'input_parameters', 'deleted_at', 'updated_at',
                        'state'):
                del src[key]
                del dst[key]

        self.assertEqual(len(expected_edges), len(edges))
        for pair in expected_edges:
            self.assertIn(pair, edges)

    @mock.patch.object(utils, "generate_uuid")
    def test_schedule_5_migrate_2_resize_actions_for_2_swimlanes(
            self, m_generate_uuid):
        self.planner.config.parallelization["migrate"] = 2
        self.planner.config.parallelization["resize"] = 2
        m_generate_uuid.side_effect = [
            "00000000-0000-0000-0000-000000000000",  # Action plan
            "11111111-1111-1111-1111-111111111111",  # Migrate 1
            "22222222-2222-2222-2222-222222222222",  # Migrate 2
            "33333333-3333-3333-3333-333333333333",  # Migrate 3
            "44444444-4444-4444-4444-444444444444",  # Migrate 4
            "55555555-5555-5555-5555-555555555555",  # Migrate 5
            "66666666-6666-6666-6666-666666666666",  # Resize 1
            "77777777-7777-7777-7777-777777777777",  # Resize 2
            "88888888-8888-8888-8888-888888888888",  # Nop
            "99999999-9999-9999-9999-999999999999",
        ]

        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server1",
                                              "destination_node": "server6"})

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server2",
                                              "destination_node": "server6"})

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server3",
                                              "destination_node": "server6"})

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server4",
                                              "destination_node": "server6"})

        solution.add_action(action_type="migrate",
                            resource_id="DOESNOTMATTER",
                            input_parameters={"source_node": "server5",
                                              "destination_node": "server6"})

        solution.add_action(action_type="resize",
                            resource_id="DOESNOTMATTER",
                            input_parameters={'flavor': 'x1'})

        solution.add_action(action_type="resize",
                            resource_id="DOESNOTMATTER",
                            input_parameters={'flavor': 'x2'})

        solution.add_action(action_type="turn_host_to_acpi_s3_state",
                            resource_id="DOESNOTMATTER")

        with mock.patch.object(
            pbase.WeightPlanner, "create_scheduled_actions",
            wraps=self.planner.create_scheduled_actions
        ) as m_create_scheduled_actions:
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(1, m_create_scheduled_actions.call_count)
        action_graph = m_create_scheduled_actions.call_args[0][0]

        expected_edges = \
            [({'action_type': 'migrate',
               'parents': [],
               'uuid': '11111111-1111-1111-1111-111111111111'},
              {'action_type': 'migrate',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222'],
               'uuid': '33333333-3333-3333-3333-333333333333'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '11111111-1111-1111-1111-111111111111'},
              {'action_type': 'migrate',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222'],
               'uuid': '44444444-4444-4444-4444-444444444444'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '22222222-2222-2222-2222-222222222222'},
              {'action_type': 'migrate',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222'],
               'uuid': '33333333-3333-3333-3333-333333333333'}),
             ({'action_type': 'migrate',
               'parents': [],
               'uuid': '22222222-2222-2222-2222-222222222222'},
              {'action_type': 'migrate',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222'],
               'uuid': '44444444-4444-4444-4444-444444444444'}),
             ({'action_type': 'migrate',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222'],
               'uuid': '33333333-3333-3333-3333-333333333333'},
              {'action_type': 'migrate',
               'parents': ['33333333-3333-3333-3333-333333333333',
                           '44444444-4444-4444-4444-444444444444'],
               'uuid': '55555555-5555-5555-5555-555555555555'}),
             ({'action_type': 'migrate',
               'parents': ['11111111-1111-1111-1111-111111111111',
                           '22222222-2222-2222-2222-222222222222'],
               'uuid': '44444444-4444-4444-4444-444444444444'},
              {'action_type': 'migrate',
               'parents': ['33333333-3333-3333-3333-333333333333',
                           '44444444-4444-4444-4444-444444444444'],
               'uuid': '55555555-5555-5555-5555-555555555555'}),
             ({'action_type': 'migrate',
               'parents': ['33333333-3333-3333-3333-333333333333',
                           '44444444-4444-4444-4444-444444444444'],
               'uuid': '55555555-5555-5555-5555-555555555555'},
              {'action_type': 'resize',
               'parents': ['55555555-5555-5555-5555-555555555555'],
               'uuid': '66666666-6666-6666-6666-666666666666'}),
             ({'action_type': 'migrate',
               'parents': ['33333333-3333-3333-3333-333333333333',
                           '44444444-4444-4444-4444-444444444444'],
               'uuid': '55555555-5555-5555-5555-555555555555'},
              {'action_type': 'resize',
               'parents': ['55555555-5555-5555-5555-555555555555'],
               'uuid': '77777777-7777-7777-7777-777777777777'}),
             ({'action_type': 'resize',
               'parents': ['55555555-5555-5555-5555-555555555555'],
               'uuid': '66666666-6666-6666-6666-666666666666'},
              {'action_type': 'turn_host_to_acpi_s3_state',
               'parents': ['66666666-6666-6666-6666-666666666666',
                           '77777777-7777-7777-7777-777777777777'],
               'uuid': '88888888-8888-8888-8888-888888888888'}),
             ({'action_type': 'resize',
               'parents': ['55555555-5555-5555-5555-555555555555'],
               'uuid': '77777777-7777-7777-7777-777777777777'},
              {'action_type': 'turn_host_to_acpi_s3_state',
               'parents': ['66666666-6666-6666-6666-666666666666',
                           '77777777-7777-7777-7777-777777777777'],
               'uuid': '88888888-8888-8888-8888-888888888888'})]

        edges = sorted([(src.as_dict(), dst.as_dict())
                        for src, dst in action_graph.edges()],
                       key=lambda pair: pair[0]['uuid'])
        for src, dst in edges:
            for key in ('id', 'action_plan', 'action_plan_id', 'created_at',
                        'input_parameters', 'deleted_at', 'updated_at',
                        'state'):
                del src[key]
                del dst[key]

        self.assertEqual(len(expected_edges), len(edges))
        for pair in expected_edges:
            self.assertIn(pair, edges)


class TestWeightPlanner(base.DbTestCase):

    def setUp(self):
        super(TestWeightPlanner, self).setUp()
        self.planner = pbase.WeightPlanner(mock.Mock())
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
