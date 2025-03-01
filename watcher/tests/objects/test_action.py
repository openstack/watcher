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
from watcher.common import utils as c_utils
from watcher.db.sqlalchemy import api as db_api
from watcher import notifications
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestActionObject(base.DbTestCase):

    action_plan_id = 2

    scenarios = [
        ('non_eager', dict(
            eager=False,
            fake_action=utils.get_test_action(
                action_plan_id=action_plan_id))),
        ('eager_with_non_eager_load', dict(
            eager=True,
            fake_action=utils.get_test_action(
                action_plan_id=action_plan_id))),
        ('eager_with_eager_load', dict(
            eager=True,
            fake_action=utils.get_test_action(
                action_plan_id=action_plan_id,
                action_plan=utils.get_test_action_plan(id=action_plan_id)))),
    ]

    def setUp(self):
        super(TestActionObject, self).setUp()

        p_action_notifications = mock.patch.object(
            notifications, 'action_plan', autospec=True)
        self.m_action_notifications = p_action_notifications.start()
        self.addCleanup(p_action_notifications.stop)
        self.m_send_update = self.m_action_notifications.send_update

        self.fake_action_plan = utils.create_test_action_plan(
            id=self.action_plan_id)

    def eager_action_assert(self, action):
        if self.eager:
            self.assertIsNotNone(action.action_plan)
            fields_to_check = set(
                super(objects.ActionPlan, objects.ActionPlan).fields
            ).symmetric_difference(objects.ActionPlan.fields)
            db_data = {
                k: v for k, v in self.fake_action_plan.as_dict().items()
                if k in fields_to_check}
            object_data = {
                k: v for k, v in action.action_plan.as_dict().items()
                if k in fields_to_check}
            self.assertEqual(db_data, object_data)

    @mock.patch.object(db_api.Connection, 'get_action_by_id')
    def test_get_by_id(self, mock_get_action):
        mock_get_action.return_value = self.fake_action
        action_id = self.fake_action['id']
        action = objects.Action.get(self.context, action_id, eager=self.eager)
        mock_get_action.assert_called_once_with(
            self.context, action_id, eager=self.eager)
        self.assertEqual(self.context, action._context)
        self.eager_action_assert(action)
        self.assertEqual(0, self.m_send_update.call_count)

    @mock.patch.object(db_api.Connection, 'get_action_by_uuid')
    def test_get_by_uuid(self, mock_get_action):
        mock_get_action.return_value = self.fake_action
        uuid = self.fake_action['uuid']
        action = objects.Action.get(self.context, uuid, eager=self.eager)
        mock_get_action.assert_called_once_with(
            self.context, uuid, eager=self.eager)
        self.assertEqual(self.context, action._context)
        self.assertEqual(0, self.m_send_update.call_count)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.Action.get, self.context, 'not-a-uuid',
                          eager=self.eager)

    @mock.patch.object(db_api.Connection, 'get_action_list')
    def test_list(self, mock_get_list):
        mock_get_list.return_value = [self.fake_action]
        actions = objects.Action.list(self.context, eager=self.eager)
        self.assertEqual(1, mock_get_list.call_count)
        self.assertEqual(1, len(actions))
        self.assertIsInstance(actions[0], objects.Action)
        self.assertEqual(self.context, actions[0]._context)
        for action in actions:
            self.eager_action_assert(action)
        self.assertEqual(0, self.m_send_update.call_count)

    @mock.patch.object(objects.Strategy, 'get')
    @mock.patch.object(objects.Audit, 'get')
    @mock.patch.object(db_api.Connection, 'update_action')
    @mock.patch.object(db_api.Connection, 'get_action_by_uuid')
    def test_save(self, mock_get_action, mock_update_action, mock_get_audit,
                  mock_get_strategy):
        mock_get_action.return_value = self.fake_action
        fake_saved_action = self.fake_action.copy()
        mock_get_audit.return_value = mock.PropertyMock(
            uuid=c_utils.generate_uuid())
        mock_get_strategy.return_value = mock.PropertyMock(
            uuid=c_utils.generate_uuid())
        fake_saved_action['updated_at'] = timeutils.utcnow()
        mock_update_action.return_value = fake_saved_action
        uuid = self.fake_action['uuid']
        action = objects.Action.get_by_uuid(
            self.context, uuid, eager=self.eager)
        action.state = objects.action.State.SUCCEEDED
        if not self.eager:
            self.assertRaises(exception.EagerlyLoadedActionRequired,
                              action.save)
        else:
            action.save()

        expected_update_at = fake_saved_action['updated_at'].replace(
            tzinfo=datetime.timezone.utc)

        mock_get_action.assert_called_once_with(
            self.context, uuid, eager=self.eager)
        mock_update_action.assert_called_once_with(
            uuid, {'state': objects.action.State.SUCCEEDED})
        self.assertEqual(self.context, action._context)
        self.assertEqual(expected_update_at, action.updated_at)
        self.assertEqual(0, self.m_send_update.call_count)

    @mock.patch.object(db_api.Connection, 'get_action_by_uuid')
    def test_refresh(self, mock_get_action):
        returns = [dict(self.fake_action, state="first state"),
                   dict(self.fake_action, state="second state")]
        mock_get_action.side_effect = returns
        uuid = self.fake_action['uuid']
        expected = [mock.call(self.context, uuid, eager=self.eager),
                    mock.call(self.context, uuid, eager=self.eager)]
        action = objects.Action.get(self.context, uuid, eager=self.eager)
        self.assertEqual("first state", action.state)
        action.refresh(eager=self.eager)
        self.assertEqual("second state", action.state)
        self.assertEqual(expected, mock_get_action.call_args_list)
        self.assertEqual(self.context, action._context)
        self.eager_action_assert(action)
        self.assertEqual(0, self.m_send_update.call_count)


