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
from watcher import objects
from watcher.tests.db import base


class ExpectedException(Exception):
    pass


@six.add_metaclass(abc.ABCMeta)
class FakeAction(abase.BaseAction):
    def schema(self):
        pass

    def postcondition(self):
        pass

    def precondition(self):
        pass

    def revert(self):
        pass

    def execute(self):
        raise ExpectedException()


class TestDefaultWorkFlowEngine(base.DbTestCase):
    def setUp(self):
        super(TestDefaultWorkFlowEngine, self).setUp()
        self.engine = tflow.DefaultWorkFlowEngine(
            config=mock.Mock(),
            context=self.context,
            applier_manager=mock.MagicMock())

    @mock.patch('taskflow.engines.load')
    @mock.patch('taskflow.patterns.graph_flow.Flow.link')
    def test_execute(self, graph_flow, engines):
        actions = mock.MagicMock()
        try:
            self.engine.execute(actions)
            self.assertTrue(engines.called)
        except Exception as exc:
            self.fail(exc)

    def create_action(self, action_type, parameters, next):
        action = {
            'uuid': utils.generate_uuid(),
            'action_plan_id': 0,
            'action_type': action_type,
            'input_parameters': parameters,
            'state': objects.action.State.PENDING,
            'next': next,
        }
        new_action = objects.Action(self.context, **action)
        new_action.create(self.context)
        new_action.save()

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

    def test_execute_with_one_action(self):
        actions = [self.create_action("nop", {'message': 'test'}, None)]
        try:
            self.engine.execute(actions)
            self.check_actions_state(actions, objects.action.State.SUCCEEDED)

        except Exception as exc:
            self.fail(exc)

    def test_execute_with_two_actions(self):
        actions = []
        second = self.create_action("sleep", {'duration': 0.0}, None)
        first = self.create_action("nop", {'message': 'test'}, second.id)

        actions.append(first)
        actions.append(second)

        try:
            self.engine.execute(actions)
            self.check_actions_state(actions, objects.action.State.SUCCEEDED)

        except Exception as exc:
            self.fail(exc)

    def test_execute_with_three_actions(self):
        actions = []

        third = self.create_action("nop", {'message': 'next'}, None)
        second = self.create_action("sleep", {'duration': 0.0}, third.id)
        first = self.create_action("nop", {'message': 'hello'}, second.id)

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

    def test_execute_with_exception(self):
        actions = []

        third = self.create_action("no_exist", {'message': 'next'}, None)
        second = self.create_action("sleep", {'duration': 0.0}, third.id)
        first = self.create_action("nop", {'message': 'hello'}, second.id)

        self.check_action_state(first, objects.action.State.PENDING)
        self.check_action_state(second, objects.action.State.PENDING)
        self.check_action_state(third, objects.action.State.PENDING)

        actions.append(first)
        actions.append(second)
        actions.append(third)

        self.assertRaises(exception.WorkflowExecutionException,
                          self.engine.execute, actions)

        self.check_action_state(first, objects.action.State.SUCCEEDED)
        self.check_action_state(second, objects.action.State.SUCCEEDED)
        self.check_action_state(third, objects.action.State.FAILED)

    @mock.patch.object(factory.ActionFactory, "make_action")
    def test_execute_with_action_exception(self, m_make_action):
        actions = [self.create_action("fake_action", {}, None)]
        m_make_action.return_value = FakeAction(mock.Mock())

        exc = self.assertRaises(exception.WorkflowExecutionException,
                                self.engine.execute, actions)

        self.assertIsInstance(exc.kwargs['error'], ExpectedException)
        self.check_action_state(actions[0], objects.action.State.FAILED)
