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

import mock

from watcher.applier.action_plan import default
from watcher.objects import action_plan as ap_objects
from watcher.tests.db import base
from watcher.tests.objects import utils as obj_utils


class TestDefaultActionPlanHandler(base.DbTestCase):

    def setUp(self):
        super(TestDefaultActionPlanHandler, self).setUp()
        obj_utils.create_test_goal(self.context)
        obj_utils.create_test_strategy(self.context)
        obj_utils.create_test_audit(self.context)
        self.action_plan = obj_utils.create_test_action_plan(self.context)

    def test_launch_action_plan(self):
        command = default.DefaultActionPlanHandler(
            self.context, mock.MagicMock(), self.action_plan.uuid)
        command.execute()
        action_plan = ap_objects.ActionPlan.get_by_uuid(
            self.context, self.action_plan.uuid)
        self.assertEqual(ap_objects.State.SUCCEEDED, action_plan.state)
