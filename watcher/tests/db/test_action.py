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

"""Tests for manipulating Action via the DB API"""

import freezegun
import six

from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.objects import action as act_objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestDbActionFilters(base.DbTestCase):

    FAKE_OLDER_DATE = '2014-01-01T09:52:05.219414'
    FAKE_OLD_DATE = '2015-01-01T09:52:05.219414'
    FAKE_TODAY = '2016-02-24T09:52:05.219414'

    def setUp(self):
        super(TestDbActionFilters, self).setUp()
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
            self.action1 = utils.create_test_action(
                action_plan_id=self.action_plan.id, id=1, uuid=None)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.action2 = utils.create_test_action(
                action_plan_id=self.action_plan.id, id=2, uuid=None)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.action3 = utils.create_test_action(
                action_plan_id=self.action_plan.id, id=3, uuid=None)

    def _soft_delete_actions(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_action(self.action1.uuid)
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.soft_delete_action(self.action2.uuid)
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.soft_delete_action(self.action3.uuid)

    def _update_actions(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.update_action(
                self.action1.uuid,
                values={"state": act_objects.State.SUCCEEDED})
        with freezegun.freeze_time(self.FAKE_OLD_DATE):
            self.dbapi.update_action(
                self.action2.uuid,
                values={"state": act_objects.State.SUCCEEDED})
        with freezegun.freeze_time(self.FAKE_OLDER_DATE):
            self.dbapi.update_action(
                self.action3.uuid,
                values={"state": act_objects.State.SUCCEEDED})

    def test_get_action_filter_deleted_true(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_action(self.action1.uuid)

        res = self.dbapi.get_action_list(
            self.context, filters={'deleted': True})

        self.assertEqual([self.action1['id']], [r.id for r in res])

    def test_get_action_filter_deleted_false(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            self.dbapi.soft_delete_action(self.action1.uuid)

        res = self.dbapi.get_action_list(
            self.context, filters={'deleted': False})

        self.assertEqual([self.action2['id'], self.action3['id']],
                         [r.id for r in res])

    def test_get_action_filter_deleted_at_eq(self):
        self._soft_delete_actions()

        res = self.dbapi.get_action_list(
            self.context, filters={'deleted_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.action1['id']], [r.id for r in res])

    def test_get_action_filter_deleted_at_lt(self):
        self._soft_delete_actions()

        res = self.dbapi.get_action_list(
            self.context, filters={'deleted_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.action2['id'], self.action3['id']],
            [r.id for r in res])

    def test_get_action_filter_deleted_at_lte(self):
        self._soft_delete_actions()

        res = self.dbapi.get_action_list(
            self.context, filters={'deleted_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action2['id'], self.action3['id']],
            [r.id for r in res])

    def test_get_action_filter_deleted_at_gt(self):
        self._soft_delete_actions()

        res = self.dbapi.get_action_list(
            self.context, filters={'deleted_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.action1['id']], [r.id for r in res])

    def test_get_action_filter_deleted_at_gte(self):
        self._soft_delete_actions()

        res = self.dbapi.get_action_list(
            self.context, filters={'deleted_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action1['id'], self.action2['id']],
            [r.id for r in res])

    # created_at #

    def test_get_action_filter_created_at_eq(self):
        res = self.dbapi.get_action_list(
            self.context, filters={'created_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.action1['id']], [r.id for r in res])

    def test_get_action_filter_created_at_lt(self):
        with freezegun.freeze_time(self.FAKE_TODAY):
            res = self.dbapi.get_action_list(
                self.context, filters={'created_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.action2['id'], self.action3['id']],
            [r.id for r in res])

    def test_get_action_filter_created_at_lte(self):
        res = self.dbapi.get_action_list(
            self.context, filters={'created_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action2['id'], self.action3['id']],
            [r.id for r in res])

    def test_get_action_filter_created_at_gt(self):
        res = self.dbapi.get_action_list(
            self.context, filters={'created_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.action1['id']], [r.id for r in res])

    def test_get_action_filter_created_at_gte(self):
        res = self.dbapi.get_action_list(
            self.context, filters={'created_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action1['id'], self.action2['id']],
            [r.id for r in res])

    # updated_at #

    def test_get_action_filter_updated_at_eq(self):
        self._update_actions()

        res = self.dbapi.get_action_list(
            self.context, filters={'updated_at__eq': self.FAKE_TODAY})

        self.assertEqual([self.action1['id']], [r.id for r in res])

    def test_get_action_filter_updated_at_lt(self):
        self._update_actions()

        res = self.dbapi.get_action_list(
            self.context, filters={'updated_at__lt': self.FAKE_TODAY})

        self.assertEqual(
            [self.action2['id'], self.action3['id']],
            [r.id for r in res])

    def test_get_action_filter_updated_at_lte(self):
        self._update_actions()

        res = self.dbapi.get_action_list(
            self.context, filters={'updated_at__lte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action2['id'], self.action3['id']],
            [r.id for r in res])

    def test_get_action_filter_updated_at_gt(self):
        self._update_actions()

        res = self.dbapi.get_action_list(
            self.context, filters={'updated_at__gt': self.FAKE_OLD_DATE})

        self.assertEqual([self.action1['id']], [r.id for r in res])

    def test_get_action_filter_updated_at_gte(self):
        self._update_actions()

        res = self.dbapi.get_action_list(
            self.context, filters={'updated_at__gte': self.FAKE_OLD_DATE})

        self.assertEqual(
            [self.action1['id'], self.action2['id']],
            [r.id for r in res])


class DbActionTestCase(base.DbTestCase):

    def _create_test_action(self, **kwargs):
        action = utils.get_test_action(**kwargs)
        self.dbapi.create_action(action)
        return action

    def _create_test_action_plan(self, **kwargs):
        action_plan = utils.get_test_action_plan(**kwargs)
        self.dbapi.create_action_plan(action_plan)
        return action_plan

    def test_get_action_list(self):
        uuids = []
        for _ in range(1, 6):
            action = utils.create_test_action(uuid=w_utils.generate_uuid())
            uuids.append(six.text_type(action['uuid']))
        res = self.dbapi.get_action_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(uuids.sort(), res_uuids.sort())

    def test_get_action_list_with_filters(self):
        audit = utils.create_test_audit(uuid=w_utils.generate_uuid())
        action_plan = self._create_test_action_plan(
            id=1,
            uuid=w_utils.generate_uuid(),
            audit_id=audit.id,
            first_action_id=None,
            state='RECOMMENDED')
        action1 = self._create_test_action(
            id=1,
            action_plan_id=1,
            description='description action 1',
            uuid=w_utils.generate_uuid(),
            next=None,
            state='PENDING')
        action2 = self._create_test_action(
            id=2,
            action_plan_id=2,
            description='description action 2',
            uuid=w_utils.generate_uuid(),
            next=action1['uuid'],
            state='PENDING')
        action3 = self._create_test_action(
            id=3,
            action_plan_id=1,
            description='description action 3',
            uuid=w_utils.generate_uuid(),
            next=action2['uuid'],
            state='ONGOING')
        res = self.dbapi.get_action_list(self.context,
                                         filters={'state': 'ONGOING'})
        self.assertEqual([action3['id']], [r.id for r in res])

        res = self.dbapi.get_action_list(self.context,
                                         filters={'state': 'bad-state'})
        self.assertEqual([], [r.id for r in res])

        res = self.dbapi.get_action_list(
            self.context,
            filters={'action_plan_id': 2})
        self.assertEqual([action2['id']], [r.id for r in res])

        res = self.dbapi.get_action_list(
            self.context,
            filters={'action_plan_uuid': action_plan['uuid']})
        self.assertEqual(
            [action1['id'], action3['id']].sort(),
            [r.id for r in res].sort())

        res = self.dbapi.get_action_list(
            self.context,
            filters={'audit_uuid': audit.uuid})
        for action in res:
            self.assertEqual(action_plan['id'], action.action_plan_id)

    def test_get_action_list_with_filter_by_uuid(self):
        action = self._create_test_action()
        res = self.dbapi.get_action_list(
            self.context, filters={'uuid': action["uuid"]})

        self.assertEqual(len(res), 1)
        self.assertEqual(action['uuid'], res[0].uuid)

    def test_get_action_by_id(self):
        action = self._create_test_action()
        action = self.dbapi.get_action_by_id(self.context, action['id'])
        self.assertEqual(action['uuid'], action.uuid)

    def test_get_action_by_uuid(self):
        action = self._create_test_action()
        action = self.dbapi.get_action_by_uuid(self.context, action['uuid'])
        self.assertEqual(action['id'], action.id)

    def test_get_action_that_does_not_exist(self):
        self.assertRaises(exception.ActionNotFound,
                          self.dbapi.get_action_by_id, self.context, 1234)

    def test_update_action(self):
        action = self._create_test_action()
        res = self.dbapi.update_action(action['id'], {'state': 'CANCELLED'})
        self.assertEqual('CANCELLED', res.state)

    def test_update_action_that_does_not_exist(self):
        self.assertRaises(exception.ActionNotFound,
                          self.dbapi.update_action, 1234, {'state': ''})

    def test_update_action_uuid(self):
        action = self._create_test_action()
        self.assertRaises(exception.Invalid,
                          self.dbapi.update_action, action['id'],
                          {'uuid': 'hello'})

    def test_destroy_action(self):
        action = self._create_test_action()
        self.dbapi.destroy_action(action['id'])
        self.assertRaises(exception.ActionNotFound,
                          self.dbapi.get_action_by_id,
                          self.context, action['id'])

    def test_destroy_action_by_uuid(self):
        uuid = w_utils.generate_uuid()
        self._create_test_action(uuid=uuid)
        self.assertIsNotNone(self.dbapi.get_action_by_uuid(self.context,
                                                           uuid))
        self.dbapi.destroy_action(uuid)
        self.assertRaises(exception.ActionNotFound,
                          self.dbapi.get_action_by_uuid, self.context, uuid)

    def test_destroy_action_that_does_not_exist(self):
        self.assertRaises(exception.ActionNotFound,
                          self.dbapi.destroy_action, 1234)

    def test_create_action_already_exists(self):
        uuid = w_utils.generate_uuid()
        self._create_test_action(id=1, uuid=uuid)
        self.assertRaises(exception.ActionAlreadyExists,
                          self._create_test_action,
                          id=2, uuid=uuid)
