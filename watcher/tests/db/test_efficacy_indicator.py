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

"""Tests for manipulating EfficacyIndicator via the DB API"""

import freezegun

from watcher.common import exception
from watcher.common import utils as w_utils
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestDbEfficacyIndicatorFilters(base.DbTestCase):

    FAKE_OLDER_DATE = '2014-01-01T09:52:05.219414'
    FAKE_OLD_DATE = '2015-01-01T09:52:05.219414'
    FAKE_TODAY = '2016-02-24T09:52:05.219414'

    def setUp(self):
        super(TestDbEfficacyIndicatorFilters, self).setUp()
        self.context.show_deleted = True
        self._data_setup()

    def _data_setup(self):
        self.audit_template_name = "Audit Template"

        self.audit_template = utils.create_test_audit_template(
            name=self.audit_template_name, id=1, uuid=None)
        self.audit = utils.create_test_audit(
            audit_template_id=self.audit_template.id, id=1, uuid=None)
        self.action_plan = utils.create_test_action_plan(
            audit_id=self.audit.id, id=1, uuid=None)

        with freezegun.freeze_time(self.FAKE_TODAY):
            self.efficacy_indicator1 = utils.create_test_efficacy_indicator(
                action_plan_id=self.action_plan.id, id=1, uuid=None,
                name="efficacy_indicator1", description="Test Indicator 1")
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.efficacy_indicator2 = utils.create_test_efficacy_indicator(
                action_plan_id=self.action_plan.id, id=2, uuid=None,
                name="efficacy_indicator2", description="Test Indicator 2")
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.efficacy_indicator3 = utils.create_test_efficacy_indicator(
                action_plan_id=self.action_plan.id, id=3, uuid=None,
                name="efficacy_indicator3", description="Test Indicator 3")

    def _soft_delete_efficacy_indicators(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_efficacy_indicator(
                self.efficacy_indicator1.uuid)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.soft_delete_efficacy_indicator(
                self.efficacy_indicator2.uuid)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.soft_delete_efficacy_indicator(
                self.efficacy_indicator3.uuid)

    def _update_efficacy_indicators(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.update_efficacy_indicator(
                self.efficacy_indicator1.uuid,
                values={"description": "New description 1"})
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.update_efficacy_indicator(
                self.efficacy_indicator2.uuid,
                values={"description": "New description 2"})
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.update_efficacy_indicator(
                self.efficacy_indicator3.uuid,
                values={"description": "New description 3"})

    def test_get_efficacy_indicator_filter_deleted_true(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_efficacy_indicator(
                self.efficacy_indicator1.uuid)

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'deleted': True})

        self.assertEqual([self.efficacy_indicator1['id']], [r.id for r in res])

    def test_get_efficacy_indicator_filter_deleted_false(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_efficacy_indicator(
                self.efficacy_indicator1.uuid)

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'deleted': False})

        self.assertEqual([self.efficacy_indicator2['id'],
                          self.efficacy_indicator3['id']],
                         [r.id for r in res])

    def test_get_efficacy_indicator_filter_deleted_at_eq(self):
        self._soft_delete_efficacy_indicators()

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'deleted_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.efficacy_indicator1['id']], [r.id for r in res])

    def test_get_efficacy_indicator_filter_deleted_at_lt(self):
        self._soft_delete_efficacy_indicators()

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'deleted_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.efficacy_indicator2['id'], self.efficacy_indicator3['id']],
            [r.id for r in res])

    def test_get_efficacy_indicator_filter_deleted_at_lte(self):
        self._soft_delete_efficacy_indicators()

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'deleted_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.efficacy_indicator2['id'], self.efficacy_indicator3['id']],
            [r.id for r in res])

    def test_get_efficacy_indicator_filter_deleted_at_gt(self):
        self._soft_delete_efficacy_indicators()

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'deleted_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.efficacy_indicator1['id']], [r.id for r in res])

    def test_get_efficacy_indicator_filter_deleted_at_gte(self):
        self._soft_delete_efficacy_indicators()

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'deleted_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.efficacy_indicator1['id'], self.efficacy_indicator2['id']],
            [r.id for r in res])

    # created_at #

    def test_get_efficacy_indicator_filter_created_at_eq(self):
        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'created_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.efficacy_indicator1['id']], [r.id for r in res])

    def test_get_efficacy_indicator_filter_created_at_lt(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            res = self.dbapi.get_efficacy_indicator_list(
                self.context, filters={'created_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.efficacy_indicator2['id'], self.efficacy_indicator3['id']],
            [r.id for r in res])

    def test_get_efficacy_indicator_filter_created_at_lte(self):
        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'created_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.efficacy_indicator2['id'], self.efficacy_indicator3['id']],
            [r.id for r in res])

    def test_get_efficacy_indicator_filter_created_at_gt(self):
        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'created_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.efficacy_indicator1['id']], [r.id for r in res])

    def test_get_efficacy_indicator_filter_created_at_gte(self):
        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'created_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.efficacy_indicator1['id'], self.efficacy_indicator2['id']],
            [r.id for r in res])

    # updated_at #

    def test_get_efficacy_indicator_filter_updated_at_eq(self):
        self._update_efficacy_indicators()

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'updated_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.efficacy_indicator1['id']], [r.id for r in res])

    def test_get_efficacy_indicator_filter_updated_at_lt(self):
        self._update_efficacy_indicators()

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'updated_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.efficacy_indicator2['id'], self.efficacy_indicator3['id']],
            [r.id for r in res])

    def test_get_efficacy_indicator_filter_updated_at_lte(self):
        self._update_efficacy_indicators()

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'updated_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.efficacy_indicator2['id'], self.efficacy_indicator3['id']],
            [r.id for r in res])

    def test_get_efficacy_indicator_filter_updated_at_gt(self):
        self._update_efficacy_indicators()

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'updated_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.efficacy_indicator1['id']], [r.id for r in res])

    def test_get_efficacy_indicator_filter_updated_at_gte(self):
        self._update_efficacy_indicators()

        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'updated_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.efficacy_indicator1['id'], self.efficacy_indicator2['id']],
            [r.id for r in res])


