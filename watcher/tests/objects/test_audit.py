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

import mock

from watcher.common import exception
from watcher.common import utils as w_utils
from watcher.db.sqlalchemy import api as db_api
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestAuditObject(base.DbTestCase):

    goal_id = 2

    goal_data = utils.get_test_goal(
        id=goal_id, uuid=w_utils.generate_uuid(), name="DUMMY")

    scenarios = [
        ('non_eager', dict(
            eager=False,
            fake_audit=utils.get_test_audit(
                goal_id=goal_id))),
        ('eager_with_non_eager_load', dict(
            eager=True,
            fake_audit=utils.get_test_audit(
                goal_id=goal_id))),
        ('eager_with_eager_load', dict(
            eager=True,
            fake_audit=utils.get_test_audit(goal_id=goal_id, goal=goal_data))),
    ]

    def setUp(self):
        super(TestAuditObject, self).setUp()
        self.fake_goal = utils.create_test_goal(**self.goal_data)

    def eager_load_audit_assert(self, audit, goal):
        if self.eager:
            self.assertIsNotNone(audit.goal)
            fields_to_check = set(
                super(objects.Goal, objects.Goal).fields
            ).symmetric_difference(objects.Goal.fields)
            db_data = {
                k: v for k, v in goal.as_dict().items()
                if k in fields_to_check}
            object_data = {
                k: v for k, v in audit.goal.as_dict().items()
                if k in fields_to_check}
            self.assertEqual(db_data, object_data)

    @mock.patch.object(db_api.Connection, 'get_audit_by_id')
    def test_get_by_id(self, mock_get_audit):
        mock_get_audit.return_value = self.fake_audit
        audit_id = self.fake_audit['id']
        audit = objects.Audit.get(self.context, audit_id, eager=self.eager)
        mock_get_audit.assert_called_once_with(
            self.context, audit_id, eager=self.eager)
        self.assertEqual(self.context, audit._context)
        self.eager_load_audit_assert(audit, self.fake_goal)

    @mock.patch.object(db_api.Connection, 'get_audit_by_uuid')
    def test_get_by_uuid(self, mock_get_audit):
        mock_get_audit.return_value = self.fake_audit
        uuid = self.fake_audit['uuid']
        audit = objects.Audit.get(self.context, uuid, eager=self.eager)
        mock_get_audit.assert_called_once_with(
            self.context, uuid, eager=self.eager)
        self.assertEqual(self.context, audit._context)
        self.eager_load_audit_assert(audit, self.fake_goal)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.Audit.get, self.context,
                          'not-a-uuid', eager=self.eager)

    @mock.patch.object(db_api.Connection, 'get_audit_list')
    def test_list(self, mock_get_list):
        mock_get_list.return_value = [self.fake_audit]
        audits = objects.Audit.list(self.context, eager=self.eager)
        mock_get_list.assert_called_once_with(
            self.context, eager=self.eager, filters=None, limit=None,
            marker=None, sort_dir=None, sort_key=None)
        self.assertEqual(1, len(audits))
        self.assertIsInstance(audits[0], objects.Audit)
        self.assertEqual(self.context, audits[0]._context)
        for audit in audits:
            self.eager_load_audit_assert(audit, self.fake_goal)

    @mock.patch.object(db_api.Connection, 'update_audit')
    @mock.patch.object(db_api.Connection, 'get_audit_by_uuid')
    def test_save(self, mock_get_audit, mock_update_audit):
        mock_get_audit.return_value = self.fake_audit
        uuid = self.fake_audit['uuid']
        audit = objects.Audit.get_by_uuid(self.context, uuid, eager=self.eager)
        audit.state = 'SUCCEEDED'
        audit.save()

        mock_get_audit.assert_called_once_with(
            self.context, uuid, eager=self.eager)
        mock_update_audit.assert_called_once_with(
            uuid, {'state': 'SUCCEEDED'})
        self.assertEqual(self.context, audit._context)
        self.eager_load_audit_assert(audit, self.fake_goal)

    @mock.patch.object(db_api.Connection, 'get_audit_by_uuid')
    def test_refresh(self, mock_get_audit):
        returns = [dict(self.fake_audit, state="first state"),
                   dict(self.fake_audit, state="second state")]
        mock_get_audit.side_effect = returns
        uuid = self.fake_audit['uuid']
        expected = [
            mock.call(self.context, uuid, eager=self.eager),
            mock.call(self.context, uuid, eager=self.eager)]
        audit = objects.Audit.get(self.context, uuid, eager=self.eager)
        self.assertEqual("first state", audit.state)
        audit.refresh(eager=self.eager)
        self.assertEqual("second state", audit.state)
        self.assertEqual(expected, mock_get_audit.call_args_list)
        self.assertEqual(self.context, audit._context)
        self.eager_load_audit_assert(audit, self.fake_goal)


class TestCreateDeleteAuditObject(base.DbTestCase):

    def setUp(self):
        super(TestCreateDeleteAuditObject, self).setUp()
        self.goal_id = 1
        self.fake_audit = utils.get_test_audit(goal_id=self.goal_id)

    @mock.patch.object(db_api.Connection, 'create_audit')
    def test_create(self, mock_create_audit):
        utils.create_test_goal(id=self.goal_id)
        mock_create_audit.return_value = self.fake_audit
        audit = objects.Audit(self.context, **self.fake_audit)
        audit.create()
        mock_create_audit.assert_called_once_with(self.fake_audit)
        self.assertEqual(self.context, audit._context)

    @mock.patch.object(db_api.Connection, 'update_audit')
    @mock.patch.object(db_api.Connection, 'soft_delete_audit')
    @mock.patch.object(db_api.Connection, 'get_audit_by_uuid')
    def test_soft_delete(self, mock_get_audit,
                         mock_soft_delete_audit, mock_update_audit):
        mock_get_audit.return_value = self.fake_audit
        uuid = self.fake_audit['uuid']
        audit = objects.Audit.get_by_uuid(self.context, uuid)
        audit.soft_delete()
        mock_get_audit.assert_called_once_with(self.context, uuid, eager=False)
        mock_soft_delete_audit.assert_called_once_with(uuid)
        mock_update_audit.assert_called_once_with(uuid, {'state': 'DELETED'})
        self.assertEqual(self.context, audit._context)

    @mock.patch.object(db_api.Connection, 'destroy_audit')
    @mock.patch.object(db_api.Connection, 'get_audit_by_uuid')
    def test_destroy(self, mock_get_audit,
                     mock_destroy_audit):
        mock_get_audit.return_value = self.fake_audit
        uuid = self.fake_audit['uuid']
        audit = objects.Audit.get_by_uuid(self.context, uuid)
        audit.destroy()
        mock_get_audit.assert_called_once_with(
            self.context, uuid, eager=False)
        mock_destroy_audit.assert_called_once_with(uuid)
        self.assertEqual(self.context, audit._context)
