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

from watcher.common import exception
from watcher.db.sqlalchemy import api as db_api
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestStrategyObject(base.DbTestCase):

    goal_id = 2

    scenarios = [
        ('non_eager', dict(
            eager=False, fake_strategy=utils.get_test_strategy(
                goal_id=goal_id))),
        ('eager_with_non_eager_load', dict(
            eager=True, fake_strategy=utils.get_test_strategy(
                goal_id=goal_id))),
        ('eager_with_eager_load', dict(
            eager=True, fake_strategy=utils.get_test_strategy(
                goal_id=goal_id, goal=utils.get_test_goal(id=goal_id)))),
    ]

    def setUp(self):
        super(TestStrategyObject, self).setUp()
        self.fake_goal = utils.create_test_goal(id=self.goal_id)

    def eager_load_strategy_assert(self, strategy):
        if self.eager:
            self.assertIsNotNone(strategy.goal)
            fields_to_check = set(
                super(objects.Goal, objects.Goal).fields
            ).symmetric_difference(objects.Goal.fields)
            db_data = {
                k: v for k, v in self.fake_goal.as_dict().items()
                if k in fields_to_check}
            object_data = {
                k: v for k, v in strategy.goal.as_dict().items()
                if k in fields_to_check}
            self.assertEqual(db_data, object_data)

    @mock.patch.object(db_api.Connection, 'get_strategy_by_id')
    def test_get_by_id(self, mock_get_strategy):
        strategy_id = self.fake_strategy['id']
        mock_get_strategy.return_value = self.fake_strategy
        strategy = objects.Strategy.get(
            self.context, strategy_id, eager=self.eager)
        mock_get_strategy.assert_called_once_with(
            self.context, strategy_id, eager=self.eager)
        self.assertEqual(self.context, strategy._context)
        self.eager_load_strategy_assert(strategy)

    @mock.patch.object(db_api.Connection, 'get_strategy_by_uuid')
    def test_get_by_uuid(self, mock_get_strategy):
        uuid = self.fake_strategy['uuid']
        mock_get_strategy.return_value = self.fake_strategy
        strategy = objects.Strategy.get(self.context, uuid, eager=self.eager)
        mock_get_strategy.assert_called_once_with(
            self.context, uuid, eager=self.eager)
        self.assertEqual(self.context, strategy._context)
        self.eager_load_strategy_assert(strategy)

    def test_get_bad_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.Strategy.get, self.context, 'not-a-uuid')

    @mock.patch.object(db_api.Connection, 'get_strategy_list')
    def test_list(self, mock_get_list):
        mock_get_list.return_value = [self.fake_strategy]
        strategies = objects.Strategy.list(self.context, eager=self.eager)
        self.assertEqual(1, mock_get_list.call_count, 1)
        self.assertEqual(1, len(strategies))
        self.assertIsInstance(strategies[0], objects.Strategy)
        self.assertEqual(self.context, strategies[0]._context)
        for strategy in strategies:
            self.eager_load_strategy_assert(strategy)

    @mock.patch.object(db_api.Connection, 'update_strategy')
    @mock.patch.object(db_api.Connection, 'get_strategy_by_id')
    def test_save(self, mock_get_strategy, mock_update_strategy):
        _id = self.fake_strategy['id']
        mock_get_strategy.return_value = self.fake_strategy
        strategy = objects.Strategy.get_by_id(
            self.context, _id, eager=self.eager)
        strategy.name = 'UPDATED NAME'
        strategy.save()

        mock_get_strategy.assert_called_once_with(
            self.context, _id, eager=self.eager)
        mock_update_strategy.assert_called_once_with(
            _id, {'name': 'UPDATED NAME'})
        self.assertEqual(self.context, strategy._context)
        self.eager_load_strategy_assert(strategy)

    @mock.patch.object(db_api.Connection, 'get_strategy_by_id')
    def test_refresh(self, mock_get_strategy):
        _id = self.fake_strategy['id']
        returns = [dict(self.fake_strategy, name="first name"),
                   dict(self.fake_strategy, name="second name")]
        mock_get_strategy.side_effect = returns
        expected = [mock.call(self.context, _id, eager=self.eager),
                    mock.call(self.context, _id, eager=self.eager)]
        strategy = objects.Strategy.get(self.context, _id, eager=self.eager)
        self.assertEqual("first name", strategy.name)
        strategy.refresh(eager=self.eager)
        self.assertEqual("second name", strategy.name)
        self.assertEqual(expected, mock_get_strategy.call_args_list)
        self.assertEqual(self.context, strategy._context)
        self.eager_load_strategy_assert(strategy)


class TestCreateDeleteStrategyObject(base.DbTestCase):

    def setUp(self):
        super(TestCreateDeleteStrategyObject, self).setUp()
        self.fake_goal = utils.create_test_goal()
        self.fake_strategy = utils.get_test_strategy(goal_id=self.fake_goal.id)

    @mock.patch.object(db_api.Connection, 'create_strategy')
    def test_create(self, mock_create_strategy):
        mock_create_strategy.return_value = self.fake_strategy
        strategy = objects.Strategy(self.context, **self.fake_strategy)
        strategy.create()
        mock_create_strategy.assert_called_once_with(self.fake_strategy)
        self.assertEqual(self.context, strategy._context)

    @mock.patch.object(db_api.Connection, 'soft_delete_strategy')
    @mock.patch.object(db_api.Connection, 'get_strategy_by_id')
    def test_soft_delete(self, mock_get_strategy, mock_soft_delete):
        _id = self.fake_strategy['id']
        mock_get_strategy.return_value = self.fake_strategy
        strategy = objects.Strategy.get_by_id(self.context, _id)
        strategy.soft_delete()
        mock_get_strategy.assert_called_once_with(
            self.context, _id, eager=False)
        mock_soft_delete.assert_called_once_with(_id)
        self.assertEqual(self.context, strategy._context)

    @mock.patch.object(db_api.Connection, 'destroy_strategy')
    @mock.patch.object(db_api.Connection, 'get_strategy_by_id')
    def test_destroy(self, mock_get_strategy, mock_destroy_strategy):
        _id = self.fake_strategy['id']
        mock_get_strategy.return_value = self.fake_strategy
        strategy = objects.Strategy.get_by_id(self.context, _id)
        strategy.destroy()
        mock_get_strategy.assert_called_once_with(
            self.context, _id, eager=False)
        mock_destroy_strategy.assert_called_once_with(_id)
        self.assertEqual(self.context, strategy._context)
