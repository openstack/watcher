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

"""Tests for manipulating ActionPlan via the DB API"""

import freezegun

from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.objects import action_plan as ap_objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestDbActionPlanFilters(base.DbTestCase):

    FAKE_OLDER_DATE = '2014-01-01T09:52:05.219414'
    FAKE_OLD_DATE = '2015-01-01T09:52:05.219414'
    FAKE_TODAY = '2016-02-24T09:52:05.219414'

    def setUp(self):
        super(TestDbActionPlanFilters, self).setUp()
        self.context.show_deleted = True
        self._data_setup()

    def _data_setup(self):
        self.audit_template_name = "Audit Template"

        self.audit_template = utils.create_test_audit_template(
            name=self.audit_template_name, id=1, uuid=None)
        self.audit = utils.create_test_audit(
            audit_template_id=self.audit_template.id, id=1, uuid=None)

        with freezegun.freeze_time(self.FAKE_TODAY):
            self.action_plan1 = utils.create_test_action_plan(
                audit_id=self.audit.id, id=1, uuid=None)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.action_plan2 = utils.create_test_action_plan(
                audit_id=self.audit.id, id=2, uuid=None)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.action_plan3 = utils.create_test_action_plan(
                audit_id=self.audit.id, id=3, uuid=None)

    def _soft_delete_action_plans(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_action_plan(self.action_plan1.uuid)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.soft_delete_action_plan(self.action_plan2.uuid)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.soft_delete_action_plan(self.action_plan3.uuid)

    def _update_action_plans(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.update_action_plan(
                self.action_plan1.uuid,
                values={"state": ap_objects.State.SUCCEEDED})
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.update_action_plan(
                self.action_plan2.uuid,
                values={"state": ap_objects.State.SUCCEEDED})
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.update_action_plan(
                self.action_plan3.uuid,
                values={"state": ap_objects.State.SUCCEEDED})

    def test_get_action_plan_list_filter_deleted_true(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_action_plan(self.action_plan1.uuid)

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'deleted': True})

        self.assertEqual([self.action_plan1['id']], [r.id for r in res])

    def test_get_action_plan_list_filter_deleted_false(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_action_plan(self.action_plan1.uuid)

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'deleted': False})

        self.assertEqual([self.action_plan2['id'], self.action_plan3['id']],
                         [r.id for r in res])

    def test_get_action_plan_list_filter_deleted_at_eq(self):
        self._soft_delete_action_plans()

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'deleted_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.action_plan1['id']], [r.id for r in res])

    def test_get_action_plan_list_filter_deleted_at_lt(self):
        self._soft_delete_action_plans()

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'deleted_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.action_plan2['id'], self.action_plan3['id']],
            [r.id for r in res])

    def test_get_action_plan_list_filter_deleted_at_lte(self):
        self._soft_delete_action_plans()

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'deleted_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action_plan2['id'], self.action_plan3['id']],
            [r.id for r in res])

    def test_get_action_plan_list_filter_deleted_at_gt(self):
        self._soft_delete_action_plans()

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'deleted_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.action_plan1['id']], [r.id for r in res])

    def test_get_action_plan_list_filter_deleted_at_gte(self):
        self._soft_delete_action_plans()

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'deleted_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action_plan1['id'], self.action_plan2['id']],
            [r.id for r in res])

    # created_at #

    def test_get_action_plan_list_filter_created_at_eq(self):
        res = self.dbapi.get_action_plan_list(
            self.context, filters={'created_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.action_plan1['id']], [r.id for r in res])

    def test_get_action_plan_list_filter_created_at_lt(self):
        res = self.dbapi.get_action_plan_list(
            self.context, filters={'created_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.action_plan2['id'], self.action_plan3['id']],
            [r.id for r in res])

    def test_get_action_plan_list_filter_created_at_lte(self):
        res = self.dbapi.get_action_plan_list(
            self.context, filters={'created_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action_plan2['id'], self.action_plan3['id']],
            [r.id for r in res])

    def test_get_action_plan_list_filter_created_at_gt(self):
        res = self.dbapi.get_action_plan_list(
            self.context, filters={'created_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.action_plan1['id']], [r.id for r in res])

    def test_get_action_plan_list_filter_created_at_gte(self):
        res = self.dbapi.get_action_plan_list(
            self.context, filters={'created_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action_plan1['id'], self.action_plan2['id']],
            [r.id for r in res])

    # updated_at #

    def test_get_action_plan_list_filter_updated_at_eq(self):
        self._update_action_plans()

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'updated_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.action_plan1['id']], [r.id for r in res])

    def test_get_action_plan_list_filter_updated_at_lt(self):
        self._update_action_plans()

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'updated_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.action_plan2['id'], self.action_plan3['id']],
            [r.id for r in res])

    def test_get_action_plan_list_filter_updated_at_lte(self):
        self._update_action_plans()

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'updated_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action_plan2['id'], self.action_plan3['id']],
            [r.id for r in res])

    def test_get_action_plan_list_filter_updated_at_gt(self):
        self._update_action_plans()

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'updated_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.action_plan1['id']], [r.id for r in res])

    def test_get_action_plan_list_filter_updated_at_gte(self):
        self._update_action_plans()

        res = self.dbapi.get_action_plan_list(
            self.context, filters={'updated_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action_plan1['id'], self.action_plan2['id']],
            [r.id for r in res])


class DbActionPlanTestCase(base.DbTestCase):

    def test_get_action_plan_list(self):
        uuids = []
        for _ in range(1, 4):
            action_plan = utils.create_test_action_plan(
                uuid=w_utils.generate_uuid())
            uuids.append(str(action_plan['uuid']))
        action_plans = self.dbapi.get_action_plan_list(self.context)
        action_plan_uuids = [ap.uuid for ap in action_plans]
        self.assertEqual(sorted(uuids), sorted(action_plan_uuids))
        for action_plan in action_plans:
            self.assertIsNone(action_plan.audit)
            self.assertIsNone(action_plan.strategy)

    def test_get_action_plan_list_eager(self):
        _strategy = utils.get_test_strategy()
        strategy = self.dbapi.create_strategy(_strategy)
        _audit = utils.get_test_audit()
        audit = self.dbapi.create_audit(_audit)

        uuids = []
        for _ in range(1, 4):
            action_plan = utils.create_test_action_plan(
                uuid=w_utils.generate_uuid())
            uuids.append(str(action_plan['uuid']))
        action_plans = self.dbapi.get_action_plan_list(
            self.context, eager=True)
        action_plan_map = {a.uuid: a for a in action_plans}
        self.assertEqual(sorted(uuids), sorted(action_plan_map.keys()))
        eager_action_plan = action_plan_map[action_plan.uuid]
        self.assertEqual(
            strategy.as_dict(), eager_action_plan.strategy.as_dict())
        self.assertEqual(audit.as_dict(), eager_action_plan.audit.as_dict())

    def test_get_action_plan_list_with_filters(self):
        audit = utils.create_test_audit(
            id=2,
            audit_type='ONESHOT',
            uuid=w_utils.generate_uuid(),
            state=ap_objects.State.ONGOING)

        action_plan1 = utils.create_test_action_plan(
            id=1,
            uuid=w_utils.generate_uuid(),
            audit_id=audit['id'],
            state=ap_objects.State.RECOMMENDED)
        action_plan2 = utils.create_test_action_plan(
            id=2,
            uuid=w_utils.generate_uuid(),
            audit_id=audit['id'],
            state=ap_objects.State.ONGOING)
        action_plan3 = utils.create_test_action_plan(
            id=3,
            uuid=w_utils.generate_uuid(),
            audit_id=audit['id'],
            state=ap_objects.State.RECOMMENDED)

        # check on bug 1761956
        self.dbapi.soft_delete_action_plan(action_plan3['uuid'])

        res = self.dbapi.get_action_plan_list(
            self.context,
            filters={'state': ap_objects.State.RECOMMENDED})
        self.assertEqual([action_plan1['id']], [r.id for r in res])

        res = self.dbapi.get_action_plan_list(
            self.context,
            filters={'state': ap_objects.State.ONGOING})
        self.assertEqual([action_plan2['id']], [r.id for r in res])

        res = self.dbapi.get_action_plan_list(
            self.context,
            filters={'audit_uuid': audit['uuid']})
        self.assertEqual(
            sorted([action_plan1['id'], action_plan2['id']]),
            sorted([r.id for r in res]))
        for r in res:
            self.assertEqual(audit['id'], r.audit_id)

        self.dbapi.soft_delete_action_plan(action_plan1['uuid'])
        res = self.dbapi.get_action_plan_list(
            self.context,
            filters={'audit_uuid': audit['uuid']})

        self.assertEqual([action_plan2['id']], [r.id for r in res])
        self.assertNotEqual([action_plan1['id']], [r.id for r in res])

    def test_get_action_plan_list_with_filter_by_uuid(self):
        action_plan = utils.create_test_action_plan()
        res = self.dbapi.get_action_plan_list(
            self.context, filters={'uuid': action_plan["uuid"]})

        self.assertEqual(len(res), 1)
        self.assertEqual(action_plan['uuid'], res[0].uuid)

    def test_get_action_plan_by_id(self):
        action_plan = utils.create_test_action_plan()
        action_plan = self.dbapi.get_action_plan_by_id(
            self.context, action_plan['id'])
        self.assertEqual(action_plan['uuid'], action_plan.uuid)

    def test_get_action_plan_by_uuid(self):
        action_plan = utils.create_test_action_plan()
        action_plan = self.dbapi.get_action_plan_by_uuid(
            self.context, action_plan['uuid'])
        self.assertEqual(action_plan['id'], action_plan.id)

    def test_get_action_plan_that_does_not_exist(self):
        self.assertRaises(exception.ActionPlanNotFound,
                          self.dbapi.get_action_plan_by_id, self.context, 1234)

    def test_update_action_plan(self):
        action_plan = utils.create_test_action_plan()
        res = self.dbapi.update_action_plan(
            action_plan['id'], {'name': 'updated-model'})
        self.assertEqual('updated-model', res.name)

    def test_update_action_plan_that_does_not_exist(self):
        self.assertRaises(exception.ActionPlanNotFound,
                          self.dbapi.update_action_plan, 1234, {'name': ''})

    def test_update_action_plan_uuid(self):
        action_plan = utils.create_test_action_plan()
        self.assertRaises(exception.Invalid,
                          self.dbapi.update_action_plan, action_plan['id'],
                          {'uuid': 'hello'})

    def test_destroy_action_plan(self):
        action_plan = utils.create_test_action_plan()
        self.dbapi.destroy_action_plan(action_plan['id'])
        self.assertRaises(exception.ActionPlanNotFound,
                          self.dbapi.get_action_plan_by_id,
                          self.context, action_plan['id'])

    def test_destroy_action_plan_by_uuid(self):
        uuid = w_utils.generate_uuid()
        utils.create_test_action_plan(uuid=uuid)
        self.assertIsNotNone(self.dbapi.get_action_plan_by_uuid(
            self.context, uuid))
        self.dbapi.destroy_action_plan(uuid)
        self.assertRaises(exception.ActionPlanNotFound,
                          self.dbapi.get_action_plan_by_uuid,
                          self.context, uuid)

    def test_destroy_action_plan_that_does_not_exist(self):
        self.assertRaises(exception.ActionPlanNotFound,
                          self.dbapi.destroy_action_plan, 1234)

    def test_destroy_action_plan_that_referenced_by_actions(self):
        action_plan = utils.create_test_action_plan()
        action = utils.create_test_action(action_plan_id=action_plan['id'])
        self.assertEqual(action_plan['id'], action.action_plan_id)
        self.assertRaises(exception.ActionPlanReferenced,
                          self.dbapi.destroy_action_plan, action_plan['id'])

    def test_create_action_plan_already_exists(self):
        uuid = w_utils.generate_uuid()
        utils.create_test_action_plan(id=1, uuid=uuid)
        self.assertRaises(exception.ActionPlanAlreadyExists,
                          utils.create_test_action_plan,
                          id=2, uuid=uuid)
