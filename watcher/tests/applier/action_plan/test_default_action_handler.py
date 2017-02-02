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

import mock

from watcher.applier.action_plan import default
from watcher.applier import default as ap_applier
from watcher import notifications
from watcher import objects
from watcher.objects import action_plan as ap_objects
from watcher.tests.db import base
from watcher.tests.objects import utils as obj_utils


class TestDefaultActionPlanHandler(base.DbTestCase):

    class FakeApplierException(Exception):
        pass

    def setUp(self):
        super(TestDefaultActionPlanHandler, self).setUp()

        p_action_plan_notifications = mock.patch.object(
            notifications, 'action_plan', autospec=True)
        self.m_action_plan_notifications = p_action_plan_notifications.start()
        self.addCleanup(p_action_plan_notifications.stop)

        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit(self.context)
        self.action_plan = obj_utils.create_test_action_plan(self.context)

    @mock.patch.object(objects.ActionPlan, "get_by_uuid")
    def test_launch_action_plan(self, m_get_action_plan):
        m_get_action_plan.return_value = self.action_plan
        command = default.DefaultActionPlanHandler(
            self.context, mock.MagicMock(), self.action_plan.uuid)
        command.execute()

        expected_calls = [
            mock.call(self.context, self.action_plan,
                      action=objects.fields.NotificationAction.EXECUTION,
                      phase=objects.fields.NotificationPhase.START),
            mock.call(self.context, self.action_plan,
                      action=objects.fields.NotificationAction.EXECUTION,
                      phase=objects.fields.NotificationPhase.END)]

        self.assertEqual(ap_objects.State.SUCCEEDED, self.action_plan.state)

        self.assertEqual(
            expected_calls,
            self.m_action_plan_notifications
                .send_action_notification
                .call_args_list)

    @mock.patch.object(ap_applier.DefaultApplier, "execute")
    @mock.patch.object(objects.ActionPlan, "get_by_uuid")
    def test_launch_action_plan_with_error(self, m_get_action_plan, m_execute):
        m_get_action_plan.return_value = self.action_plan
        m_execute.side_effect = self.FakeApplierException
        command = default.DefaultActionPlanHandler(
            self.context, mock.MagicMock(), self.action_plan.uuid)
        command.execute()

        expected_calls = [
            mock.call(self.context, self.action_plan,
                      action=objects.fields.NotificationAction.EXECUTION,
                      phase=objects.fields.NotificationPhase.START),
            mock.call(self.context, self.action_plan,
                      action=objects.fields.NotificationAction.EXECUTION,
                      priority=objects.fields.NotificationPriority.ERROR,
                      phase=objects.fields.NotificationPhase.ERROR)]

        self.assertEqual(ap_objects.State.FAILED, self.action_plan.state)

        self.assertEqual(
            expected_calls,
            self.m_action_plan_notifications
                .send_action_notification
                .call_args_list)
