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
from mock import call
from mock import MagicMock


from watcher.applier.framework.messaging.events import Events
from watcher.applier.framework.messaging.launch_action_plan import \
    LaunchActionPlanCommand

from watcher.objects.action_plan import Status
from watcher.objects import ActionPlan
from watcher.tests.db.base import DbTestCase
from watcher.tests.objects import utils as obj_utils


class TestLaunchActionPlanCommand(DbTestCase):
    def setUp(self):
        super(TestLaunchActionPlanCommand, self).setUp()
        self.action_plan = obj_utils.create_test_action_plan(
            self.context)

    def test_launch_action_plan_wihout_errors(self):
        try:

            command = LaunchActionPlanCommand(self.context, MagicMock(),
                                              self.action_plan.uuid)
            command.execute()
        except Exception as e:
            self.fail(
                "The ActionPlan should be trigged wihtour error" + unicode(e))

    def test_launch_action_plan_state_failed(self):
        command = LaunchActionPlanCommand(self.context, MagicMock(),
                                          self.action_plan.uuid)
        command.execute()
        action_plan = ActionPlan.get_by_uuid(self.context,
                                             self.action_plan.uuid)
        self.assertEqual(Status.SUCCESS, action_plan.state)

    def test_trigger_audit_send_notification(self):
        messaging = MagicMock()
        command = LaunchActionPlanCommand(self.context, messaging,
                                          self.action_plan.uuid)
        command.execute()

        call_on_going = call(Events.LAUNCH_ACTION_PLAN.name, {
            'action_plan_status': Status.ONGOING,
            'action_plan__uuid': self.action_plan.uuid})
        call_success = call(Events.LAUNCH_ACTION_PLAN.name, {
            'action_plan_status': Status.SUCCESS,
            'action_plan__uuid': self.action_plan.uuid})

        calls = [call_on_going, call_success]
        messaging.topic_status.publish_event.assert_has_calls(calls)
        self.assertEqual(2, messaging.topic_status.publish_event.call_count)
