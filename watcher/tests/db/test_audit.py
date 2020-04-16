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

"""Tests for manipulating Audit via the DB API"""

import freezegun

from watcher.common import exception
from watcher.common import utils as w_utils
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestDbAuditFilters(base.DbTestCase):

    FAKE_OLDER_DATE = '2014-01-01T09:52:05.219414'
    FAKE_OLD_DATE = '2015-01-01T09:52:05.219414'
    FAKE_TODAY = '2016-02-24T09:52:05.219414'

    def setUp(self):
        super(TestDbAuditFilters, self).setUp()
        self.context.show_deleted = True
        self._data_setup()

    def _data_setup(self):
        self.audit_template_name = "Audit Template"

        def gen_name():
            return "Audit %s" % w_utils.generate_uuid()

        self.audit1_name = gen_name()
        self.audit2_name = gen_name()
        self.audit3_name = gen_name()
        self.audit4_name = gen_name()

        self.audit_template = utils.create_test_audit_template(
            name=self.audit_template_name, id=1, uuid=None)

        with freezegun.freeze_time(self.FAKE_TODAY):
            self.audit1 = utils.create_test_audit(
                audit_template_id=self.audit_template.id, id=1, uuid=None,
                name=self.audit1_name)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.audit2 = utils.create_test_audit(
                audit_template_id=self.audit_template.id, id=2, uuid=None,
                name=self.audit2_name, state=objects.audit.State.FAILED)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.audit3 = utils.create_test_audit(
                audit_template_id=self.audit_template.id, id=3, uuid=None,
                name=self.audit3_name, state=objects.audit.State.CANCELLED)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.audit4 = utils.create_test_audit(
                audit_template_id=self.audit_template.id, id=4, uuid=None,
                name=self.audit4_name, state=objects.audit.State.SUSPENDED)

    def _soft_delete_audits(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_audit(self.audit1.uuid)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.soft_delete_audit(self.audit2.uuid)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.soft_delete_audit(self.audit3.uuid)

    def _update_audits(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.update_audit(
                self.audit1.uuid,
                values={"state": objects.audit.State.SUCCEEDED})
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.update_audit(
                self.audit2.uuid,
                values={"state": objects.audit.State.SUCCEEDED})
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.update_audit(
                self.audit3.uuid,
                values={"state": objects.audit.State.SUCCEEDED})

    def test_get_audit_list_filter_deleted_true(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_audit(self.audit1.uuid)

        res = self.dbapi.get_audit_list(
            self.context, filters={'deleted': True})

        self.assertEqual([self.audit1['id']], [r.id for r in res])

    def test_get_audit_list_filter_deleted_false(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_audit(self.audit1.uuid)

        res = self.dbapi.get_audit_list(
            self.context, filters={'deleted': False})

        self.assertEqual(
            [self.audit2['id'], self.audit3['id'], self.audit4['id']],
            [r.id for r in res])

    def test_get_audit_list_filter_deleted_at_eq(self):
        self._soft_delete_audits()

        res = self.dbapi.get_audit_list(
            self.context, filters={'deleted_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.audit1['id']], [r.id for r in res])

    def test_get_audit_list_filter_deleted_at_lt(self):
        self._soft_delete_audits()

        res = self.dbapi.get_audit_list(
            self.context, filters={'deleted_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.audit2['id'], self.audit3['id']],
            [r.id for r in res])

    def test_get_audit_list_filter_deleted_at_lte(self):
        self._soft_delete_audits()

        res = self.dbapi.get_audit_list(
            self.context, filters={'deleted_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit2['id'], self.audit3['id']],
            [r.id for r in res])

    def test_get_audit_list_filter_deleted_at_gt(self):
        self._soft_delete_audits()

        res = self.dbapi.get_audit_list(
            self.context, filters={'deleted_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.audit1['id']], [r.id for r in res])

    def test_get_audit_list_filter_deleted_at_gte(self):
        self._soft_delete_audits()

        res = self.dbapi.get_audit_list(
            self.context, filters={'deleted_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit1['id'], self.audit2['id']],
            [r.id for r in res])

    # created_at #

    def test_get_audit_list_filter_created_at_eq(self):
        res = self.dbapi.get_audit_list(
            self.context, filters={'created_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.audit1['id']], [r.id for r in res])

    def test_get_audit_list_filter_created_at_lt(self):
        res = self.dbapi.get_audit_list(
            self.context, filters={'created_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.audit2['id'], self.audit3['id'], self.audit4['id']],
            [r.id for r in res])

    def test_get_audit_list_filter_created_at_lte(self):
        res = self.dbapi.get_audit_list(
            self.context, filters={'created_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit2['id'], self.audit3['id'], self.audit4['id']],
            [r.id for r in res])

    def test_get_audit_list_filter_created_at_gt(self):
        res = self.dbapi.get_audit_list(
            self.context, filters={'created_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.audit1['id']], [r.id for r in res])

    def test_get_audit_list_filter_created_at_gte(self):
        res = self.dbapi.get_audit_list(
            self.context, filters={'created_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit1['id'], self.audit2['id']],
            [r.id for r in res])

    # updated_at #

    def test_get_audit_list_filter_updated_at_eq(self):
        self._update_audits()

        res = self.dbapi.get_audit_list(
            self.context, filters={'updated_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.audit1['id']], [r.id for r in res])

    def test_get_audit_list_filter_updated_at_lt(self):
        self._update_audits()

        res = self.dbapi.get_audit_list(
            self.context, filters={'updated_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.audit2['id'], self.audit3['id']],
            [r.id for r in res])

    def test_get_audit_list_filter_updated_at_lte(self):
        self._update_audits()

        res = self.dbapi.get_audit_list(
            self.context, filters={'updated_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit2['id'], self.audit3['id']],
            [r.id for r in res])

    def test_get_audit_list_filter_updated_at_gt(self):
        self._update_audits()

        res = self.dbapi.get_audit_list(
            self.context, filters={'updated_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.audit1['id']], [r.id for r in res])

    def test_get_audit_list_filter_updated_at_gte(self):
        self._update_audits()

        res = self.dbapi.get_audit_list(
            self.context, filters={'updated_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.audit1['id'], self.audit2['id']],
            [r.id for r in res])

    def test_get_audit_list_filter_state_in(self):
        res = self.dbapi.get_audit_list(
            self.context,
            filters={
                'state__in':
                    objects.audit.AuditStateTransitionManager.INACTIVE_STATES
            })

        self.assertEqual(
            [self.audit2['id'], self.audit3['id'], self.audit4['id']],
            [r.id for r in res])

    def test_get_audit_list_filter_state_notin(self):
        res = self.dbapi.get_audit_list(
            self.context,
            filters={
                'state__notin':
                    objects.audit.AuditStateTransitionManager.INACTIVE_STATES
            })

        self.assertEqual(
            [self.audit1['id']],
            [r.id for r in res])


class DbAuditTestCase(base.DbTestCase):

    def test_get_audit_list(self):
        uuids = []
        for id_ in range(1, 4):
            audit = utils.create_test_audit(uuid=w_utils.generate_uuid(),
                                            name='My Audit {0}'.format(id_))
            uuids.append(str(audit['uuid']))
        audits = self.dbapi.get_audit_list(self.context)
        audit_uuids = [a.uuid for a in audits]
        self.assertEqual(sorted(uuids), sorted(audit_uuids))
        for audit in audits:
            self.assertIsNone(audit.goal)
            self.assertIsNone(audit.strategy)

    def test_get_audit_list_eager(self):
        _goal = utils.get_test_goal()
        goal = self.dbapi.create_goal(_goal)
        _strategy = utils.get_test_strategy()
        strategy = self.dbapi.create_strategy(_strategy)

        uuids = []
        for i in range(1, 4):
            audit = utils.create_test_audit(
                id=i, uuid=w_utils.generate_uuid(),
                name='My Audit {0}'.format(i),
                goal_id=goal.id, strategy_id=strategy.id)
            uuids.append(str(audit['uuid']))
        audits = self.dbapi.get_audit_list(self.context, eager=True)
        audit_map = {a.uuid: a for a in audits}
        self.assertEqual(sorted(uuids), sorted(audit_map.keys()))
        eager_audit = audit_map[audit.uuid]
        self.assertEqual(goal.as_dict(), eager_audit.goal.as_dict())
        self.assertEqual(strategy.as_dict(), eager_audit.strategy.as_dict())

    def test_get_audit_list_with_filters(self):
        goal = utils.create_test_goal(name='DUMMY')

        audit1 = utils.create_test_audit(
            id=1,
            audit_type=objects.audit.AuditType.ONESHOT.value,
            uuid=w_utils.generate_uuid(),
            name='My Audit {0}'.format(1),
            state=objects.audit.State.ONGOING,
            goal_id=goal['id'])
        audit2 = utils.create_test_audit(
            id=2,
            audit_type=objects.audit.AuditType.CONTINUOUS.value,
            uuid=w_utils.generate_uuid(),
            name='My Audit {0}'.format(2),
            state=objects.audit.State.PENDING,
            goal_id=goal['id'])
        audit3 = utils.create_test_audit(
            id=3,
            audit_type=objects.audit.AuditType.CONTINUOUS.value,
            uuid=w_utils.generate_uuid(),
            name='My Audit {0}'.format(3),
            state=objects.audit.State.ONGOING,
            goal_id=goal['id'])

        self.dbapi.soft_delete_audit(audit3['uuid'])

        res = self.dbapi.get_audit_list(
            self.context,
            filters={'audit_type': objects.audit.AuditType.ONESHOT.value})
        self.assertEqual([audit1['id']], [r.id for r in res])

        res = self.dbapi.get_audit_list(
            self.context,
            filters={'audit_type': 'bad-type'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_audit_list(
            self.context,
            filters={'state': objects.audit.State.ONGOING})
        self.assertEqual([audit1['id']], [r.id for r in res])

        res = self.dbapi.get_audit_list(
            self.context,
            filters={'state': objects.audit.State.PENDING})
        self.assertEqual([audit2['id']], [r.id for r in res])

        res = self.dbapi.get_audit_list(
            self.context,
            filters={'goal_name': 'DUMMY'})
        self.assertEqual(sorted([audit1['id'], audit2['id']]),
                         sorted([r.id for r in res]))

        temp_context = self.context
        temp_context.show_deleted = True
        res = self.dbapi.get_audit_list(
            temp_context,
            filters={'goal_name': 'DUMMY'})
        self.assertEqual(sorted([audit1['id'], audit2['id'], audit3['id']]),
                         sorted([r.id for r in res]))

    def test_get_audit_list_with_filter_by_uuid(self):
        audit = utils.create_test_audit()
        res = self.dbapi.get_audit_list(
            self.context, filters={'uuid': audit["uuid"]})

        self.assertEqual(len(res), 1)
        self.assertEqual(audit['uuid'], res[0].uuid)

    def test_get_audit_by_id(self):
        audit = utils.create_test_audit()
        audit = self.dbapi.get_audit_by_id(self.context, audit['id'])
        self.assertEqual(audit['uuid'], audit.uuid)

    def test_get_audit_by_uuid(self):
        audit = utils.create_test_audit()
        audit = self.dbapi.get_audit_by_uuid(self.context, audit['uuid'])
        self.assertEqual(audit['id'], audit.id)

    def test_get_audit_that_does_not_exist(self):
        self.assertRaises(exception.AuditNotFound,
                          self.dbapi.get_audit_by_id, self.context, 1234)

    def test_update_audit(self):
        audit = utils.create_test_audit()
        res = self.dbapi.update_audit(audit['id'], {'name': 'updated-model'})
        self.assertEqual('updated-model', res.name)

    def test_update_audit_that_does_not_exist(self):
        self.assertRaises(exception.AuditNotFound,
                          self.dbapi.update_audit, 1234, {'name': ''})

    def test_update_audit_uuid(self):
        audit = utils.create_test_audit()
        self.assertRaises(exception.Invalid,
                          self.dbapi.update_audit, audit['id'],
                          {'uuid': 'hello'})

    def test_destroy_audit(self):
        audit = utils.create_test_audit()
        self.dbapi.destroy_audit(audit['id'])
        self.assertRaises(exception.AuditNotFound,
                          self.dbapi.get_audit_by_id,
                          self.context, audit['id'])

    def test_destroy_audit_by_uuid(self):
        audit = utils.create_test_audit()
        self.assertIsNotNone(self.dbapi.get_audit_by_uuid(self.context,
                                                          audit['uuid']))
        self.dbapi.destroy_audit(audit['uuid'])
        self.assertRaises(exception.AuditNotFound,
                          self.dbapi.get_audit_by_uuid, self.context,
                          audit['uuid'])

    def test_destroy_audit_that_does_not_exist(self):
        self.assertRaises(exception.AuditNotFound,
                          self.dbapi.destroy_audit, 1234)

    def test_destroy_audit_that_referenced_by_action_plans(self):
        audit = utils.create_test_audit()
        action_plan = utils.create_test_action_plan(audit_id=audit['id'])
        self.assertEqual(audit['id'], action_plan.audit_id)
        self.assertRaises(exception.AuditReferenced,
                          self.dbapi.destroy_audit, audit['id'])

    def test_create_audit_already_exists(self):
        uuid = w_utils.generate_uuid()
        utils.create_test_audit(id=1, uuid=uuid)
        self.assertRaises(exception.AuditAlreadyExists,
                          utils.create_test_audit,
                          id=2, uuid=uuid)

    def test_create_same_name_audit(self):
        audit = utils.create_test_audit(
            uuid=w_utils.generate_uuid(),
            name='my_audit')
        self.assertEqual(audit['uuid'], audit.uuid)
        self.assertRaises(
            exception.AuditAlreadyExists,
            utils.create_test_audit,
            uuid=w_utils.generate_uuid(),
            name='my_audit')
