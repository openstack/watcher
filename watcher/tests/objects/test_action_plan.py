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

import iso8601

from watcher.common import exception
from watcher.common import utils as common_utils
from watcher import conf
from watcher.db.sqlalchemy import api as db_api
from watcher import notifications
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils

CONF = conf.CONF


class TestActionPlanObject(base.DbTestCase):

    audit_id = 2
    strategy_id = 2

    scenarios = [
        ('non_eager', dict(
            eager=False,
            fake_action_plan=utils.get_test_action_plan(
                created_at=datetime.datetime.utcnow(),
                audit_id=audit_id,
                strategy_id=strategy_id))),
        ('eager_with_non_eager_load', dict(
            eager=True,
            fake_action_plan=utils.get_test_action_plan(
                created_at=datetime.datetime.utcnow(),
                audit_id=audit_id,
                strategy_id=strategy_id))),
        ('eager_with_eager_load', dict(
            eager=True,
            fake_action_plan=utils.get_test_action_plan(
                created_at=datetime.datetime.utcnow(),
                strategy_id=strategy_id,
                strategy=utils.get_test_strategy(id=strategy_id),
                audit_id=audit_id,
                audit=utils.get_test_audit(id=audit_id)))),
    ]

    def setUp(self):
        super(TestActionPlanObject, self).setUp()

        p_action_plan_notifications = mock.patch.object(
            notifications, 'action_plan', autospec=True)
        self.m_action_plan_notifications = p_action_plan_notifications.start()
        self.addCleanup(p_action_plan_notifications.stop)
        self.m_send_update = self.m_action_plan_notifications.send_update

        self.fake_audit = utils.create_test_audit(id=self.audit_id)
        self.fake_strategy = utils.create_test_strategy(
            id=self.strategy_id, name="DUMMY")

    def eager_load_action_plan_assert(self, action_plan):
        if self.eager:
            self.assertIsNotNone(action_plan.audit)
            fields_to_check = set(
                super(objects.Audit, objects.Audit).fields
            ).symmetric_difference(objects.Audit.fields)
            db_data = {
                k: v for k, v in self.fake_audit.as_dict().items()
                if k in fields_to_check}
            object_data = {
                k: v for k, v in action_plan.audit.as_dict().items()
                if k in fields_to_check}
            self.assertEqual(db_data, object_data)

    @mock.patch.object(db_api.Connection, 'get_action_plan_by_id')
    def test_get_by_id(self, mock_get_action_plan):
        mock_get_action_plan.return_value = self.fake_action_plan
        action_plan_id = self.fake_action_plan['id']
        action_plan = objects.ActionPlan.get(
            self.context, action_plan_id, eager=self.eager)
        mock_get_action_plan.assert_called_once_with(
            self.context, action_plan_id, eager=self.eager)
        self.assertEqual(self.context, action_plan._context)
        self.eager_load_action_plan_assert(action_plan)
        self.assertEqual(0, self.m_send_update.call_count)

    @mock.patch.object(db_api.Connection, 'get_action_plan_by_uuid')
    def test_get_by_uuid(self, mock_get_action_plan):
        mock_get_action_plan.return_value = self.fake_action_plan
        uuid = self.fake_action_plan['uuid']
        action_plan = objects.ActionPlan.get(
            self.context, uuid, eager=self.eager)
        mock_get_action_plan.assert_called_once_with(
            self.context, uuid, eager=self.eager)
        self.assertEqual(self.context, action_plan._context)
        self.eager_load_action_plan_assert(action_plan)
        self.assertEqual(0, self.m_send_update.call_count)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.ActionPlan.get, self.context,
                          'not-a-uuid', eager=self.eager)

    @mock.patch.object(db_api.Connection, 'get_action_plan_list')
    def test_list(self, mock_get_list):
        mock_get_list.return_value = [self.fake_action_plan]
        action_plans = objects.ActionPlan.list(self.context, eager=self.eager)
        self.assertEqual(1, mock_get_list.call_count)
        self.assertEqual(1, len(action_plans))
        self.assertIsInstance(action_plans[0], objects.ActionPlan)
        self.assertEqual(self.context, action_plans[0]._context)
        for action_plan in action_plans:
            self.eager_load_action_plan_assert(action_plan)
        self.assertEqual(0, self.m_send_update.call_count)

    @mock.patch.object(db_api.Connection, 'update_action_plan')
    @mock.patch.object(db_api.Connection, 'get_action_plan_by_uuid')
    def test_save(self, mock_get_action_plan, mock_update_action_plan):
        mock_get_action_plan.return_value = self.fake_action_plan
        fake_saved_action_plan = self.fake_action_plan.copy()
        fake_saved_action_plan['state'] = objects.action_plan.State.SUCCEEDED
        fake_saved_action_plan['updated_at'] = datetime.datetime.utcnow()

        mock_update_action_plan.return_value = fake_saved_action_plan

        expected_action_plan = fake_saved_action_plan.copy()
        expected_action_plan[
            'created_at'] = expected_action_plan['created_at'].replace(
                tzinfo=iso8601.UTC)
        expected_action_plan[
            'updated_at'] = expected_action_plan['updated_at'].replace(
                tzinfo=iso8601.UTC)

        uuid = self.fake_action_plan['uuid']
        action_plan = objects.ActionPlan.get_by_uuid(
            self.context, uuid, eager=self.eager)
        action_plan.state = objects.action_plan.State.SUCCEEDED
        action_plan.save()

        mock_get_action_plan.assert_called_once_with(
            self.context, uuid, eager=self.eager)
        mock_update_action_plan.assert_called_once_with(
            uuid, {'state': objects.action_plan.State.SUCCEEDED})
        self.assertEqual(self.context, action_plan._context)
        self.eager_load_action_plan_assert(action_plan)
        self.m_send_update.assert_called_once_with(
            self.context, action_plan,
            old_state=self.fake_action_plan['state'])
        self.assertEqual(
            {k: v for k, v in expected_action_plan.items()
             if k not in action_plan.object_fields},
            {k: v for k, v in action_plan.as_dict().items()
             if k not in action_plan.object_fields})

    @mock.patch.object(db_api.Connection, 'get_action_plan_by_uuid')
    def test_refresh(self, mock_get_action_plan):
        returns = [dict(self.fake_action_plan, state="first state"),
                   dict(self.fake_action_plan, state="second state")]
        mock_get_action_plan.side_effect = returns
        uuid = self.fake_action_plan['uuid']
        expected = [mock.call(self.context, uuid, eager=self.eager),
                    mock.call(self.context, uuid, eager=self.eager)]
        action_plan = objects.ActionPlan.get(
            self.context, uuid, eager=self.eager)
        self.assertEqual("first state", action_plan.state)
        action_plan.refresh(eager=self.eager)
        self.assertEqual("second state", action_plan.state)
        self.assertEqual(expected, mock_get_action_plan.call_args_list)
        self.assertEqual(self.context, action_plan._context)
        self.eager_load_action_plan_assert(action_plan)


