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
from testtools.matchers import HasLength

from watcher.common import exception
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestStrategyObject(base.DbTestCase):

    def setUp(self):
        super(TestStrategyObject, self).setUp()
        self.fake_strategy = utils.get_test_strategy()

    def test_get_by_id(self):
        strategy_id = self.fake_strategy['id']
        with mock.patch.object(self.dbapi, 'get_strategy_by_id',
                               autospec=True) as mock_get_strategy:
            mock_get_strategy.return_value = self.fake_strategy
            strategy = objects.Strategy.get(self.context, strategy_id)
            mock_get_strategy.assert_called_once_with(self.context,
                                                      strategy_id)
            self.assertEqual(self.context, strategy._context)

    def test_get_by_uuid(self):
        uuid = self.fake_strategy['uuid']
        with mock.patch.object(self.dbapi, 'get_strategy_by_uuid',
                               autospec=True) as mock_get_strategy:
            mock_get_strategy.return_value = self.fake_strategy
            strategy = objects.Strategy.get(self.context, uuid)
            mock_get_strategy.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, strategy._context)

    def test_get_bad_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.Strategy.get, self.context, 'not-a-uuid')

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_strategy_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_strategy]
            strategies = objects.Strategy.list(self.context)
            self.assertEqual(1, mock_get_list.call_count, 1)
            self.assertThat(strategies, HasLength(1))
            self.assertIsInstance(strategies[0], objects.Strategy)
            self.assertEqual(self.context, strategies[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_strategy',
                               autospec=True) as mock_create_strategy:
            mock_create_strategy.return_value = self.fake_strategy
            strategy = objects.Strategy(self.context, **self.fake_strategy)

            strategy.create()
            mock_create_strategy.assert_called_once_with(self.fake_strategy)
            self.assertEqual(self.context, strategy._context)

    def test_destroy(self):
        _id = self.fake_strategy['id']
        with mock.patch.object(self.dbapi, 'get_strategy_by_id',
                               autospec=True) as mock_get_strategy:
            mock_get_strategy.return_value = self.fake_strategy
            with mock.patch.object(self.dbapi, 'destroy_strategy',
                                   autospec=True) as mock_destroy_strategy:
                strategy = objects.Strategy.get_by_id(self.context, _id)
                strategy.destroy()
                mock_get_strategy.assert_called_once_with(self.context, _id)
                mock_destroy_strategy.assert_called_once_with(_id)
                self.assertEqual(self.context, strategy._context)

    def test_save(self):
        _id = self.fake_strategy['id']
        with mock.patch.object(self.dbapi, 'get_strategy_by_id',
                               autospec=True) as mock_get_strategy:
            mock_get_strategy.return_value = self.fake_strategy
            with mock.patch.object(self.dbapi, 'update_strategy',
                                   autospec=True) as mock_update_strategy:
                strategy = objects.Strategy.get_by_id(self.context, _id)
                strategy.name = 'UPDATED NAME'
                strategy.save()

                mock_get_strategy.assert_called_once_with(self.context, _id)
                mock_update_strategy.assert_called_once_with(
                    _id, {'name': 'UPDATED NAME'})
                self.assertEqual(self.context, strategy._context)

    def test_refresh(self):
        _id = self.fake_strategy['id']
        returns = [dict(self.fake_strategy, name="first name"),
                   dict(self.fake_strategy, name="second name")]
        expected = [mock.call(self.context, _id),
                    mock.call(self.context, _id)]
        with mock.patch.object(self.dbapi, 'get_strategy_by_id',
                               side_effect=returns,
                               autospec=True) as mock_get_strategy:
            strategy = objects.Strategy.get(self.context, _id)
            self.assertEqual("first name", strategy.name)
            strategy.refresh()
            self.assertEqual("second name", strategy.name)
            self.assertEqual(expected, mock_get_strategy.call_args_list)
            self.assertEqual(self.context, strategy._context)

    def test_soft_delete(self):
        _id = self.fake_strategy['id']
        with mock.patch.object(self.dbapi, 'get_strategy_by_id',
                               autospec=True) as mock_get_strategy:
            mock_get_strategy.return_value = self.fake_strategy
            with mock.patch.object(self.dbapi, 'soft_delete_strategy',
                                   autospec=True) as mock_soft_delete:
                strategy = objects.Strategy.get_by_id(self.context, _id)
                strategy.soft_delete()
                mock_get_strategy.assert_called_once_with(self.context, _id)
                mock_soft_delete.assert_called_once_with(_id)
                self.assertEqual(self.context, strategy._context)
