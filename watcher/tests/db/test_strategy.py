# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.


"""Tests for manipulating Strategy via the DB API"""

import freezegun
import six

from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.tests.db import base
from watcher.tests.db import utils


class TestDbStrategyFilters(base.DbTestCase):

    FAKE_OLDER_DATE = '2014-01-01T09:52:05.219414'
    FAKE_OLD_DATE = '2015-01-01T09:52:05.219414'
    FAKE_TODAY = '2016-02-24T09:52:05.219414'

    def setUp(self):
        super(TestDbStrategyFilters, self).setUp()
        self.context.show_deleted = True
        self._data_setup()

    def _data_setup(self):
        strategy1_name = "STRATEGY_ID_1"
        strategy2_name = "STRATEGY_ID_2"
        strategy3_name = "STRATEGY_ID_3"

        self.goal1 = utils.create_test_goal(
            id=1, uuid=w_utils.generate_uuid(),
            name="GOAL_ID", display_name="Goal")
        self.goal2 = utils.create_test_goal(
            id=2, uuid=w_utils.generate_uuid(),
            name="DUMMY", display_name="Dummy")

        with freezegun.freeze_time(self.FAKE_TODAY):
            self.strategy1 = utils.create_test_strategy(
                id=1, uuid=w_utils.generate_uuid(),
                name=strategy1_name, display_name="Strategy 1",
                goal_id=self.goal1.id)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.strategy2 = utils.create_test_strategy(
                id=2, uuid=w_utils.generate_uuid(),
                name=strategy2_name, display_name="Strategy 2",
                goal_id=self.goal1.id)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.strategy3 = utils.create_test_strategy(
                id=3, uuid=w_utils.generate_uuid(),
                name=strategy3_name, display_name="Strategy 3",
                goal_id=self.goal2.id)

    def _soft_delete_strategys(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_strategy(self.strategy1.id)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.soft_delete_strategy(self.strategy2.id)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.soft_delete_strategy(self.strategy3.id)

    def _update_strategies(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.update_strategy(
                self.strategy1.id, values={"display_name": "strategy1"})
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.update_strategy(
                self.strategy2.id, values={"display_name": "strategy2"})
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.update_strategy(
                self.strategy3.id, values={"display_name": "strategy3"})

    def test_get_strategy_list_filter_deleted_true(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_strategy(self.strategy1.id)

        res = self.dbapi.get_strategy_list(
            self.context, filters={'deleted': True})

        self.assertEqual([self.strategy1['uuid']], [r.uuid for r in res])

    def test_get_strategy_list_filter_deleted_false(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_strategy(self.strategy1.id)

        res = self.dbapi.get_strategy_list(
            self.context, filters={'deleted': False})

        self.assertEqual(
            set([self.strategy2['uuid'], self.strategy3['uuid']]),
            set([r.uuid for r in res]))

    def test_get_strategy_list_filter_deleted_at_eq(self):
        self._soft_delete_strategys()

        res = self.dbapi.get_strategy_list(
            self.context, filters={'deleted_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.strategy1['uuid']], [r.uuid for r in res])

    def test_get_strategy_list_filter_deleted_at_lt(self):
        self._soft_delete_strategys()

        res = self.dbapi.get_strategy_list(
            self.context, filters={'deleted_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.strategy2['uuid'], self.strategy3['uuid']]),
            set([r.uuid for r in res]))

    def test_get_strategy_list_filter_deleted_at_lte(self):
        self._soft_delete_strategys()

        res = self.dbapi.get_strategy_list(
            self.context, filters={'deleted_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.strategy2['uuid'], self.strategy3['uuid']]),
            set([r.uuid for r in res]))

    def test_get_strategy_list_filter_deleted_at_gt(self):
        self._soft_delete_strategys()

        res = self.dbapi.get_strategy_list(
            self.context, filters={'deleted_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.strategy1['uuid']], [r.uuid for r in res])

    def test_get_strategy_list_filter_deleted_at_gte(self):
        self._soft_delete_strategys()

        res = self.dbapi.get_strategy_list(
            self.context, filters={'deleted_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.strategy1['uuid'], self.strategy2['uuid']]),
            set([r.uuid for r in res]))

    # created_at #

    def test_get_strategy_list_filter_created_at_eq(self):
        res = self.dbapi.get_strategy_list(
            self.context, filters={'created_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.strategy1['uuid']], [r.uuid for r in res])

    def test_get_strategy_list_filter_created_at_lt(self):
        res = self.dbapi.get_strategy_list(
            self.context, filters={'created_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.strategy2['uuid'], self.strategy3['uuid']]),
            set([r.uuid for r in res]))

    def test_get_strategy_list_filter_created_at_lte(self):
        res = self.dbapi.get_strategy_list(
            self.context, filters={'created_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.strategy2['uuid'], self.strategy3['uuid']]),
            set([r.uuid for r in res]))

    def test_get_strategy_list_filter_created_at_gt(self):
        res = self.dbapi.get_strategy_list(
            self.context, filters={'created_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.strategy1['uuid']], [r.uuid for r in res])

    def test_get_strategy_list_filter_created_at_gte(self):
        res = self.dbapi.get_strategy_list(
            self.context, filters={'created_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.strategy1['uuid'], self.strategy2['uuid']]),
            set([r.uuid for r in res]))

    # updated_at #

    def test_get_strategy_list_filter_updated_at_eq(self):
        self._update_strategies()

        res = self.dbapi.get_strategy_list(
            self.context, filters={'updated_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.strategy1['uuid']], [r.uuid for r in res])

    def test_get_strategy_list_filter_updated_at_lt(self):
        self._update_strategies()

        res = self.dbapi.get_strategy_list(
            self.context, filters={'updated_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.strategy2['uuid'], self.strategy3['uuid']]),
            set([r.uuid for r in res]))

    def test_get_strategy_list_filter_updated_at_lte(self):
        self._update_strategies()

        res = self.dbapi.get_strategy_list(
            self.context, filters={'updated_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.strategy2['uuid'], self.strategy3['uuid']]),
            set([r.uuid for r in res]))

    def test_get_strategy_list_filter_updated_at_gt(self):
        self._update_strategies()

        res = self.dbapi.get_strategy_list(
            self.context, filters={'updated_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.strategy1['uuid']], [r.uuid for r in res])

    def test_get_strategy_list_filter_updated_at_gte(self):
        self._update_strategies()

        res = self.dbapi.get_strategy_list(
            self.context, filters={'updated_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.strategy1['uuid'], self.strategy2['uuid']]),
            set([r.uuid for r in res]))


class DbStrategyTestCase(base.DbTestCase):

    def test_get_strategy_list(self):
        uuids = []
        for i in range(1, 4):
            strategy = utils.create_test_strategy(
                id=i,
                uuid=w_utils.generate_uuid(),
                name="STRATEGY_ID_%s" % i,
                display_name='My Strategy {0}'.format(i))
            uuids.append(six.text_type(strategy['uuid']))
        strategies = self.dbapi.get_strategy_list(self.context)
        strategy_uuids = [s.uuid for s in strategies]
        self.assertEqual(sorted(uuids), sorted(strategy_uuids))
        for strategy in strategies:
            self.assertIsNone(strategy.goal)

    def test_get_strategy_list_eager(self):
        _goal = utils.get_test_goal()
        goal = self.dbapi.create_goal(_goal)
        uuids = []
        for i in range(1, 4):
            strategy = utils.create_test_strategy(
                id=i,
                uuid=w_utils.generate_uuid(),
                name="STRATEGY_ID_%s" % i,
                display_name='My Strategy {0}'.format(i),
                goal_id=goal.id)
            uuids.append(six.text_type(strategy['uuid']))
        strategys = self.dbapi.get_strategy_list(self.context, eager=True)
        strategy_map = {a.uuid: a for a in strategys}
        self.assertEqual(sorted(uuids), sorted(strategy_map.keys()))
        eager_strategy = strategy_map[strategy.uuid]
        self.assertEqual(goal.as_dict(), eager_strategy.goal.as_dict())

    def test_get_strategy_list_with_filters(self):
        # NOTE(erakli): we don't create goal in database but links to
        # goal_id = 1. There is no error in dbapi.create_strategy() method.
        # Is it right behaviour?
        strategy1 = utils.create_test_strategy(
            id=1,
            uuid=w_utils.generate_uuid(),
            name="STRATEGY_ID_1",
            display_name='Strategy 1',
        )
        strategy2 = utils.create_test_strategy(
            id=2,
            uuid=w_utils.generate_uuid(),
            name="STRATEGY_ID_2",
            display_name='Strategy 2',
        )
        strategy3 = utils.create_test_strategy(
            id=3,
            uuid=w_utils.generate_uuid(),
            name="STRATEGY_ID_3",
            display_name='Strategy 3',
        )

        self.dbapi.soft_delete_strategy(strategy3['uuid'])

        res = self.dbapi.get_strategy_list(
            self.context, filters={'display_name': 'Strategy 1'})
        self.assertEqual([strategy1['uuid']], [r.uuid for r in res])

        res = self.dbapi.get_strategy_list(
            self.context, filters={'display_name': 'Strategy 3'})
        self.assertEqual([], [r.uuid for r in res])

        res = self.dbapi.get_strategy_list(
            self.context, filters={'goal_id': 1})
        self.assertEqual([strategy1['uuid'], strategy2['uuid']],
                         [r.uuid for r in res])

        res = self.dbapi.get_strategy_list(
            self.context, filters={'display_name': 'Strategy 2'})
        self.assertEqual([strategy2['uuid']], [r.uuid for r in res])

    def test_get_strategy_by_uuid(self):
        created_strategy = utils.create_test_strategy()
        strategy = self.dbapi.get_strategy_by_uuid(
            self.context, created_strategy['uuid'])
        self.assertEqual(strategy.uuid, created_strategy['uuid'])

    def test_get_strategy_by_name(self):
        created_strategy = utils.create_test_strategy()
        strategy = self.dbapi.get_strategy_by_name(
            self.context, created_strategy['name'])
        self.assertEqual(strategy.name, created_strategy['name'])

    def test_get_strategy_that_does_not_exist(self):
        self.assertRaises(exception.StrategyNotFound,
                          self.dbapi.get_strategy_by_id,
                          self.context, 404)

    def test_update_strategy(self):
        strategy = utils.create_test_strategy()
        res = self.dbapi.update_strategy(
            strategy['uuid'], {'display_name': 'updated-model'})
        self.assertEqual('updated-model', res.display_name)

    def test_update_goal_id(self):
        strategy = utils.create_test_strategy()
        self.assertRaises(exception.Invalid,
                          self.dbapi.update_strategy, strategy['uuid'],
                          {'uuid': 'new_strategy_id'})

    def test_update_strategy_that_does_not_exist(self):
        self.assertRaises(exception.StrategyNotFound,
                          self.dbapi.update_strategy,
                          404,
                          {'display_name': ''})

    def test_destroy_strategy(self):
        strategy = utils.create_test_strategy()
        self.dbapi.destroy_strategy(strategy['uuid'])
        self.assertRaises(exception.StrategyNotFound,
                          self.dbapi.get_strategy_by_id,
                          self.context, strategy['uuid'])

    def test_destroy_strategy_that_does_not_exist(self):
        self.assertRaises(exception.StrategyNotFound,
                          self.dbapi.destroy_strategy, 404)

    def test_create_strategy_already_exists(self):
        strategy_id = "STRATEGY_ID"
        utils.create_test_strategy(name=strategy_id)
        self.assertRaises(exception.StrategyAlreadyExists,
                          utils.create_test_strategy,
                          name=strategy_id)