class TestCreateDeleteActionPlanObject(base.DbTestCase):

    def setUp(self):
        super(TestCreateDeleteActionPlanObject, self).setUp()

        p_action_plan_notifications = mock.patch.object(
            notifications, 'action_plan', autospec=True)
        self.m_action_plan_notifications = p_action_plan_notifications.start()
        self.addCleanup(p_action_plan_notifications.stop)
        self.m_send_update = self.m_action_plan_notifications.send_update

        self.fake_strategy = utils.create_test_strategy(name="DUMMY")
        self.fake_audit = utils.create_test_audit()
        self.fake_action_plan = utils.get_test_action_plan(
            created_at=datetime.datetime.utcnow())

    @mock.patch.object(db_api.Connection, 'create_action_plan')
    def test_create(self, mock_create_action_plan):
        mock_create_action_plan.return_value = self.fake_action_plan
        action_plan = objects.ActionPlan(
            self.context, **self.fake_action_plan)
        action_plan.create()
        expected_action_plan = self.fake_action_plan.copy()
        expected_action_plan['created_at'] = expected_action_plan[
            'created_at'].replace(tzinfo=iso8601.UTC)
        mock_create_action_plan.assert_called_once_with(expected_action_plan)
        self.assertEqual(self.context, action_plan._context)

    @mock.patch.multiple(
        db_api.Connection,
        get_action_plan_by_uuid=mock.DEFAULT,
        soft_delete_action_plan=mock.DEFAULT,
        update_action_plan=mock.DEFAULT,
        get_efficacy_indicator_list=mock.DEFAULT,
        soft_delete_efficacy_indicator=mock.DEFAULT,
    )
    def test_soft_delete(self, get_action_plan_by_uuid,
                         soft_delete_action_plan, update_action_plan,
                         get_efficacy_indicator_list,
                         soft_delete_efficacy_indicator):
        efficacy_indicator = utils.get_test_efficacy_indicator(
            action_plan_id=self.fake_action_plan['id'])
        uuid = self.fake_action_plan['uuid']
        m_get_action_plan = get_action_plan_by_uuid
        m_soft_delete_action_plan = soft_delete_action_plan
        m_get_efficacy_indicator_list = get_efficacy_indicator_list
        m_soft_delete_efficacy_indicator = soft_delete_efficacy_indicator
        m_update_action_plan = update_action_plan

        m_get_action_plan.return_value = self.fake_action_plan
        fake_deleted_action_plan = self.fake_action_plan.copy()
        fake_deleted_action_plan['deleted_at'] = datetime.datetime.utcnow()
        m_update_action_plan.return_value = fake_deleted_action_plan
        m_soft_delete_action_plan.return_value = fake_deleted_action_plan
        expected_action_plan = fake_deleted_action_plan.copy()
        expected_action_plan['created_at'] = expected_action_plan[
            'created_at'].replace(tzinfo=iso8601.UTC)
        expected_action_plan['deleted_at'] = expected_action_plan[
            'deleted_at'].replace(tzinfo=iso8601.UTC)
        del expected_action_plan['audit']
        del expected_action_plan['strategy']

        m_get_efficacy_indicator_list.return_value = [efficacy_indicator]
        action_plan = objects.ActionPlan.get_by_uuid(
            self.context, uuid, eager=False)
        action_plan.soft_delete()

        m_get_action_plan.assert_called_once_with(
            self.context, uuid, eager=False)
        m_get_efficacy_indicator_list.assert_called_once_with(
            self.context, filters={"action_plan_uuid": uuid},
            limit=None, marker=None, sort_dir=None, sort_key=None)
        m_soft_delete_action_plan.assert_called_once_with(uuid)
        m_soft_delete_efficacy_indicator.assert_called_once_with(
            efficacy_indicator['uuid'])
        m_update_action_plan.assert_called_once_with(
            uuid, {'state': objects.action_plan.State.DELETED})

        self.assertEqual(self.context, action_plan._context)
        self.assertEqual(expected_action_plan, action_plan.as_dict())

    @mock.patch.multiple(
        db_api.Connection,
        get_action_plan_by_uuid=mock.DEFAULT,
        destroy_action_plan=mock.DEFAULT,
        get_efficacy_indicator_list=mock.DEFAULT,
        destroy_efficacy_indicator=mock.DEFAULT,
    )
    def test_destroy(self, get_action_plan_by_uuid, destroy_action_plan,
                     get_efficacy_indicator_list, destroy_efficacy_indicator):
        m_get_action_plan = get_action_plan_by_uuid
        m_destroy_action_plan = destroy_action_plan
        m_get_efficacy_indicator_list = get_efficacy_indicator_list
        m_destroy_efficacy_indicator = destroy_efficacy_indicator
        efficacy_indicator = utils.get_test_efficacy_indicator(
            action_plan_id=self.fake_action_plan['id'])
        uuid = self.fake_action_plan['uuid']
        m_get_action_plan.return_value = self.fake_action_plan
        m_get_efficacy_indicator_list.return_value = [efficacy_indicator]
        action_plan = objects.ActionPlan.get_by_uuid(self.context, uuid)
        action_plan.destroy()

        m_get_action_plan.assert_called_once_with(
            self.context, uuid, eager=False)
        m_get_efficacy_indicator_list.assert_called_once_with(
            self.context, filters={"action_plan_uuid": uuid},
            limit=None, marker=None, sort_dir=None, sort_key=None)
        m_destroy_action_plan.assert_called_once_with(uuid)
        m_destroy_efficacy_indicator.assert_called_once_with(
            efficacy_indicator['uuid'])
        self.assertEqual(self.context, action_plan._context)


@mock.patch.object(notifications.action_plan, 'send_update', mock.Mock())
class TestStateManager(base.DbTestCase):

    def setUp(self):
        super(TestStateManager, self).setUp()
        self.state_manager = objects.action_plan.StateManager()

    def test_check_expired(self):
        CONF.set_default('action_plan_expiry', 0,
                         group='watcher_decision_engine')
        strategy_1 = utils.create_test_strategy(
            uuid=common_utils.generate_uuid())
        audit_1 = utils.create_test_audit(
            uuid=common_utils.generate_uuid())
        action_plan_1 = utils.create_test_action_plan(
            state=objects.action_plan.State.RECOMMENDED,
            uuid=common_utils.generate_uuid(),
            audit_id=audit_1.id,
            strategy_id=strategy_1.id)

        self.state_manager.check_expired(self.context)

        action_plan = objects.action_plan.ActionPlan.get_by_uuid(
            self.context, action_plan_1.uuid)
        self.assertEqual(objects.action_plan.State.SUPERSEDED,
                         action_plan.state)