class TestCreateDeleteActionObject(base.DbTestCase):

    def setUp(self):
        super(TestCreateDeleteActionObject, self).setUp()
        self.fake_strategy = utils.create_test_strategy(name="DUMMY")
        self.fake_audit = utils.create_test_audit()
        self.fake_action_plan = utils.create_test_action_plan()
        self.fake_action = utils.get_test_action(
            created_at=timeutils.utcnow())

    @mock.patch.object(db_api.Connection, 'create_action')
    def test_create(self, mock_create_action):
        mock_create_action.return_value = self.fake_action
        action = objects.Action(self.context, **self.fake_action)
        action.create()
        expected_action = self.fake_action.copy()
        expected_action['created_at'] = expected_action['created_at'].replace(
            tzinfo=datetime.timezone.utc)
        mock_create_action.assert_called_once_with(expected_action)
        self.assertEqual(self.context, action._context)

    @mock.patch.object(notifications.action, 'send_delete')
    @mock.patch.object(notifications.action, 'send_update')
    @mock.patch.object(db_api.Connection, 'update_action')
    @mock.patch.object(db_api.Connection, 'soft_delete_action')
    @mock.patch.object(db_api.Connection, 'get_action_by_uuid')
    def test_soft_delete(self, mock_get_action,
                         mock_soft_delete_action, mock_update_action,
                         mock_send_update, mock_send_delete):
        mock_get_action.return_value = self.fake_action
        fake_deleted_action = self.fake_action.copy()
        fake_deleted_action['deleted_at'] = timeutils.utcnow()
        mock_soft_delete_action.return_value = fake_deleted_action
        mock_update_action.return_value = fake_deleted_action

        expected_action = fake_deleted_action.copy()
        expected_action['created_at'] = expected_action['created_at'].replace(
            tzinfo=datetime.timezone.utc)
        expected_action['deleted_at'] = expected_action['deleted_at'].replace(
            tzinfo=datetime.timezone.utc)
        del expected_action['action_plan']

        uuid = self.fake_action['uuid']
        action = objects.Action.get_by_uuid(self.context, uuid)
        action.soft_delete()
        mock_get_action.assert_called_once_with(
            self.context, uuid, eager=False)
        mock_soft_delete_action.assert_called_once_with(uuid)
        mock_update_action.assert_called_once_with(
            uuid, {'state': objects.action.State.DELETED})
        self.assertEqual(self.context, action._context)
        self.assertEqual(expected_action, action.as_dict())

    @mock.patch.object(db_api.Connection, 'destroy_action')
    @mock.patch.object(db_api.Connection, 'get_action_by_uuid')
    def test_destroy(self, mock_get_action, mock_destroy_action):
        mock_get_action.return_value = self.fake_action
        uuid = self.fake_action['uuid']
        action = objects.Action.get_by_uuid(self.context, uuid)
        action.destroy()

        mock_get_action.assert_called_once_with(
            self.context, uuid, eager=False)
        mock_destroy_action.assert_called_once_with(uuid)
        self.assertEqual(self.context, action._context)
