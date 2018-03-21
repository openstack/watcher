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
#
import abc
import mock

import six

from watcher.applier.actions import base as abase
from watcher.applier.actions import factory
from watcher.applier.workflow_engine import default as tflow
from watcher.common import exception
from watcher.common import utils
from watcher import notifications
from watcher import objects
from watcher.tests.db import base
from watcher.tests.objects import utils as obj_utils


class ExpectedException(Exception):
    pass


@six.add_metaclass(abc.ABCMeta)
class FakeAction(abase.BaseAction):
    def schema(self):
        pass

    def post_condition(self):
        pass

    def pre_condition(self):
        pass

    def revert(self):
        pass

    def execute(self):
        return False

    def get_description(self):
        return "fake action, just for test"


class TestDefaultWorkFlowEngine(base.DbTestCase):
    def setUp(self):
        super(TestDefaultWorkFlowEngine, self).setUp()
        self.engine = tflow.DefaultWorkFlowEngine(
            config=mock.Mock(),
            context=self.context,
            applier_manager=mock.MagicMock())
        self.engine.config.max_workers = 2

    @mock.patch.object(objects.Strategy, "get_by_id")
    @mock.patch.object(objects.ActionPlan, "get_by_id")
    @mock.patch('taskflow.engines.load')
    @mock.patch('taskflow.patterns.graph_flow.Flow.link')
    def test_execute(self, graph_flow, engines, m_actionplan, m_strategy):
        actions = mock.MagicMock()
        try:
            self.engine.execute(actions)
            self.assertTrue(engines.called)
        except Exception as exc:
            self.fail(exc)

    def create_action(self, action_type, parameters, parents=None, uuid=None,
                      state=None):
        action = {
            'uuid': uuid or utils.generate_uuid(),
            'action_plan_id': 0,
            'action_type': action_type,
            'input_parameters': parameters,
            'state': objects.action.State.PENDING,
            'parents': parents or [],

        }
        new_action = objects.Action(self.context, **action)
        with mock.patch.object(notifications.action, 'send_create'):
            new_action.create()
        return new_action

    def check_action_state(self, action, expected_state):
        to_check = objects.Action.get_by_uuid(self.context, action.uuid)
        self.assertEqual(expected_state, to_check.state)

    def check_actions_state(self, actions, expected_state):
        for a in actions:
            self.check_action_state(a, expected_state)

    @mock.patch('taskflow.engines.load')
    @mock.patch('taskflow.patterns.graph_flow.Flow.link')
    def test_execute_with_no_actions(self, graph_flow, engines):
        actions = []
        try:
            self.engine.execute(actions)
            self.assertFalse(graph_flow.called)
            self.assertTrue(engines.called)
        except Exception as exc:
            self.fail(exc)

    @mock.patch.object(objects.Strategy, "get_by_id")
    @mock.patch.object(objects.ActionPlan, "get_by_id")
    @mock.patch.object(notifications.action, 'send_execution_notification')
    @mock.patch.object(notifications.action, 'send_update')
    def test_execute_with_one_action(self, mock_send_update,
                                     mock_execution_notification,
                                     m_get_actionplan, m_get_strategy):
        m_get_actionplan.return_value = obj_utils.get_test_action_plan(
            self.context, id=0)
        m_get_strategy.return_value = obj_utils.get_test_strategy(
            self.context, id=1)
        actions = [self.create_action("nop", {'message': 'test'})]
        try:
            self.engine.execute(actions)
            self.check_actions_state(actions, objects.action.State.SUCCEEDED)

        except Exception as exc:
            self.fail(exc)

    @mock.patch.object(objects.Strategy, "get_by_id")
    @mock.patch.object(objects.ActionPlan, "get_by_id")
    @mock.patch.object(notifications.action, 'send_execution_notification')
    @mock.patch.object(notifications.action, 'send_update')
    def test_execute_nop_sleep(self, mock_send_update,
                               mock_execution_notification,
                               m_get_actionplan, m_get_strategy):
        m_get_actionplan.return_value = obj_utils.get_test_action_plan(
            self.context, id=0)
        m_get_strategy.return_value = obj_utils.get_test_strategy(
            self.context, id=1)
        actions = []
        first_nop = self.create_action("nop", {'message': 'test'})
        second_nop = self.create_action("nop", {'message': 'second test'})
        sleep = self.create_action("sleep", {'duration': 0.0},
                                   parents=[first_nop.uuid, second_nop.uuid])
        actions.extend([first_nop, second_nop, sleep])

        try:
            self.engine.execute(actions)
            self.check_actions_state(actions, objects.action.State.SUCCEEDED)

        except Exception as exc:
            self.fail(exc)

    @mock.patch.object(objects.Strategy, "get_by_id")
    @mock.patch.object(objects.ActionPlan, "get_by_id")
    @mock.patch.object(notifications.action, 'send_execution_notification')
    @mock.patch.object(notifications.action, 'send_update')
    def test_execute_with_parents(self, mock_send_update,
                                  mock_execution_notification,
                                  m_get_actionplan, m_get_strategy):
        m_get_actionplan.return_value = obj_utils.get_test_action_plan(
            self.context, id=0)
        m_get_strategy.return_value = obj_utils.get_test_strategy(
            self.context, id=1)
        actions = []
        first_nop = self.create_action(
            "nop", {'message': 'test'},
            uuid='bc7eee5c-4fbe-4def-9744-b539be55aa19')
        second_nop = self.create_action(
            "nop", {'message': 'second test'},
            uuid='0565bd5c-aa00-46e5-8d81-2cb5cc1ffa23')
        first_sleep = self.create_action(
            "sleep", {'duration': 0.0}, parents=[first_nop.uuid,
                                                 second_nop.uuid],
            uuid='be436531-0da3-4dad-a9c0-ea1d2aff6496')
        second_sleep = self.create_action(
            "sleep", {'duration': 0.0}, parents=[first_sleep.uuid],
            uuid='9eb51e14-936d-4d12-a500-6ba0f5e0bb1c')
        actions.extend([first_nop, second_nop, first_sleep, second_sleep])

        expected_nodes = [
            {'uuid': 'bc7eee5c-4fbe-4def-9744-b539be55aa19',
             'input_parameters': {u'message': u'test'},
             'action_plan_id': 0, 'state': u'PENDING', 'parents': [],
             'action_type': u'nop', 'id': 1},
            {'uuid': '0565bd5c-aa00-46e5-8d81-2cb5cc1ffa23',
             'input_parameters': {u'message': u'second test'},
             'action_plan_id': 0, 'state': u'PENDING', 'parents': [],
             'action_type': u'nop', 'id': 2},
            {'uuid': 'be436531-0da3-4dad-a9c0-ea1d2aff6496',
             'input_parameters': {u'duration': 0.0},
             'action_plan_id': 0, 'state': u'PENDING',
             'parents': [u'bc7eee5c-4fbe-4def-9744-b539be55aa19',
                         u'0565bd5c-aa00-46e5-8d81-2cb5cc1ffa23'],
             'action_type': u'sleep', 'id': 3},
            {'uuid': '9eb51e14-936d-4d12-a500-6ba0f5e0bb1c',
             'input_parameters': {u'duration': 0.0},
             'action_plan_id': 0, 'state': u'PENDING',
             'parents': [u'be436531-0da3-4dad-a9c0-ea1d2aff6496'],
             'action_type': u'sleep', 'id': 4}]

        expected_edges = [
            ('action_type:nop uuid:0565bd5c-aa00-46e5-8d81-2cb5cc1ffa23',
             'action_type:sleep uuid:be436531-0da3-4dad-a9c0-ea1d2aff6496'),
            ('action_type:nop uuid:bc7eee5c-4fbe-4def-9744-b539be55aa19',
             'action_type:sleep uuid:be436531-0da3-4dad-a9c0-ea1d2aff6496'),
            ('action_type:sleep uuid:be436531-0da3-4dad-a9c0-ea1d2aff6496',
             'action_type:sleep uuid:9eb51e14-936d-4d12-a500-6ba0f5e0bb1c')]

        try:
            flow = self.engine.execute(actions)
            actual_nodes = sorted([x[0]._db_action.as_dict()
                                   for x in flow.iter_nodes()],
                                  key=lambda x: x['id'])
            for expected, actual in zip(expected_nodes, actual_nodes):
                for key in expected.keys():
                    self.assertIn(expected[key], actual.values())
            actual_edges = [(u.name, v.name)
                            for (u, v, _) in flow.iter_links()]

            for edge in expected_edges:
                self.assertIn(edge, actual_edges)

            self.check_actions_state(actions, objects.action.State.SUCCEEDED)

        except Exception as exc:
            self.fail(exc)

    @mock.patch.object(objects.Strategy, "get_by_id")
    @mock.patch.object(objects.ActionPlan, "get_by_id")
    @mock.patch.object(notifications.action, 'send_execution_notification')
    @mock.patch.object(notifications.action, 'send_update')
    def test_execute_with_two_actions(self, m_send_update, m_execution,
                                      m_get_actionplan, m_get_strategy):
        m_get_actionplan.return_value = obj_utils.get_test_action_plan(
            self.context, id=0)
        m_get_strategy.return_value = obj_utils.get_test_strategy(
            self.context, id=1)
        actions = []
        second = self.create_action("sleep", {'duration': 0.0})
        first = self.create_action("nop", {'message': 'test'})

        actions.append(first)
        actions.append(second)

        try:
            self.engine.execute(actions)
            self.check_actions_state(actions, objects.action.State.SUCCEEDED)

        except Exception as exc:
            self.fail(exc)

    @mock.patch.object(objects.Strategy, "get_by_id")
    @mock.patch.object(objects.ActionPlan, "get_by_id")
    @mock.patch.object(notifications.action, 'send_execution_notification')
    @mock.patch.object(notifications.action, 'send_update')
    def test_execute_with_three_actions(self, m_send_update, m_execution,
                                        m_get_actionplan, m_get_strategy):
        m_get_actionplan.return_value = obj_utils.get_test_action_plan(
            self.context, id=0)
        m_get_strategy.return_value = obj_utils.get_test_strategy(
            self.context, id=1)
        actions = []
        third = self.create_action("nop", {'message': 'next'})
        second = self.create_action("sleep", {'duration': 0.0})
        first = self.create_action("nop", {'message': 'hello'})

        self.check_action_state(first, objects.action.State.PENDING)
        self.check_action_state(second, objects.action.State.PENDING)
        self.check_action_state(third, objects.action.State.PENDING)

        actions.append(first)
        actions.append(second)
        actions.append(third)

        try:
            self.engine.execute(actions)
            self.check_actions_state(actions, objects.action.State.SUCCEEDED)

        except Exception as exc:
            self.fail(exc)

    @mock.patch.object(objects.Strategy, "get_by_id")
    @mock.patch.object(objects.ActionPlan, "get_by_id")
    @mock.patch.object(notifications.action, 'send_execution_notification')
    @mock.patch.object(notifications.action, 'send_update')
    def test_execute_with_exception(self, m_send_update, m_execution,
                                    m_get_actionplan, m_get_strategy):
        m_get_actionplan.return_value = obj_utils.get_test_action_plan(
            self.context, id=0)
        m_get_strategy.return_value = obj_utils.get_test_strategy(
            self.context, id=1)
        actions = []

        third = self.create_action("no_exist", {'message': 'next'})
        second = self.create_action("sleep", {'duration': 0.0})
        first = self.create_action("nop", {'message': 'hello'})

        self.check_action_state(first, objects.action.State.PENDING)
        self.check_action_state(second, objects.action.State.PENDING)
        self.check_action_state(third, objects.action.State.PENDING)

        actions.append(first)
        actions.append(second)
        actions.append(third)

        self.engine.execute(actions)

        self.check_action_state(first, objects.action.State.SUCCEEDED)
        self.check_action_state(second, objects.action.State.SUCCEEDED)
        self.check_action_state(third, objects.action.State.FAILED)

    @mock.patch.object(objects.Strategy, "get_by_id")
    @mock.patch.object(objects.ActionPlan, "get_by_id")
    @mock.patch.object(notifications.action, 'send_execution_notification')
    @mock.patch.object(notifications.action, 'send_update')
    @mock.patch.object(factory.ActionFactory, "make_action")
    def test_execute_with_action_failed(self, m_make_action, m_send_update,
                                        m_send_execution, m_get_actionplan,
                                        m_get_strategy):
        m_get_actionplan.return_value = obj_utils.get_test_action_plan(
            self.context, id=0)
        m_get_strategy.return_value = obj_utils.get_test_strategy(
            self.context, id=1)
        actions = [self.create_action("fake_action", {})]
        m_make_action.return_value = FakeAction(mock.Mock())

        self.engine.execute(actions)
        self.check_action_state(actions[0], objects.action.State.FAILED)

    @mock.patch.object(objects.ActionPlan, "get_by_uuid")
    def test_execute_with_action_plan_cancel(self, m_get_actionplan):
        obj_utils.create_test_goal(self.context)
        strategy = obj_utils.create_test_strategy(self.context)
        audit = obj_utils.create_test_audit(
            self.context, strategy_id=strategy.id)
        action_plan = obj_utils.create_test_action_plan(
            self.context, audit_id=audit.id,
            strategy_id=strategy.id,
            state=objects.action_plan.State.CANCELLING)
        action1 = obj_utils.create_test_action(
            self.context, action_plan_id=action_plan.id,
            action_type='nop', state=objects.action.State.SUCCEEDED,
            input_parameters={'message': 'hello World'})
        action2 = obj_utils.create_test_action(
            self.context, action_plan_id=action_plan.id,
            action_type='nop', state=objects.action.State.ONGOING,
            uuid='9eb51e14-936d-4d12-a500-6ba0f5e0bb1c',
            input_parameters={'message': 'hello World'})
        action3 = obj_utils.create_test_action(
            self.context, action_plan_id=action_plan.id,
            action_type='nop', state=objects.action.State.PENDING,
            uuid='bc7eee5c-4fbe-4def-9744-b539be55aa19',
            input_parameters={'message': 'hello World'})
        m_get_actionplan.return_value = action_plan
        actions = []
        actions.append(action1)
        actions.append(action2)
        actions.append(action3)
        self.assertRaises(exception.ActionPlanCancelled,
                          self.engine.execute, actions)
        try:
            self.check_action_state(action1, objects.action.State.SUCCEEDED)
            self.check_action_state(action2, objects.action.State.CANCELLED)
            self.check_action_state(action3, objects.action.State.CANCELLED)

        except Exception as exc:
            self.fail(exc)

    def test_decider(self):
        # execution_rule is ALWAYS
        self.engine.execution_rule = 'ALWAYS'
        history = {'action1': True}
        self.assertTrue(self.engine.decider(history))

        history = {'action1': False}
        self.assertTrue(self.engine.decider(history))

        # execution_rule is ANY
        self.engine.execution_rule = 'ANY'
        history = {'action1': True}
        self.assertFalse(self.engine.decider(history))

        history = {'action1': False}
        self.assertTrue(self.engine.decider(history))
