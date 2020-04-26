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

from unittest import mock

from watcher.common import exception
from watcher.common import utils
from watcher.db import api as db_api
from watcher.decision_engine.planner import \
    node_resource_consolidation as pbase
from watcher.decision_engine.solution import default as dsol
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils as db_utils
from watcher.tests.objects import utils as obj_utils


class TestActionScheduling(base.DbTestCase):

    def setUp(self):
        super(TestActionScheduling, self).setUp()
        self.goal = db_utils.create_test_goal(name="server_consolidation")
        self.strategy = db_utils.create_test_strategy(
            name="node_resource_consolidation")
        self.audit = db_utils.create_test_audit(
            uuid=utils.generate_uuid(), strategy_id=self.strategy.id)
        self.planner = pbase.NodeResourceConsolidationPlanner(mock.Mock())

    def test_schedule_actions(self):
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "source_node": "host1",
            "destination_node": "host2",
        }
        solution.add_action(action_type="migrate",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters=parameters)

        with mock.patch.object(
            pbase.NodeResourceConsolidationPlanner, "create_action",
            wraps=self.planner.create_action
        ) as m_create_action:
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

        server1_uuid = "b199db0c-1408-4d52-b5a5-5ca14de0ff36"
        server2_uuid = "b199db0c-1408-4d52-b5a5-5ca14de0ff37"
        solution.add_action(action_type="migrate",
                            resource_id=server1_uuid,
                            input_parameters={
                                "source_node": "host1",
                                "destination_node": "host2",
                            })

        solution.add_action(action_type="migrate",
                            resource_id=server2_uuid,
                            input_parameters={
                                "source_node": "host1",
                                "destination_node": "host3",
                            })

        with mock.patch.object(
            pbase.NodeResourceConsolidationPlanner, "create_action",
            wraps=self.planner.create_action
        ) as m_create_action:
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(2, m_create_action.call_count)
        # check order
        filters = {'action_plan_id': action_plan.id}
        actions = objects.Action.dbapi.get_action_list(self.context, filters)
        self.assertEqual(
            server1_uuid, actions[0]['input_parameters'].get('resource_id'))
        self.assertEqual(
            server2_uuid, actions[1]['input_parameters'].get('resource_id'))
        self.assertIn(actions[0]['uuid'], actions[1]['parents'])

    def test_schedule_actions_with_unknown_action(self):
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        parameters = {
            "src_uuid_node": "host1",
            "dst_uuid_node": "host2",
        }
        solution.add_action(action_type="migrate",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters=parameters)

        solution.add_action(action_type="new_action_type",
                            resource_id="",
                            input_parameters={})

        with mock.patch.object(
            pbase.NodeResourceConsolidationPlanner, "create_action",
            wraps=self.planner.create_action
        ) as m_create_action:
            self.assertRaises(
                exception.UnsupportedActionType,
                self.planner.schedule,
                self.context, self.audit.id, solution)
        self.assertEqual(2, m_create_action.call_count)

    def test_schedule_migrate_change_state_actions(self):
        solution = dsol.DefaultSolution(
            goal=mock.Mock(), strategy=self.strategy)

        solution.add_action(action_type="change_nova_service_state",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters={"state": "disabled"})

        solution.add_action(action_type="change_nova_service_state",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff37",
                            input_parameters={"state": "disabled"})

        solution.add_action(action_type="migrate",
                            resource_id="f6416850-da28-4047-a547-8c49f53e95fe",
                            input_parameters={"source_node": "host1"})

        solution.add_action(action_type="migrate",
                            resource_id="bb404e74-2caf-447b-bd1e-9234db386ca5",
                            input_parameters={"source_node": "host2"})

        solution.add_action(action_type="migrate",
                            resource_id="f6416850-da28-4047-a547-8c49f53e95ff",
                            input_parameters={"source_node": "host1"})

        solution.add_action(action_type="change_nova_service_state",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff36",
                            input_parameters={"state": "enabled"})

        solution.add_action(action_type="change_nova_service_state",
                            resource_id="b199db0c-1408-4d52-b5a5-5ca14de0ff37",
                            input_parameters={"state": "enabled"})

        with mock.patch.object(
                pbase.NodeResourceConsolidationPlanner, "create_action",
                wraps=self.planner.create_action
        ) as m_create_action:
            action_plan = self.planner.schedule(
                self.context, self.audit.id, solution)
        self.assertIsNotNone(action_plan.uuid)
        self.assertEqual(7, m_create_action.call_count)
        # check order
        filters = {'action_plan_id': action_plan.id}
        actions = objects.Action.dbapi.get_action_list(self.context, filters)
        self.assertEqual("change_nova_service_state", actions[0].action_type)
        self.assertEqual("change_nova_service_state", actions[1].action_type)
        self.assertEqual("migrate", actions[2].action_type)
        self.assertEqual("migrate", actions[3].action_type)
        self.assertEqual("migrate", actions[4].action_type)
        self.assertEqual("change_nova_service_state", actions[5].action_type)
        self.assertEqual("change_nova_service_state", actions[6].action_type)
        action0_uuid = actions[0]['uuid']
        action1_uuid = actions[1]['uuid']
        action2_uuid = actions[2]['uuid']
        action3_uuid = actions[3]['uuid']
        action4_uuid = actions[4]['uuid']
        action5_uuid = actions[5]['uuid']
        action6_uuid = actions[6]['uuid']
        # parents of action3,4,5 are action0,1
        # resource2 and 4 have the same source,
        # so action about resource4 depends on
        # action about resource2
        parents = []
        for action in actions:
            if action.parents:
                parents.extend(action.parents)
        self.assertIn(action0_uuid, parents)
        self.assertIn(action1_uuid, parents)
        self.assertIn(action2_uuid, parents)
        self.assertIn(action3_uuid, parents)
        self.assertIn(action4_uuid, parents)
        self.assertNotIn(action5_uuid, parents)
        self.assertNotIn(action6_uuid, parents)


class TestDefaultPlanner(base.DbTestCase):

    def setUp(self):
        super(TestDefaultPlanner, self).setUp()
        self.planner = pbase.NodeResourceConsolidationPlanner(mock.Mock())

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
