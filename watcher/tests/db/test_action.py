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

import six
from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.tests.db import base
from watcher.tests.db import utils


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
        for i in range(1, 6):
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
            state='PENDING',
            alarm=None)
        action2 = self._create_test_action(
            id=2,
            action_plan_id=2,
            description='description action 2',
            uuid=w_utils.generate_uuid(),
            next=action1['uuid'],
            state='PENDING',
            alarm=None)
        action3 = self._create_test_action(
            id=3,
            action_plan_id=1,
            description='description action 3',
            uuid=w_utils.generate_uuid(),
            next=action2['uuid'],
            state='ONGOING',
            alarm=None)
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
        self.assertRaises(exception.InvalidParameterValue,
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
