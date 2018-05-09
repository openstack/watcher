# -*- encoding: utf-8 -*-
# Copyright (c) 2017 ZTE
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


"""Tests for manipulating ActionDescription via the DB API"""

import freezegun

from watcher.common import exception
from watcher.tests.db import base
from watcher.tests.db import utils


class TestDbActionDescriptionFilters(base.DbTestCase):

    FAKE_OLDER_DATE = '2015-01-01T09:52:05.219414'
    FAKE_OLD_DATE = '2016-01-01T09:52:05.219414'
    FAKE_TODAY = '2017-02-24T09:52:05.219414'

    def setUp(self):
        super(TestDbActionDescriptionFilters, self).setUp()
        self.context.show_deleted = True
        self._data_setup()

    def _data_setup(self):
        action_desc1_type = "nop"
        action_desc2_type = "sleep"
        action_desc3_type = "resize"

        with freezegun.freeze_time(self.FAKE_TODAY):
            self.action_desc1 = utils.create_test_action_desc(
                id=1, action_type=action_desc1_type,
                description="description")
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.action_desc2 = utils.create_test_action_desc(
                id=2, action_type=action_desc2_type,
                description="description")
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.action_desc3 = utils.create_test_action_desc(
                id=3, action_type=action_desc3_type,
                description="description")

    def _soft_delete_action_descs(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_action_description(self.action_desc1.id)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.soft_delete_action_description(self.action_desc2.id)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.soft_delete_action_description(self.action_desc3.id)

    def _update_action_descs(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.update_action_description(
                self.action_desc1.id, values={"description":
                                              "nop description"})
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.update_action_description(
                self.action_desc2.id, values={"description":
                                              "sleep description"})
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.update_action_description(
                self.action_desc3.id, values={"description":
                                              "resize description"})

    def test_get_action_desc_list_filter_deleted_true(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_action_description(self.action_desc1.id)

        res = self.dbapi.get_action_description_list(
            self.context, filters={'deleted': True})

        self.assertEqual([self.action_desc1['action_type']],
                         [r.action_type for r in res])

    def test_get_action_desc_list_filter_deleted_false(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_action_description(self.action_desc1.id)

        res = self.dbapi.get_action_description_list(
            self.context, filters={'deleted': False})

        self.assertEqual(
            set([self.action_desc2['action_type'],
                self.action_desc3['action_type']]),
            set([r.action_type for r in res]))

    def test_get_action_desc_list_filter_deleted_at_eq(self):
        self._soft_delete_action_descs()

        res = self.dbapi.get_action_description_list(
            self.context, filters={'deleted_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.action_desc1['id']], [r.id for r in res])

    def test_get_action_desc_list_filter_deleted_at_lt(self):
        self._soft_delete_action_descs()

        res = self.dbapi.get_action_description_list(
            self.context, filters={'deleted_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.action_desc2['id'], self.action_desc3['id']]),
            set([r.id for r in res]))

    def test_get_action_desc_list_filter_deleted_at_lte(self):
        self._soft_delete_action_descs()

        res = self.dbapi.get_action_description_list(
            self.context, filters={'deleted_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.action_desc2['id'], self.action_desc3['id']]),
            set([r.id for r in res]))

    def test_get_action_desc_list_filter_deleted_at_gt(self):
        self._soft_delete_action_descs()

        res = self.dbapi.get_action_description_list(
            self.context, filters={'deleted_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.action_desc1['id']], [r.id for r in res])

    def test_get_action_desc_list_filter_deleted_at_gte(self):
        self._soft_delete_action_descs()

        res = self.dbapi.get_action_description_list(
            self.context, filters={'deleted_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.action_desc1['id'], self.action_desc2['id']]),
            set([r.id for r in res]))

    # created_at #

    def test_get_action_desc_list_filter_created_at_eq(self):
        res = self.dbapi.get_action_description_list(
            self.context, filters={'created_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.action_desc1['id']], [r.id for r in res])

    def test_get_action_desc_list_filter_created_at_lt(self):
        res = self.dbapi.get_action_description_list(
            self.context, filters={'created_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.action_desc2['id'], self.action_desc3['id']]),
            set([r.id for r in res]))

    def test_get_action_desc_list_filter_created_at_lte(self):
        res = self.dbapi.get_action_description_list(
            self.context, filters={'created_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.action_desc2['id'], self.action_desc3['id']]),
            set([r.id for r in res]))

    def test_get_action_desc_list_filter_created_at_gt(self):
        res = self.dbapi.get_action_description_list(
            self.context, filters={'created_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.action_desc1['id']], [r.id for r in res])

    def test_get_action_desc_list_filter_created_at_gte(self):
        res = self.dbapi.get_action_description_list(
            self.context, filters={'created_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.action_desc1['id'], self.action_desc2['id']]),
            set([r.id for r in res]))

    # updated_at #

    def test_get_action_desc_list_filter_updated_at_eq(self):
        self._update_action_descs()

        res = self.dbapi.get_action_description_list(
            self.context, filters={'updated_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.action_desc1['id']], [r.id for r in res])

    def test_get_action_desc_list_filter_updated_at_lt(self):
        self._update_action_descs()

        res = self.dbapi.get_action_description_list(
            self.context, filters={'updated_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.action_desc2['id'], self.action_desc3['id']]),
            set([r.id for r in res]))

    def test_get_action_desc_list_filter_updated_at_lte(self):
        self._update_action_descs()

        res = self.dbapi.get_action_description_list(
            self.context, filters={'updated_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.action_desc2['id'], self.action_desc3['id']]),
            set([r.id for r in res]))

    def test_get_action_desc_list_filter_updated_at_gt(self):
        self._update_action_descs()

        res = self.dbapi.get_action_description_list(
            self.context, filters={'updated_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.action_desc1['id']], [r.id for r in res])

    def test_get_action_desc_list_filter_updated_at_gte(self):
        self._update_action_descs()

        res = self.dbapi.get_action_description_list(
            self.context, filters={'updated_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.action_desc1['id'], self.action_desc2['id']]),
            set([r.id for r in res]))


class DbActionDescriptionTestCase(base.DbTestCase):

    def test_get_action_desc_list(self):
        ids = []
        for i in range(1, 4):
            action_desc = utils.create_test_action_desc(
                id=i,
                action_type="action_%s" % i,
                description="description_{0}".format(i))
            ids.append(action_desc['id'])
        action_descs = self.dbapi.get_action_description_list(self.context)
        action_desc_ids = [s.id for s in action_descs]
        self.assertEqual(sorted(ids), sorted(action_desc_ids))

    def test_get_action_desc_list_with_filters(self):
        action_desc1 = utils.create_test_action_desc(
            id=1,
            action_type="action_1",
            description="description_1",
        )
        action_desc2 = utils.create_test_action_desc(
            id=2,
            action_type="action_2",
            description="description_2",
        )

        res = self.dbapi.get_action_description_list(
            self.context, filters={'action_type': 'action_1'})
        self.assertEqual([action_desc1['id']], [r.id for r in res])

        res = self.dbapi.get_action_description_list(
            self.context, filters={'action_type': 'action_3'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_action_description_list(
            self.context,
            filters={'action_type': 'action_2'})
        self.assertEqual([action_desc2['id']], [r.id for r in res])

    def test_get_action_desc_by_type(self):
        created_action_desc = utils.create_test_action_desc()
        action_desc = self.dbapi.get_action_description_by_type(
            self.context, created_action_desc['action_type'])
        self.assertEqual(action_desc.action_type,
                         created_action_desc['action_type'])

    def test_get_action_desc_that_does_not_exist(self):
        self.assertRaises(exception.ActionDescriptionNotFound,
                          self.dbapi.get_action_description_by_id,
                          self.context, 404)

    def test_update_action_desc(self):
        action_desc = utils.create_test_action_desc()
        res = self.dbapi.update_action_description(
            action_desc['id'], {'description': 'description_test'})
        self.assertEqual('description_test', res.description)
