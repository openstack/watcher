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
import eventlet
import mock

from watcher.applier.workflow_engine import default as tflow
from watcher import objects
from watcher.tests.db import base
from watcher.tests.objects import utils as obj_utils


class TestTaskFlowActionContainer(base.DbTestCase):
    def setUp(self):
        super(TestTaskFlowActionContainer, self).setUp()
        self.engine = tflow.DefaultWorkFlowEngine(
            config=mock.Mock(),
            context=self.context,
            applier_manager=mock.MagicMock())
        obj_utils.create_test_goal(self.context)
        self.strategy = obj_utils.create_test_strategy(self.context)
        self.audit = obj_utils.create_test_audit(
            self.context, strategy_id=self.strategy.id)

    def test_execute(self):
        action_plan = obj_utils.create_test_action_plan(
            self.context, audit_id=self.audit.id,
            strategy_id=self.strategy.id,
            state=objects.action.State.ONGOING)

        action = obj_utils.create_test_action(
            self.context, action_plan_id=action_plan.id,
            state=objects.action.State.ONGOING,
            action_type='nop',
            input_parameters={'message': 'hello World'})
        action_container = tflow.TaskFlowActionContainer(
            db_action=action,
            engine=self.engine)
        action_container.execute()

        self.assertTrue(action.state, objects.action.State.SUCCEEDED)

    @mock.patch('eventlet.spawn')
    def test_execute_with_cancel_action_plan(self, mock_eventlet_spawn):
        action_plan = obj_utils.create_test_action_plan(
            self.context, audit_id=self.audit.id,
            strategy_id=self.strategy.id,
            state=objects.action_plan.State.CANCELLING)

        action = obj_utils.create_test_action(
            self.context, action_plan_id=action_plan.id,
            state=objects.action.State.ONGOING,
            action_type='nop',
            input_parameters={'message': 'hello World'})
        action_container = tflow.TaskFlowActionContainer(
            db_action=action,
            engine=self.engine)

        def empty_test():
            pass
        et = eventlet.spawn(empty_test)
        mock_eventlet_spawn.return_value = et
        action_container.execute()
        et.kill.assert_called_with()
