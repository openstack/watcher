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

import datetime

import iso8601
import mock

from watcher.db.sqlalchemy import api as db_api
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestGoalObject(base.DbTestCase):

    def setUp(self):
        super(TestGoalObject, self).setUp()
        self.fake_goal = utils.get_test_goal(
            created_at=datetime.datetime.utcnow())

    @mock.patch.object(db_api.Connection, 'get_goal_by_id')
    def test_get_by_id(self, mock_get_goal):
        goal_id = self.fake_goal['id']
        mock_get_goal.return_value = self.fake_goal
        goal = objects.Goal.get(self.context, goal_id)
        mock_get_goal.assert_called_once_with(self.context, goal_id)
        self.assertEqual(self.context, goal._context)

    @mock.patch.object(db_api.Connection, 'get_goal_by_uuid')
    def test_get_by_uuid(self, mock_get_goal):
        uuid = self.fake_goal['uuid']
        mock_get_goal.return_value = self.fake_goal
        goal = objects.Goal.get(self.context, uuid)
        mock_get_goal.assert_called_once_with(self.context, uuid)
        self.assertEqual(self.context, goal._context)

    @mock.patch.object(db_api.Connection, 'get_goal_by_name')
    def test_get_by_name(self, mock_get_goal):
        name = self.fake_goal['name']
        mock_get_goal.return_value = self.fake_goal
        goal = objects.Goal.get_by_name(self.context, name)
        mock_get_goal.assert_called_once_with(self.context, name)
        self.assertEqual(self.context, goal._context)

    @mock.patch.object(db_api.Connection, 'get_goal_list')
    def test_list(self, mock_get_list):
        mock_get_list.return_value = [self.fake_goal]
        goals = objects.Goal.list(self.context)
        self.assertEqual(1, mock_get_list.call_count)
        self.assertEqual(1, len(goals))
        self.assertIsInstance(goals[0], objects.Goal)
        self.assertEqual(self.context, goals[0]._context)

    @mock.patch.object(db_api.Connection, 'create_goal')
    def test_create(self, mock_create_goal):
        mock_create_goal.return_value = self.fake_goal
        goal = objects.Goal(self.context, **self.fake_goal)
        goal.create()
        expected_goal = self.fake_goal.copy()
        expected_goal['created_at'] = expected_goal['created_at'].replace(
            tzinfo=iso8601.UTC)
        mock_create_goal.assert_called_once_with(expected_goal)
        self.assertEqual(self.context, goal._context)

    @mock.patch.object(db_api.Connection, 'destroy_goal')
    @mock.patch.object(db_api.Connection, 'get_goal_by_id')
    def test_destroy(self, mock_get_goal, mock_destroy_goal):
        goal_id = self.fake_goal['id']
        mock_get_goal.return_value = self.fake_goal
        goal = objects.Goal.get_by_id(self.context, goal_id)
        goal.destroy()
        mock_get_goal.assert_called_once_with(
            self.context, goal_id)
        mock_destroy_goal.assert_called_once_with(goal_id)
        self.assertEqual(self.context, goal._context)

    @mock.patch.object(db_api.Connection, 'update_goal')
    @mock.patch.object(db_api.Connection, 'get_goal_by_uuid')
    def test_save(self, mock_get_goal, mock_update_goal):
        mock_get_goal.return_value = self.fake_goal
        goal_uuid = self.fake_goal['uuid']
        fake_saved_goal = self.fake_goal.copy()
        fake_saved_goal['updated_at'] = datetime.datetime.utcnow()
        mock_update_goal.return_value = fake_saved_goal

        goal = objects.Goal.get_by_uuid(self.context, goal_uuid)
        goal.display_name = 'DUMMY'
        goal.save()

        mock_get_goal.assert_called_once_with(self.context, goal_uuid)
        mock_update_goal.assert_called_once_with(
            goal_uuid, {'display_name': 'DUMMY'})
        self.assertEqual(self.context, goal._context)

    @mock.patch.object(db_api.Connection, 'get_goal_by_uuid')
    def test_refresh(self, mock_get_goal):
        fake_goal2 = utils.get_test_goal(name="BALANCE_LOAD")
        returns = [self.fake_goal, fake_goal2]
        mock_get_goal.side_effect = returns
        uuid = self.fake_goal['uuid']
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        goal = objects.Goal.get(self.context, uuid)
        self.assertEqual("TEST", goal.name)
        goal.refresh()
        self.assertEqual("BALANCE_LOAD", goal.name)
        self.assertEqual(expected, mock_get_goal.call_args_list)
        self.assertEqual(self.context, goal._context)

    @mock.patch.object(db_api.Connection, 'soft_delete_goal')
    @mock.patch.object(db_api.Connection, 'get_goal_by_uuid')
    def test_soft_delete(self, mock_get_goal, mock_soft_delete_goal):
        mock_get_goal.return_value = self.fake_goal
        fake_deleted_goal = self.fake_goal.copy()
        fake_deleted_goal['deleted_at'] = datetime.datetime.utcnow()
        mock_soft_delete_goal.return_value = fake_deleted_goal

        expected_goal = fake_deleted_goal.copy()
        expected_goal['created_at'] = expected_goal['created_at'].replace(
            tzinfo=iso8601.UTC)
        expected_goal['deleted_at'] = expected_goal['deleted_at'].replace(
            tzinfo=iso8601.UTC)

        uuid = self.fake_goal['uuid']
        goal = objects.Goal.get_by_uuid(self.context, uuid)
        goal.soft_delete()
        mock_get_goal.assert_called_once_with(self.context, uuid)
        mock_soft_delete_goal.assert_called_once_with(uuid)
        self.assertEqual(self.context, goal._context)
        self.assertEqual(expected_goal, goal.as_dict())
