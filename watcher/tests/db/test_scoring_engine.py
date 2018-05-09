# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Intel
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


"""Tests for manipulating ScoringEngine via the DB API"""

import freezegun
import six

from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.tests.db import base
from watcher.tests.db import utils


class TestDbScoringEngineFilters(base.DbTestCase):

    FAKE_OLDER_DATE = '2014-01-01T09:52:05.219414'
    FAKE_OLD_DATE = '2015-01-01T09:52:05.219414'
    FAKE_TODAY = '2016-02-24T09:52:05.219414'

    def setUp(self):
        super(TestDbScoringEngineFilters, self).setUp()
        self.context.show_deleted = True
        self._data_setup()

    def _data_setup(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.scoring_engine1 = utils.create_test_scoring_engine(
                id=1, uuid='e8370ede-4f39-11e6-9ffa-08002722cb22',
                name="se-1", description="Scoring Engine 1", metainfo="a1=b1")
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.scoring_engine2 = utils.create_test_scoring_engine(
                id=2, uuid='e8370ede-4f39-11e6-9ffa-08002722cb23',
                name="se-2", description="Scoring Engine 2", metainfo="a2=b2")
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.scoring_engine3 = utils.create_test_scoring_engine(
                id=3, uuid='e8370ede-4f39-11e6-9ffa-08002722cb24',
                name="se-3", description="Scoring Engine 3", metainfo="a3=b3")

    def _soft_delete_scoring_engines(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_scoring_engine(self.scoring_engine1.id)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.soft_delete_scoring_engine(self.scoring_engine2.id)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.soft_delete_scoring_engine(self.scoring_engine3.id)

    def _update_scoring_engines(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.update_scoring_engine(
                self.scoring_engine1.id,
                values={"description": "scoring_engine1"})
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.update_scoring_engine(
                self.scoring_engine2.id,
                values={"description": "scoring_engine2"})
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.update_scoring_engine(
                self.scoring_engine3.id,
                values={"description": "scoring_engine3"})

    def test_get_scoring_engine_list_filter_deleted_true(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_scoring_engine(self.scoring_engine1.id)

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'deleted': True})

        self.assertEqual([self.scoring_engine1['id']], [r.id for r in res])

    def test_get_scoring_engine_list_filter_deleted_false(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_scoring_engine(self.scoring_engine1.id)

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'deleted': False})

        self.assertEqual(
            set([self.scoring_engine2['id'], self.scoring_engine3['id']]),
            set([r.id for r in res]))

    def test_get_scoring_engine_list_filter_deleted_at_eq(self):
        self._soft_delete_scoring_engines()

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'deleted_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.scoring_engine1['id']], [r.id for r in res])

    def test_get_scoring_engine_list_filter_deleted_at_lt(self):
        self._soft_delete_scoring_engines()

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'deleted_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.scoring_engine2['id'], self.scoring_engine3['id']]),
            set([r.id for r in res]))

    def test_get_scoring_engine_list_filter_deleted_at_lte(self):
        self._soft_delete_scoring_engines()

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'deleted_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.scoring_engine2['id'], self.scoring_engine3['id']]),
            set([r.id for r in res]))

    def test_get_scoring_engine_list_filter_deleted_at_gt(self):
        self._soft_delete_scoring_engines()

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'deleted_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.scoring_engine1['id']], [r.id for r in res])

    def test_get_scoring_engine_list_filter_deleted_at_gte(self):
        self._soft_delete_scoring_engines()

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'deleted_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.scoring_engine1['id'], self.scoring_engine2['id']]),
            set([r.id for r in res]))

    # created_at #

    def test_get_scoring_engine_list_filter_created_at_eq(self):
        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'created_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.scoring_engine1['id']], [r.id for r in res])

    def test_get_scoring_engine_list_filter_created_at_lt(self):
        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'created_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.scoring_engine2['id'], self.scoring_engine3['id']]),
            set([r.id for r in res]))

    def test_get_scoring_engine_list_filter_created_at_lte(self):
        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'created_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.scoring_engine2['id'], self.scoring_engine3['id']]),
            set([r.id for r in res]))

    def test_get_scoring_engine_list_filter_created_at_gt(self):
        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'created_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.scoring_engine1['id']], [r.id for r in res])

    def test_get_scoring_engine_list_filter_created_at_gte(self):
        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'created_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.scoring_engine1['id'], self.scoring_engine2['id']]),
            set([r.id for r in res]))

    # updated_at #

    def test_get_scoring_engine_list_filter_updated_at_eq(self):
        self._update_scoring_engines()

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'updated_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.scoring_engine1['id']], [r.id for r in res])

    def test_get_scoring_engine_list_filter_updated_at_lt(self):
        self._update_scoring_engines()

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'updated_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.scoring_engine2['id'], self.scoring_engine3['id']]),
            set([r.id for r in res]))

    def test_get_scoring_engine_list_filter_updated_at_lte(self):
        self._update_scoring_engines()

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'updated_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.scoring_engine2['id'], self.scoring_engine3['id']]),
            set([r.id for r in res]))

    def test_get_scoring_engine_list_filter_updated_at_gt(self):
        self._update_scoring_engines()

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'updated_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.scoring_engine1['id']], [r.id for r in res])

    def test_get_scoring_engine_list_filter_updated_at_gte(self):
        self._update_scoring_engines()

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'updated_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.scoring_engine1['id'], self.scoring_engine2['id']]),
            set([r.id for r in res]))


