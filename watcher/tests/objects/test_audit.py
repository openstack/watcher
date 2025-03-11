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

import datetime
from unittest import mock

from oslo_utils import timeutils

from watcher.common import exception
from watcher.common import rpc
from watcher.common import utils as w_utils
from watcher.db.sqlalchemy import api as db_api
from watcher import notifications
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils
from watcher.tests.objects import utils as objutils


class TestAuditObject(base.DbTestCase):

    goal_id = 2

    goal_data = utils.get_test_goal(
        id=goal_id, uuid=w_utils.generate_uuid(), name="DUMMY")

    scenarios = [
        ('non_eager', dict(
            eager=False,
            fake_audit=utils.get_test_audit(
                created_at=timeutils.utcnow(),
                goal_id=goal_id))),
        ('eager_with_non_eager_load', dict(
            eager=True,
            fake_audit=utils.get_test_audit(
                created_at=timeutils.utcnow(),
                goal_id=goal_id))),
        ('eager_with_eager_load', dict(
            eager=True,
            fake_audit=utils.get_test_audit(
                created_at=timeutils.utcnow(),
                goal_id=goal_id, goal=goal_data))),
    ]

    def setUp(self):
        super(TestAuditObject, self).setUp()

        p_audit_notifications = mock.patch.object(
            notifications, 'audit', autospec=True)
        self.m_audit_notifications = p_audit_notifications.start()
        self.addCleanup(p_audit_notifications.stop)
        self.m_send_update = self.m_audit_notifications.send_update
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
        self.assertEqual(0, self.m_send_update.call_count)

    @mock.patch.object(db_api.Connection, 'get_audit_by_uuid')
    def test_get_by_uuid(self, mock_get_audit):
        mock_get_audit.return_value = self.fake_audit
        uuid = self.fake_audit['uuid']
        audit = objects.Audit.get(self.context, uuid, eager=self.eager)
        mock_get_audit.assert_called_once_with(
            self.context, uuid, eager=self.eager)
        self.assertEqual(self.context, audit._context)
        self.eager_load_audit_assert(audit, self.fake_goal)
        self.assertEqual(0, self.m_send_update.call_count)

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
        self.assertEqual(0, self.m_send_update.call_count)

    @mock.patch.object(db_api.Connection, 'update_audit')
    @mock.patch.object(db_api.Connection, 'get_audit_by_uuid')
    def test_save(self, mock_get_audit, mock_update_audit):
        mock_get_audit.return_value = self.fake_audit
        fake_saved_audit = self.fake_audit.copy()
        fake_saved_audit['state'] = objects.audit.State.SUCCEEDED
        fake_saved_audit['updated_at'] = timeutils.utcnow()
        mock_update_audit.return_value = fake_saved_audit

        expected_audit = fake_saved_audit.copy()
        expected_audit['created_at'] = expected_audit['created_at'].replace(
            tzinfo=datetime.timezone.utc)
        expected_audit['updated_at'] = expected_audit['updated_at'].replace(
            tzinfo=datetime.timezone.utc)

        uuid = self.fake_audit['uuid']
        audit = objects.Audit.get_by_uuid(self.context, uuid, eager=self.eager)
        audit.state = objects.audit.State.SUCCEEDED
        audit.save()

        mock_get_audit.assert_called_once_with(
            self.context, uuid, eager=self.eager)
        mock_update_audit.assert_called_once_with(
            uuid, {'state': objects.audit.State.SUCCEEDED})
        self.assertEqual(self.context, audit._context)
        self.eager_load_audit_assert(audit, self.fake_goal)
        self.m_send_update.assert_called_once_with(
            self.context, audit, old_state=self.fake_audit['state'])
        self.assertEqual(
            {k: v for k, v in expected_audit.items()
             if k not in audit.object_fields},
            {k: v for k, v in audit.as_dict().items()
             if k not in audit.object_fields})

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
        p_audit_notifications = mock.patch.object(
            notifications, 'audit', autospec=True)
        self.m_audit_notifications = p_audit_notifications.start()
        self.addCleanup(p_audit_notifications.stop)
        self.m_send_update = self.m_audit_notifications.send_update

        self.goal_id = 1
        self.goal = utils.create_test_goal(id=self.goal_id, name="DUMMY")
        self.fake_audit = utils.get_test_audit(
            goal_id=self.goal_id, created_at=timeutils.utcnow())

    @mock.patch.object(db_api.Connection, 'create_audit')
    def test_create(self, mock_create_audit):
        mock_create_audit.return_value = self.fake_audit
        audit = objects.Audit(self.context, **self.fake_audit)
        audit.create()
        expected_audit = self.fake_audit.copy()
        expected_audit['created_at'] = expected_audit['created_at'].replace(
            tzinfo=datetime.timezone.utc)
        mock_create_audit.assert_called_once_with(expected_audit)
        self.assertEqual(self.context, audit._context)

    @mock.patch.object(db_api.Connection, 'update_audit')
    @mock.patch.object(db_api.Connection, 'soft_delete_audit')
    @mock.patch.object(db_api.Connection, 'get_audit_by_uuid')
    def test_soft_delete(self, mock_get_audit,
                         mock_soft_delete_audit, mock_update_audit):
        mock_get_audit.return_value = self.fake_audit
        fake_deleted_audit = self.fake_audit.copy()
        fake_deleted_audit['deleted_at'] = timeutils.utcnow()
        mock_soft_delete_audit.return_value = fake_deleted_audit
        mock_update_audit.return_value = fake_deleted_audit

        expected_audit = fake_deleted_audit.copy()
        expected_audit['created_at'] = expected_audit['created_at'].replace(
            tzinfo=datetime.timezone.utc)
        expected_audit['deleted_at'] = expected_audit['deleted_at'].replace(
            tzinfo=datetime.timezone.utc)
        del expected_audit['goal']
        del expected_audit['strategy']

        uuid = self.fake_audit['uuid']
        audit = objects.Audit.get_by_uuid(self.context, uuid, eager=False)
        audit.soft_delete()
        mock_get_audit.assert_called_once_with(self.context, uuid, eager=False)
        mock_soft_delete_audit.assert_called_once_with(uuid)
        mock_update_audit.assert_called_once_with(uuid, {'state': 'DELETED'})
        self.assertEqual(self.context, audit._context)
        self.assertEqual(expected_audit, audit.as_dict())

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


