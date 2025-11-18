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


from oslo_config import cfg
from unittest import mock

from watcher.applier.messaging import trigger
from watcher.common import utils
from watcher import objects
from watcher.tests.unit import base

CONF = cfg.CONF


class TestTriggerActionPlan(base.TestCase):
    def __init__(self, *args, **kwds):
        super().__init__(*args, **kwds)
        self.applier = mock.MagicMock()
        self.endpoint = trigger.TriggerActionPlan(self.applier)

    @mock.patch.object(objects.ActionPlan, 'get_by_uuid', autospec=True)
    @mock.patch.object(objects.ActionPlan, 'save', autospec=True)
    def test_launch_action_plan(self, mock_save, mock_get_by_uuid):
        action_plan_uuid = utils.generate_uuid()
        action_plan = objects.ActionPlan(
            context=self.context,
            uuid=action_plan_uuid,
            hostname=None,
            state=objects.action_plan.State.PENDING)
        mock_get_by_uuid.return_value = action_plan
        CONF.set_default('host', 'applier1.example.com')

        expected_uuid = self.endpoint.launch_action_plan(self.context,
                                                         action_plan_uuid)
        self.assertEqual(expected_uuid, action_plan_uuid)
        self.assertEqual(action_plan.hostname, "applier1.example.com")
        mock_save.assert_called_once_with(action_plan)