class DbEfficacyIndicatorTestCase(base.DbTestCase):

    def test_get_efficacy_indicator_list(self):
        uuids = []
        action_plan = utils.create_test_action_plan()
        for id_ in range(1, 4):
            efficacy_indicator = utils.create_test_efficacy_indicator(
                action_plan_id=action_plan.id, id=id_, uuid=None,
                name="efficacy_indicator", description="Test Indicator ")
            uuids.append(str(efficacy_indicator['uuid']))
        efficacy_indicators = self.dbapi.get_efficacy_indicator_list(
            self.context)
        efficacy_indicator_uuids = [ei.uuid for ei in efficacy_indicators]
        self.assertEqual(sorted(uuids), sorted(efficacy_indicator_uuids))
        for efficacy_indicator in efficacy_indicators:
            self.assertIsNone(efficacy_indicator.action_plan)

    def test_get_efficacy_indicator_list_eager(self):
        _action_plan = utils.get_test_action_plan()
        action_plan = self.dbapi.create_action_plan(_action_plan)

        uuids = []
        for i in range(1, 4):
            efficacy_indicator = utils.create_test_efficacy_indicator(
                id=i, uuid=w_utils.generate_uuid(),
                action_plan_id=action_plan.id)
            uuids.append(str(efficacy_indicator['uuid']))
        efficacy_indicators = self.dbapi.get_efficacy_indicator_list(
            self.context, eager=True)
        efficacy_indicator_map = {a.uuid: a for a in efficacy_indicators}
        self.assertEqual(sorted(uuids), sorted(efficacy_indicator_map.keys()))
        eager_efficacy_indicator = efficacy_indicator_map[
            efficacy_indicator.uuid]
        self.assertEqual(
            action_plan.as_dict(),
            eager_efficacy_indicator.action_plan.as_dict())

    def test_get_efficacy_indicator_list_with_filters(self):
        audit = utils.create_test_audit(uuid=w_utils.generate_uuid())
        action_plan = utils.create_test_action_plan(
            id=1,
            uuid=w_utils.generate_uuid(),
            audit_id=audit.id,
            first_efficacy_indicator_id=None,
            state=objects.action_plan.State.RECOMMENDED)

        efficacy_indicator1 = utils.create_test_efficacy_indicator(
            id=1,
            name='indicator_1',
            uuid=w_utils.generate_uuid(),
            action_plan_id=action_plan['id'],
            description='Description efficacy indicator 1',
            unit='%')
        efficacy_indicator2 = utils.create_test_efficacy_indicator(
            id=2,
            name='indicator_2',
            uuid=w_utils.generate_uuid(),
            action_plan_id=2,
            description='Description efficacy indicator 2',
            unit='%')
        efficacy_indicator3 = utils.create_test_efficacy_indicator(
            id=3,
            name='indicator_3',
            uuid=w_utils.generate_uuid(),
            action_plan_id=action_plan['id'],
            description='Description efficacy indicator 3',
            unit='%')
        efficacy_indicator4 = utils.create_test_efficacy_indicator(
            id=4,
            name='indicator_4',
            uuid=w_utils.generate_uuid(),
            action_plan_id=action_plan['id'],
            description='Description efficacy indicator 4',
            unit='%')

        self.dbapi.soft_delete_efficacy_indicator(efficacy_indicator4['uuid'])

        res = self.dbapi.get_efficacy_indicator_list(
            self.context,
            filters={'name': 'indicator_3'})
        self.assertEqual([efficacy_indicator3['id']], [r.id for r in res])

        res = self.dbapi.get_efficacy_indicator_list(
            self.context,
            filters={'unit': 'kWh'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_efficacy_indicator_list(
            self.context,
            filters={'action_plan_id': 2})
        self.assertEqual([efficacy_indicator2['id']], [r.id for r in res])

        res = self.dbapi.get_efficacy_indicator_list(
            self.context,
            filters={'action_plan_uuid': action_plan['uuid']})
        self.assertEqual(
            sorted([efficacy_indicator1['id'], efficacy_indicator3['id']]),
            sorted([r.id for r in res]))

    def test_get_efficacy_indicator_list_with_filter_by_uuid(self):
        efficacy_indicator = utils.create_test_efficacy_indicator()
        res = self.dbapi.get_efficacy_indicator_list(
            self.context, filters={'uuid': efficacy_indicator.uuid})

        self.assertEqual(len(res), 1)
        self.assertEqual(efficacy_indicator.uuid, res[0].uuid)

    def test_get_efficacy_indicator_by_id(self):
        efficacy_indicator = utils.create_test_efficacy_indicator()
        efficacy_indicator = self.dbapi.get_efficacy_indicator_by_id(
            self.context, efficacy_indicator.id)
        self.assertEqual(efficacy_indicator.uuid, efficacy_indicator.uuid)

    def test_get_efficacy_indicator_by_uuid(self):
        efficacy_indicator = utils.create_test_efficacy_indicator()
        efficacy_indicator = self.dbapi.get_efficacy_indicator_by_uuid(
            self.context, efficacy_indicator.uuid)
        self.assertEqual(efficacy_indicator['id'], efficacy_indicator.id)

    def test_get_efficacy_indicator_that_does_not_exist(self):
        self.assertRaises(
            exception.EfficacyIndicatorNotFound,
            self.dbapi.get_efficacy_indicator_by_id, self.context, 1234)

    def test_update_efficacy_indicator(self):
        efficacy_indicator = utils.create_test_efficacy_indicator()
        res = self.dbapi.update_efficacy_indicator(
            efficacy_indicator.id,
            {'state': objects.action_plan.State.CANCELLED})
        self.assertEqual('CANCELLED', res.state)

    def test_update_efficacy_indicator_that_does_not_exist(self):
        self.assertRaises(
            exception.EfficacyIndicatorNotFound,
            self.dbapi.update_efficacy_indicator, 1234, {'state': ''})

    def test_update_efficacy_indicator_uuid(self):
        efficacy_indicator = utils.create_test_efficacy_indicator()
        self.assertRaises(
            exception.Invalid,
            self.dbapi.update_efficacy_indicator, efficacy_indicator.id,
            {'uuid': 'hello'})

    def test_destroy_efficacy_indicator(self):
        efficacy_indicator = utils.create_test_efficacy_indicator()
        self.dbapi.destroy_efficacy_indicator(efficacy_indicator['id'])
        self.assertRaises(exception.EfficacyIndicatorNotFound,
                          self.dbapi.get_efficacy_indicator_by_id,
                          self.context, efficacy_indicator['id'])

    def test_destroy_efficacy_indicator_by_uuid(self):
        uuid = w_utils.generate_uuid()
        utils.create_test_efficacy_indicator(uuid=uuid)
        self.assertIsNotNone(self.dbapi.get_efficacy_indicator_by_uuid(
            self.context, uuid))
        self.dbapi.destroy_efficacy_indicator(uuid)
        self.assertRaises(
            exception.EfficacyIndicatorNotFound,
            self.dbapi.get_efficacy_indicator_by_uuid, self.context, uuid)

    def test_destroy_efficacy_indicator_that_does_not_exist(self):
        self.assertRaises(exception.EfficacyIndicatorNotFound,
                          self.dbapi.destroy_efficacy_indicator, 1234)

    def test_create_efficacy_indicator_already_exists(self):
        uuid = w_utils.generate_uuid()
        utils.create_test_efficacy_indicator(id=1, uuid=uuid)
        self.assertRaises(exception.EfficacyIndicatorAlreadyExists,
                          utils.create_test_efficacy_indicator,
                          id=2, uuid=uuid)
