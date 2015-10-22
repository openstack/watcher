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
import mock

from watcher.applier.framework.command_executor import CommandExecutor
from watcher import objects

from watcher.common import utils
from watcher.decision_engine.framework.default_planner import Primitives
from watcher.objects.action import Action
from watcher.objects.action import Status
from watcher.tests.db.base import DbTestCase


class TestCommandExecutor(DbTestCase):
    def setUp(self):
        super(TestCommandExecutor, self).setUp()
        self.applier = mock.MagicMock()
        self.executor = CommandExecutor(self.applier, self.context)

    def test_execute(self):
        actions = mock.MagicMock()
        result = self.executor.execute(actions)
        self.assertEqual(result, True)

    def test_execute_with_actions(self):
        actions = []
        action = {
            'uuid': utils.generate_uuid(),
            'action_plan_id': 0,
            'action_type': Primitives.NOP.value,
            'applies_to': '',
            'src': '',
            'dst': '',
            'parameter': '',
            'description': '',
            'state': Status.PENDING,
            'alarm': None,
            'next': None,
        }
        new_action = objects.Action(self.context, **action)
        new_action.create(self.context)
        new_action.save()
        actions.append(Action.get_by_uuid(self.context, action['uuid']))
        result = self.executor.execute(actions)
        self.assertEqual(result, True)
