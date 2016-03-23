# Copyright 2015 OpenStack Foundation
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import mock

from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestGoalObject(base.DbTestCase):

    def setUp(self):
        super(TestGoalObject, self).setUp()
        self.fake_goal = utils.get_test_goal()

    def test_get_by_id(self):
        goal_id = self.fake_goal['id']
        with mock.patch.object(self.dbapi, 'get_goal_by_id',
                               autospec=True) as mock_get_goal:
            mock_get_goal.return_value = self.fake_goal
            goal = objects.Goal.get(self.context, goal_id)
            mock_get_goal.assert_called_once_with(self.context, goal_id)
            self.assertEqual(self.context, goal._context)

    def test_get_by_uuid(self):
        uuid = self.fake_goal['uuid']
        with mock.patch.object(self.dbapi, 'get_goal_by_uuid',
                               autospec=True) as mock_get_goal:
            mock_get_goal.return_value = self.fake_goal
            goal = objects.Goal.get(self.context, uuid)
            mock_get_goal.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, goal._context)

    def test_get_by_name(self):
        name = self.fake_goal['name']
        with mock.patch.object(self.dbapi, 'get_goal_by_name',
                               autospec=True) as mock_get_goal:
            mock_get_goal.return_value = self.fake_goal
            goal = objects.Goal.get_by_name(
                self.context,
                name)
            mock_get_goal.assert_called_once_with(self.context, name)
            self.assertEqual(self.context, goal._context)

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_goal_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_goal]
            goals = objects.Goal.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertEqual(1, len(goals))
            self.assertIsInstance(goals[0], objects.Goal)
            self.assertEqual(self.context, goals[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_goal',
                               autospec=True) as mock_create_goal:
            mock_create_goal.return_value = self.fake_goal
            goal = objects.Goal(self.context, **self.fake_goal)
            goal.create()
            mock_create_goal.assert_called_once_with(self.fake_goal)
            self.assertEqual(self.context, goal._context)

    def test_destroy(self):
        goal_id = self.fake_goal['id']
        with mock.patch.object(self.dbapi, 'get_goal_by_id',
                               autospec=True) as mock_get_goal:
            mock_get_goal.return_value = self.fake_goal
            with mock.patch.object(self.dbapi, 'destroy_goal',
                                   autospec=True) \
                    as mock_destroy_goal:
                goal = objects.Goal.get_by_id(self.context, goal_id)
                goal.destroy()
                mock_get_goal.assert_called_once_with(
                    self.context, goal_id)
                mock_destroy_goal.assert_called_once_with(goal_id)
                self.assertEqual(self.context, goal._context)

    def test_save(self):
        goal_id = self.fake_goal['id']
        with mock.patch.object(self.dbapi, 'get_goal_by_id',
                               autospec=True) as mock_get_goal:
            mock_get_goal.return_value = self.fake_goal
            with mock.patch.object(self.dbapi, 'update_goal',
                                   autospec=True) as mock_update_goal:
                goal = objects.Goal.get_by_id(self.context, goal_id)
                goal.display_name = 'DUMMY'
                goal.save()

                mock_get_goal.assert_called_once_with(self.context, goal_id)
                mock_update_goal.assert_called_once_with(
                    goal_id, {'display_name': 'DUMMY'})
                self.assertEqual(self.context, goal._context)

    def test_refresh(self):
        uuid = self.fake_goal['uuid']
        fake_goal2 = utils.get_test_goal(name="BALANCE_LOAD")
        returns = [self.fake_goal, fake_goal2]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_goal_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_goal:
            goal = objects.Goal.get(self.context, uuid)
            self.assertEqual("TEST", goal.name)
            goal.refresh()
            self.assertEqual("BALANCE_LOAD", goal.name)
            self.assertEqual(expected, mock_get_goal.call_args_list)
            self.assertEqual(self.context, goal._context)

    def test_soft_delete(self):
        uuid = self.fake_goal['uuid']
        with mock.patch.object(self.dbapi, 'get_goal_by_uuid',
                               autospec=True) as mock_get_goal:
            mock_get_goal.return_value = self.fake_goal
            with mock.patch.object(self.dbapi, 'soft_delete_goal',
                                   autospec=True) \
                    as mock_soft_delete_goal:
                goal = objects.Goal.get_by_uuid(
                    self.context, uuid)
                goal.soft_delete()
                mock_get_goal.assert_called_once_with(
                    self.context, uuid)
                mock_soft_delete_goal.assert_called_once_with(uuid)
                self.assertEqual(self.context, goal._context)