class DbScoringEngineTestCase(base.DbTestCase):

    def test_get_scoring_engine_list(self):
        names = []
        for i in range(1, 4):
            scoring_engine = utils.create_test_scoring_engine(
                id=i,
                uuid=w_utils.generate_uuid(),
                name="SE_ID_%s" % i,
                description='My ScoringEngine {0}'.format(i),
                metainfo='a{0}=b{0}'.format(i))
            names.append(six.text_type(scoring_engine['name']))
        scoring_engines = self.dbapi.get_scoring_engine_list(self.context)
        scoring_engines_names = [se.name for se in scoring_engines]
        self.assertEqual(sorted(names), sorted(scoring_engines_names))

    def test_get_scoring_engine_list_with_filters(self):
        scoring_engine1 = utils.create_test_scoring_engine(
            id=1,
            uuid=w_utils.generate_uuid(),
            name="SE_ID_1",
            description='ScoringEngine 1',
            metainfo="a1=b1",
        )
        scoring_engine2 = utils.create_test_scoring_engine(
            id=2,
            uuid=w_utils.generate_uuid(),
            name="SE_ID_2",
            description='ScoringEngine 2',
            metainfo="a2=b2",
        )
        scoring_engine3 = utils.create_test_scoring_engine(
            id=3,
            uuid=w_utils.generate_uuid(),
            name="SE_ID_3",
            description='ScoringEngine 3',
            metainfo="a3=b3",
        )

        self.dbapi.soft_delete_scoring_engine(scoring_engine3['uuid'])

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'description': 'ScoringEngine 1'})
        self.assertEqual([scoring_engine1['name']], [r.name for r in res])

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'description': 'ScoringEngine 3'})
        self.assertEqual([], [r.name for r in res])

        res = self.dbapi.get_scoring_engine_list(
            self.context, filters={'description': 'ScoringEngine 2'})
        self.assertEqual([scoring_engine2['name']], [r.name for r in res])

    def test_get_scoring_engine_by_id(self):
        created_scoring_engine = utils.create_test_scoring_engine()
        scoring_engine = self.dbapi.get_scoring_engine_by_id(
            self.context, created_scoring_engine['id'])
        self.assertEqual(scoring_engine.id, created_scoring_engine['id'])

    def test_get_scoring_engine_by_uuid(self):
        created_scoring_engine = utils.create_test_scoring_engine()
        scoring_engine = self.dbapi.get_scoring_engine_by_uuid(
            self.context, created_scoring_engine['uuid'])
        self.assertEqual(scoring_engine.uuid, created_scoring_engine['uuid'])

    def test_get_scoring_engine_by_name(self):
        created_scoring_engine = utils.create_test_scoring_engine()
        scoring_engine = self.dbapi.get_scoring_engine_by_name(
            self.context, created_scoring_engine['name'])
        self.assertEqual(scoring_engine.name, created_scoring_engine['name'])

    def test_get_scoring_engine_that_does_not_exist(self):
        self.assertRaises(exception.ScoringEngineNotFound,
                          self.dbapi.get_scoring_engine_by_id,
                          self.context, 404)

    def test_update_scoring_engine(self):
        scoring_engine = utils.create_test_scoring_engine()
        res = self.dbapi.update_scoring_engine(
            scoring_engine['id'], {'description': 'updated-model'})
        self.assertEqual('updated-model', res.description)

    def test_update_scoring_engine_id(self):
        scoring_engine = utils.create_test_scoring_engine()
        self.assertRaises(exception.Invalid,
                          self.dbapi.update_scoring_engine,
                          scoring_engine['id'],
                          {'uuid': w_utils.generate_uuid()})

    def test_update_scoring_engine_that_does_not_exist(self):
        self.assertRaises(exception.ScoringEngineNotFound,
                          self.dbapi.update_scoring_engine,
                          404,
                          {'description': ''})

    def test_destroy_scoring_engine(self):
        scoring_engine = utils.create_test_scoring_engine()
        self.dbapi.destroy_scoring_engine(scoring_engine['id'])
        self.assertRaises(exception.ScoringEngineNotFound,
                          self.dbapi.get_scoring_engine_by_id,
                          self.context, scoring_engine['id'])

    def test_destroy_scoring_engine_that_does_not_exist(self):
        self.assertRaises(exception.ScoringEngineNotFound,
                          self.dbapi.destroy_scoring_engine, 404)

    def test_create_scoring_engine_already_exists(self):
        scoring_engine_id = "SE_ID"
        utils.create_test_scoring_engine(name=scoring_engine_id)
        self.assertRaises(exception.ScoringEngineAlreadyExists,
                          utils.create_test_scoring_engine,
                          name=scoring_engine_id)
