# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Servionica
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


"""Tests for manipulating Service via the DB API"""

import freezegun

from oslo_utils import timeutils

from watcher.common import exception
from watcher.tests.db import base
from watcher.tests.db import utils


class TestDbServiceFilters(base.DbTestCase):

    FAKE_OLDER_DATE = '2014-01-01T09:52:05.219414'
    FAKE_OLD_DATE = '2015-01-01T09:52:05.219414'
    FAKE_TODAY = '2016-02-24T09:52:05.219414'

    def setUp(self):
        super(TestDbServiceFilters, self).setUp()
        self.context.show_deleted = True
        self._data_setup()

    def _data_setup(self):
        service1_name = "SERVICE_ID_1"
        service2_name = "SERVICE_ID_2"
        service3_name = "SERVICE_ID_3"

        with freezegun.freeze_time(self.FAKE_TODAY):
            self.service1 = utils.create_test_service(
                id=1, name=service1_name, host="controller",
                last_seen_up=timeutils.parse_isotime("2016-09-22T08:32:05"))
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.service2 = utils.create_test_service(
                id=2, name=service2_name, host="controller",
                last_seen_up=timeutils.parse_isotime("2016-09-22T08:32:05"))
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.service3 = utils.create_test_service(
                id=3, name=service3_name, host="controller",
                last_seen_up=timeutils.parse_isotime("2016-09-22T08:32:05"))

    def _soft_delete_services(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_service(self.service1.id)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.soft_delete_service(self.service2.id)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.soft_delete_service(self.service3.id)

    def _update_services(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.update_service(
                self.service1.id, values={"host": "controller1"})
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.update_service(
                self.service2.id, values={"host": "controller2"})
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.update_service(
                self.service3.id, values={"host": "controller3"})

    def test_get_service_list_filter_deleted_true(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_service(self.service1.id)

        res = self.dbapi.get_service_list(
            self.context, filters={'deleted': True})

        self.assertEqual([self.service1['name']], [r.name for r in res])

    def test_get_service_list_filter_deleted_false(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_service(self.service1.id)

        res = self.dbapi.get_service_list(
            self.context, filters={'deleted': False})

        self.assertEqual(
            set([self.service2['name'], self.service3['name']]),
            set([r.name for r in res]))

    def test_get_service_list_filter_deleted_at_eq(self):
        self._soft_delete_services()

        res = self.dbapi.get_service_list(
            self.context, filters={'deleted_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.service1['id']], [r.id for r in res])

    def test_get_service_list_filter_deleted_at_lt(self):
        self._soft_delete_services()

        res = self.dbapi.get_service_list(
            self.context, filters={'deleted_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.service2['id'], self.service3['id']]),
            set([r.id for r in res]))

    def test_get_service_list_filter_deleted_at_lte(self):
        self._soft_delete_services()

        res = self.dbapi.get_service_list(
            self.context, filters={'deleted_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.service2['id'], self.service3['id']]),
            set([r.id for r in res]))

    def test_get_service_list_filter_deleted_at_gt(self):
        self._soft_delete_services()

        res = self.dbapi.get_service_list(
            self.context, filters={'deleted_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.service1['id']], [r.id for r in res])

    def test_get_service_list_filter_deleted_at_gte(self):
        self._soft_delete_services()

        res = self.dbapi.get_service_list(
            self.context, filters={'deleted_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.service1['id'], self.service2['id']]),
            set([r.id for r in res]))

    # created_at #

    def test_get_service_list_filter_created_at_eq(self):
        res = self.dbapi.get_service_list(
            self.context, filters={'created_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.service1['id']], [r.id for r in res])

    def test_get_service_list_filter_created_at_lt(self):
        res = self.dbapi.get_service_list(
            self.context, filters={'created_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.service2['id'], self.service3['id']]),
            set([r.id for r in res]))

    def test_get_service_list_filter_created_at_lte(self):
        res = self.dbapi.get_service_list(
            self.context, filters={'created_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.service2['id'], self.service3['id']]),
            set([r.id for r in res]))

    def test_get_service_list_filter_created_at_gt(self):
        res = self.dbapi.get_service_list(
            self.context, filters={'created_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.service1['id']], [r.id for r in res])

    def test_get_service_list_filter_created_at_gte(self):
        res = self.dbapi.get_service_list(
            self.context, filters={'created_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.service1['id'], self.service2['id']]),
            set([r.id for r in res]))

    # updated_at #

    def test_get_service_list_filter_updated_at_eq(self):
        self._update_services()

        res = self.dbapi.get_service_list(
            self.context, filters={'updated_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.service1['id']], [r.id for r in res])

    def test_get_service_list_filter_updated_at_lt(self):
        self._update_services()

        res = self.dbapi.get_service_list(
            self.context, filters={'updated_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            set([self.service2['id'], self.service3['id']]),
            set([r.id for r in res]))

    def test_get_service_list_filter_updated_at_lte(self):
        self._update_services()

        res = self.dbapi.get_service_list(
            self.context, filters={'updated_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.service2['id'], self.service3['id']]),
            set([r.id for r in res]))

    def test_get_service_list_filter_updated_at_gt(self):
        self._update_services()

        res = self.dbapi.get_service_list(
            self.context, filters={'updated_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.service1['id']], [r.id for r in res])

    def test_get_service_list_filter_updated_at_gte(self):
        self._update_services()

        res = self.dbapi.get_service_list(
            self.context, filters={'updated_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            set([self.service1['id'], self.service2['id']]),
            set([r.id for r in res]))


class DbServiceTestCase(base.DbTestCase):

    def test_get_service_list(self):
        ids = []
        for i in range(1, 4):
            service = utils.create_test_service(
                id=i,
                name="SERVICE_ID_%s" % i,
                host="controller_{0}".format(i))
            ids.append(service['id'])
        services = self.dbapi.get_service_list(self.context)
        service_ids = [s.id for s in services]
        self.assertEqual(sorted(ids), sorted(service_ids))

    def test_get_service_list_with_filters(self):
        service1 = utils.create_test_service(
            id=1,
            name="SERVICE_ID_1",
            host="controller_1",
        )
        service2 = utils.create_test_service(
            id=2,
            name="SERVICE_ID_2",
            host="controller_2",
        )
        service3 = utils.create_test_service(
            id=3,
            name="SERVICE_ID_3",
            host="controller_3",
        )

        self.dbapi.soft_delete_service(service3['id'])

        res = self.dbapi.get_service_list(
            self.context, filters={'host': 'controller_1'})
        self.assertEqual([service1['id']], [r.id for r in res])

        res = self.dbapi.get_service_list(
            self.context, filters={'host': 'controller_3'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_service_list(
            self.context, filters={'host': 'controller_2'})
        self.assertEqual([service2['id']], [r.id for r in res])

    def test_get_service_by_name(self):
        created_service = utils.create_test_service()
        service = self.dbapi.get_service_by_name(
            self.context, created_service['name'])
        self.assertEqual(service.name, created_service['name'])

    def test_get_service_that_does_not_exist(self):
        self.assertRaises(exception.ServiceNotFound,
                          self.dbapi.get_service_by_id,
                          self.context, 404)

    def test_update_service(self):
        service = utils.create_test_service()
        res = self.dbapi.update_service(
            service['id'], {'host': 'controller_test'})
        self.assertEqual('controller_test', res.host)

    def test_update_service_that_does_not_exist(self):
        self.assertRaises(exception.ServiceNotFound,
                          self.dbapi.update_service,
                          405,
                          {'name': ''})

    def test_create_service_already_exists(self):
        service_id = "STRATEGY_ID"
        utils.create_test_service(name=service_id)
        self.assertRaises(exception.ServiceAlreadyExists,
                          utils.create_test_service,
                          name=service_id)
