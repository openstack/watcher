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
from unittest import mock

from watcher.applier.actions import base as abase
from watcher.applier.actions import factory
from watcher.applier.actions import nop
from watcher.applier.workflow_engine import default as tflow
from watcher.common import exception
from watcher.common import utils
from watcher import notifications
from watcher import objects
from watcher.tests.db import base
from watcher.tests.objects import utils as obj_utils


class ExpectedException(Exception):
    pass


class FakeAction(abase.BaseAction, metaclass=abc.ABCMeta):
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
        super().setUp()
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

    def check_notifications_contains(self, notification_calls, action_state,
                                     old_state=None):
        """Check that an action notification contains the expected info.

        notification_calls: list of notification calls arguments
        action_state: expected action state (dict)
        old_state: expected old action state (optional)
        """
        if old_state:
            action_state['old_state'] = old_state
        for call in notification_calls:
            data_dict = call.args[1].as_dict()
            if call.kwargs and 'old_state' in call.kwargs:
                data_dict['old_state'] = call.kwargs['old_state']
            try:
                self.assertLessEqual(action_state.items(), data_dict.items())
                return True
            except AssertionError:
                continue
        return False

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
             'input_parameters': {'message': 'test'},
             'action_plan_id': 0, 'state': 'PENDING', 'parents': [],
             'action_type': 'nop', 'id': 1},
            {'uuid': '0565bd5c-aa00-46e5-8d81-2cb5cc1ffa23',
             'input_parameters': {'message': 'second test'},
             'action_plan_id': 0, 'state': 'PENDING', 'parents': [],
             'action_type': 'nop', 'id': 2},
            {'uuid': 'be436531-0da3-4dad-a9c0-ea1d2aff6496',
             'input_parameters': {'duration': 0.0},
             'action_plan_id': 0, 'state': 'PENDING',
             'parents': ['bc7eee5c-4fbe-4def-9744-b539be55aa19',
                         '0565bd5c-aa00-46e5-8d81-2cb5cc1ffa23'],
             'action_type': 'sleep', 'id': 3},
            {'uuid': '9eb51e14-936d-4d12-a500-6ba0f5e0bb1c',
             'input_parameters': {'duration': 0.0},
             'action_plan_id': 0, 'state': 'PENDING',
             'parents': ['be436531-0da3-4dad-a9c0-ea1d2aff6496'],
             'action_type': 'sleep', 'id': 4}]

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
        self.assertTrue(self.check_notifications_contains(
            m_send_update.call_args_list,
            {
                'state': objects.action.State.FAILED,
                'uuid': actions[0].uuid,
                'action_type': 'fake_action',
                'status_message': "Action failed in execute: The action %s "
                "execution failed." % actions[0].uuid,
            },
        ))

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

    @mock.patch.object(objects.ActionPlan, "get_by_id")
    @mock.patch.object(notifications.action, 'send_execution_notification')
    @mock.patch.object(notifications.action, 'send_update')
    @mock.patch.object(nop.Nop, 'debug_message')
    def test_execute_with_automatic_skipped(self, m_nop_message,
                                            m_send_update, m_execution,
                                            m_get_actionplan):

        obj_utils.create_test_goal(self.context)
        strategy = obj_utils.create_test_strategy(self.context)
        audit = obj_utils.create_test_audit(
            self.context, strategy_id=strategy.id)
        action_plan = obj_utils.create_test_action_plan(
            self.context, audit_id=audit.id,
            strategy_id=strategy.id,
            state=objects.action_plan.State.ONGOING,
            id=0)
        m_get_actionplan.return_value = action_plan
        actions = []

        action = self.create_action("nop", {'message': 'action2',
                                            'skip_pre_condition': True})

        self.check_action_state(action, objects.action.State.PENDING)

        actions.append(action)

        self.engine.execute(actions)

        # action skipped automatically in the pre_condition phase
        self.check_action_state(action, objects.action.State.SKIPPED)
        self.assertEqual(
            objects.Action.get_by_uuid(
                self.context, action.uuid).status_message,
            "Action was skipped automatically: Skipped in pre_condition")
        action_state_dict = {
            'state': objects.action.State.SKIPPED,
            'status_message': "Action was skipped automatically: "
            "Skipped in pre_condition",
            'uuid': action.uuid,
            'action_type': 'nop',
        }
        self.assertTrue(self.check_notifications_contains(
            m_send_update.call_args_list, action_state_dict))
        self.assertTrue(self.check_notifications_contains(
            m_send_update.call_args_list, action_state_dict,
            old_state=objects.action.State.PENDING))

        m_nop_message.assert_not_called()

    @mock.patch.object(objects.ActionPlan, "get_by_id")
    @mock.patch.object(notifications.action, 'send_execution_notification')
    @mock.patch.object(notifications.action, 'send_update')
    @mock.patch.object(nop.Nop, 'debug_message')
    @mock.patch.object(nop.Nop, 'pre_condition')
    def test_execute_with_manually_skipped(self, m_nop_pre_condition,
                                           m_nop_message,
                                           m_send_update, m_execution,
                                           m_get_actionplan):
        obj_utils.create_test_goal(self.context)
        strategy = obj_utils.create_test_strategy(self.context)
        audit = obj_utils.create_test_audit(
            self.context, strategy_id=strategy.id)
        action_plan = obj_utils.create_test_action_plan(
            self.context, audit_id=audit.id,
            strategy_id=strategy.id,
            state=objects.action_plan.State.ONGOING,
            id=0)
        m_get_actionplan.return_value = action_plan
        actions = []
        action1 = obj_utils.create_test_action(
            self.context,
            action_type='nop',
            state=objects.action.State.PENDING,
            input_parameters={'message': 'action1'})
        action2 = obj_utils.create_test_action(
            self.context,
            action_type='nop',
            state=objects.action.State.SKIPPED,
            uuid='bc7eee5c-4fbe-4def-9744-b539be55aa19',
            input_parameters={'message': 'action2'})
        self.check_action_state(action1, objects.action.State.PENDING)
        self.check_action_state(action2, objects.action.State.SKIPPED)
        actions.append(action1)
        actions.append(action2)
        self.engine.execute(actions)
        # action skipped automatically in the pre_condition phase
        self.check_action_state(action1, objects.action.State.SUCCEEDED)
        self.check_action_state(action2, objects.action.State.SKIPPED)
        # pre_condition and execute are only called for action1
        m_nop_pre_condition.assert_called_once_with()
        m_nop_message.assert_called_once_with('action1')

    @mock.patch.object(objects.ActionPlan, "get_by_id")
    @mock.patch.object(notifications.action, 'send_execution_notification')
    @mock.patch.object(notifications.action, 'send_update')
    @mock.patch.object(nop.Nop, 'debug_message')
    def test_execute_different_action_results(self, m_nop_message,
                                              m_send_update, m_execution,
                                              m_get_actionplan):

        obj_utils.create_test_goal(self.context)
        strategy = obj_utils.create_test_strategy(self.context)
        audit = obj_utils.create_test_audit(
            self.context, strategy_id=strategy.id)
        action_plan = obj_utils.create_test_action_plan(
            self.context, audit_id=audit.id,
            strategy_id=strategy.id,
            state=objects.action_plan.State.ONGOING,
            id=0)
        m_get_actionplan.return_value = action_plan
        actions = []

        action1 = self.create_action("nop", {'message': 'action1'})
        action2 = self.create_action("nop", {'message': 'action2',
                                             'skip_pre_condition': True})
        action3 = self.create_action("nop", {'message': 'action3',
                                             'fail_pre_condition': True})
        action4 = self.create_action("nop", {'message': 'action4',
                                             'fail_execute': True})
        action5 = self.create_action("nop", {'message': 'action5',
                                             'fail_post_condition': True})
        action6 = self.create_action("sleep", {'duration': 1.0})

        self.check_action_state(action1, objects.action.State.PENDING)
        self.check_action_state(action2, objects.action.State.PENDING)
        self.check_action_state(action3, objects.action.State.PENDING)
        self.check_action_state(action4, objects.action.State.PENDING)
        self.check_action_state(action5, objects.action.State.PENDING)
        self.check_action_state(action6, objects.action.State.PENDING)

        actions.append(action1)
        actions.append(action2)
        actions.append(action3)
        actions.append(action4)
        actions.append(action5)
        actions.append(action6)

        self.engine.execute(actions)

        # successful nop action
        self.check_action_state(action1, objects.action.State.SUCCEEDED)
        self.assertIsNone(
            objects.Action.get_by_uuid(self.context, action1.uuid)
            .status_message)
        # action skipped automatically in the pre_condition phase
        self.check_action_state(action2, objects.action.State.SKIPPED)
        self.assertEqual(
            objects.Action.get_by_uuid(
                self.context, action2.uuid).status_message,
            "Action was skipped automatically: Skipped in pre_condition")
        # action failed in the pre_condition phase
        self.check_action_state(action3, objects.action.State.FAILED)
        self.assertEqual(
            objects.Action.get_by_uuid(
                self.context, action3.uuid).status_message,
            "Action failed in pre_condition: Failed in pre_condition")
        # action failed in the execute phase
        self.check_action_state(action4, objects.action.State.FAILED)
        self.assertEqual(
            objects.Action.get_by_uuid(
                self.context, action4.uuid).status_message,
            "Action failed in execute: The action %s execution failed."
            % action4.uuid)
        # action failed in the post_condition phase
        self.check_action_state(action5, objects.action.State.FAILED)
        self.assertEqual(
            objects.Action.get_by_uuid(
                self.context, action5.uuid).status_message,
            "Action failed in post_condition: Failed in post_condition")
        # successful sleep action
        self.check_action_state(action6, objects.action.State.SUCCEEDED)

        # execute method should not be called for actions that are skipped of
        # failed in the pre_condition phase
        expected_execute_calls = [mock.call('action1'),
                                  mock.call('action4'),
                                  mock.call('action5')]
        m_nop_message.assert_has_calls(expected_execute_calls, any_order=True)
        self.assertEqual(m_nop_message.call_count, 3)

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

    @mock.patch.object(objects.ActionPlan, "get_by_uuid")
    def test_notify_with_status_message(self, m_get_actionplan):
        """Test that notify method properly handles status_message."""
        obj_utils.create_test_goal(self.context)
        strategy = obj_utils.create_test_strategy(self.context)
        audit = obj_utils.create_test_audit(
            self.context, strategy_id=strategy.id)
        action_plan = obj_utils.create_test_action_plan(
            self.context, audit_id=audit.id,
            strategy_id=strategy.id,
            state=objects.action_plan.State.ONGOING)
        action1 = obj_utils.create_test_action(
            self.context, action_plan_id=action_plan.id,
            action_type='nop', state=objects.action.State.ONGOING,
            input_parameters={'message': 'hello World'})
        m_get_actionplan.return_value = action_plan
        actions = []
        actions.append(action1)

        # Test notify with status_message provided
        test_status_message = "Action completed successfully"
        result = self.engine.notify(action1, objects.action.State.FAILED,
                                    status_message=test_status_message)

        # Verify the action state was updated
        self.assertEqual(result.state, objects.action.State.FAILED)

        # Verify the status_message was set
        self.assertEqual(result.status_message, test_status_message)

        # Verify the changes were persisted to the database
        persisted_action = objects.Action.get_by_uuid(
            self.context, action1.uuid)
        self.assertEqual(persisted_action.state, objects.action.State.FAILED)
        self.assertEqual(persisted_action.status_message, test_status_message)

    @mock.patch.object(objects.ActionPlan, "get_by_uuid")
    def test_notify_without_status_message(self, m_get_actionplan):
        """Test that notify method works without status_message parameter."""
        obj_utils.create_test_goal(self.context)
        strategy = obj_utils.create_test_strategy(self.context)
        audit = obj_utils.create_test_audit(
            self.context, strategy_id=strategy.id)
        action_plan = obj_utils.create_test_action_plan(
            self.context, audit_id=audit.id,
            strategy_id=strategy.id,
            state=objects.action_plan.State.ONGOING)
        action1 = obj_utils.create_test_action(
            self.context, action_plan_id=action_plan.id,
            action_type='nop', state=objects.action.State.ONGOING,
            input_parameters={'message': 'hello World'})
        m_get_actionplan.return_value = action_plan
        actions = []
        actions.append(action1)

        # Test notify without status_message
        result = self.engine.notify(action1, objects.action.State.SUCCEEDED)
        # Verify the action state was updated
        self.assertEqual(result.state, objects.action.State.SUCCEEDED)

        # Verify the status_message
        self.assertIsNone(result.status_message)
        # Verify the changes were persisted to the database
        persisted_action = objects.Action.get_by_uuid(
            self.context, action1.uuid)
        self.assertEqual(persisted_action.state,
                         objects.action.State.SUCCEEDED)
        self.assertIsNone(persisted_action.status_message)
