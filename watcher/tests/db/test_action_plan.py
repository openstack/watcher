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

import six
from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.tests.db import base
from watcher.tests.db import utils


class DbActionPlanTestCase(base.DbTestCase):

    def _create_test_audit(self, **kwargs):
        audit = utils.get_test_audit(**kwargs)
        self.dbapi.create_audit(audit)
        return audit

    def _create_test_action_plan(self, **kwargs):
        action_plan = utils.get_test_action_plan(**kwargs)
        self.dbapi.create_action_plan(action_plan)
        return action_plan

    def test_get_action_plan_list(self):
        uuids = []
        for i in range(1, 6):
            audit = utils.create_test_action_plan(uuid=w_utils.generate_uuid())
            uuids.append(six.text_type(audit['uuid']))
        res = self.dbapi.get_action_plan_list(self.context)
        res_uuids = [r.uuid for r in res]
        self.assertEqual(uuids.sort(), res_uuids.sort())

    def test_get_action_plan_list_with_filters(self):
        audit = self._create_test_audit(
            id=1,
            type='ONESHOT',
            uuid=w_utils.generate_uuid(),
            deadline=None,
            state='ONGOING')
        action_plan1 = self._create_test_action_plan(
            id=1,
            uuid=w_utils.generate_uuid(),
            audit_id=audit['id'],
            first_action_id=None,
            state='RECOMMENDED')
        action_plan2 = self._create_test_action_plan(
            id=2,
            uuid=w_utils.generate_uuid(),
            audit_id=audit['id'],
            first_action_id=action_plan1['id'],
            state='ONGOING')

        res = self.dbapi.get_action_plan_list(
            self.context,
            filters={'state': 'RECOMMENDED'})
        self.assertEqual([action_plan1['id']], [r.id for r in res])

        res = self.dbapi.get_action_plan_list(
            self.context,
            filters={'state': 'ONGOING'})
        self.assertEqual([action_plan2['id']], [r.id for r in res])

        res = self.dbapi.get_action_plan_list(
            self.context,
            filters={'audit_uuid': audit['uuid']})

        for r in res:
            self.assertEqual(audit['id'], r.audit_id)

    def test_get_action_plan_by_id(self):
        action_plan = self._create_test_action_plan()
        action_plan = self.dbapi.get_action_plan_by_id(
            self.context, action_plan['id'])
        self.assertEqual(action_plan['uuid'], action_plan.uuid)

    def test_get_action_plan_by_uuid(self):
        action_plan = self._create_test_action_plan()
        action_plan = self.dbapi.get_action_plan_by_uuid(
            self.context, action_plan['uuid'])
        self.assertEqual(action_plan['id'], action_plan.id)

    def test_get_action_plan_that_does_not_exist(self):
        self.assertRaises(exception.ActionPlanNotFound,
                          self.dbapi.get_action_plan_by_id, self.context, 1234)

    def test_update_action_plan(self):
        action_plan = self._create_test_action_plan()
        res = self.dbapi.update_action_plan(
            action_plan['id'], {'name': 'updated-model'})
        self.assertEqual('updated-model', res.name)

    def test_update_action_plan_that_does_not_exist(self):
        self.assertRaises(exception.ActionPlanNotFound,
                          self.dbapi.update_action_plan, 1234, {'name': ''})

    def test_update_action_plan_uuid(self):
        action_plan = self._create_test_action_plan()
        self.assertRaises(exception.InvalidParameterValue,
                          self.dbapi.update_action_plan, action_plan['id'],
                          {'uuid': 'hello'})

    def test_destroy_action_plan(self):
        action_plan = self._create_test_action_plan()
        self.dbapi.destroy_action_plan(action_plan['id'])
        self.assertRaises(exception.ActionPlanNotFound,
                          self.dbapi.get_action_plan_by_id,
                          self.context, action_plan['id'])

    def test_destroy_action_plan_by_uuid(self):
        uuid = w_utils.generate_uuid()
        self._create_test_action_plan(uuid=uuid)
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
        action_plan = self._create_test_action_plan()
        action = utils.create_test_action(action_plan_id=action_plan['id'])
        self.assertEqual(action_plan['id'], action.action_plan_id)
        self.assertRaises(exception.ActionPlanReferenced,
                          self.dbapi.destroy_action_plan, action_plan['id'])

    def test_create_action_plan_already_exists(self):
        uuid = w_utils.generate_uuid()
        self._create_test_action_plan(id=1, uuid=uuid)
        self.assertRaises(exception.ActionPlanAlreadyExists,
                          self._create_test_action_plan,
                          id=2, uuid=uuid)