class TestAuditObjectSendNotifications(base.DbTestCase):

    def setUp(self):
        super(TestAuditObjectSendNotifications, self).setUp()
        goal_id = 1
        self.fake_goal = utils.create_test_goal(id=goal_id, name="DUMMY")
        self.fake_strategy = utils.create_test_strategy(
            id=goal_id, name="DUMMY")
        self.fake_audit = utils.get_test_audit(
            goal_id=goal_id, goal=utils.get_test_goal(id=goal_id),
            strategy_id=self.fake_strategy.id, strategy=self.fake_strategy)

        p_get_notifier = mock.patch.object(rpc, 'get_notifier')
        self.m_get_notifier = p_get_notifier.start()
        self.m_get_notifier.return_value = mock.Mock(name='m_notifier')
        self.m_notifier = self.m_get_notifier.return_value
        self.addCleanup(p_get_notifier.stop)

    @mock.patch.object(db_api.Connection, 'update_audit')
    @mock.patch.object(db_api.Connection, 'get_audit_by_uuid')
    def test_send_update_notification(self, m_get_audit, m_update_audit):
        fake_audit = utils.get_test_audit(
            goal=self.fake_goal.as_dict(),
            strategy_id=self.fake_strategy.id,
            strategy=self.fake_strategy.as_dict())
        m_get_audit.return_value = fake_audit
        fake_saved_audit = self.fake_audit.copy()
        fake_saved_audit['state'] = objects.audit.State.SUCCEEDED
        m_update_audit.return_value = fake_saved_audit
        uuid = fake_audit['uuid']

        audit = objects.Audit.get_by_uuid(self.context, uuid, eager=True)
        audit.state = objects.audit.State.ONGOING
        audit.save()

        self.assertEqual(1, self.m_notifier.info.call_count)
        self.assertEqual('audit.update',
                         self.m_notifier.info.call_args[1]['event_type'])

    @mock.patch.object(db_api.Connection, 'create_audit')
    def test_send_create_notification(self, m_create_audit):
        audit = objutils.get_test_audit(
            self.context,
            id=1,
            goal_id=self.fake_goal.id,
            strategy_id=self.fake_strategy.id,
            goal=self.fake_goal.as_dict(),
            strategy=self.fake_strategy.as_dict())
        m_create_audit.return_value = audit
        audit.create()

        self.assertEqual(1, self.m_notifier.info.call_count)
        self.assertEqual('audit.create',
                         self.m_notifier.info.call_args[1]['event_type'])

    @mock.patch.object(db_api.Connection, 'update_audit')
    @mock.patch.object(db_api.Connection, 'soft_delete_audit')
    @mock.patch.object(db_api.Connection, 'get_audit_by_uuid')
    def test_send_delete_notification(
            self, m_get_audit, m_soft_delete_audit, m_update_audit):
        fake_audit = utils.get_test_audit(
            goal=self.fake_goal.as_dict(),
            strategy_id=self.fake_strategy.id,
            strategy=self.fake_strategy.as_dict())
        m_get_audit.return_value = fake_audit
        fake_deleted_audit = self.fake_audit.copy()
        fake_deleted_audit['deleted_at'] = timeutils.utcnow()
        expected_audit = fake_deleted_audit.copy()
        expected_audit['deleted_at'] = expected_audit['deleted_at'].replace(
            tzinfo=datetime.timezone.utc)

        m_soft_delete_audit.return_value = fake_deleted_audit
        m_update_audit.return_value = fake_deleted_audit
        uuid = fake_audit['uuid']
        audit = objects.Audit.get_by_uuid(self.context, uuid, eager=True)
        audit.soft_delete()

        self.assertEqual(2, self.m_notifier.info.call_count)
        self.assertEqual(
            'audit.update',
            self.m_notifier.info.call_args_list[0][1]['event_type'])
        self.assertEqual(
            'audit.delete',
            self.m_notifier.info.call_args_list[1][1]['event_type'])
