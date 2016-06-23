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
from testtools import matchers

from watcher.common import exception
# from watcher.common import utils as w_utils
from watcher import objects
from watcher.tests.db import base
from watcher.tests.db import utils


class TestActionPlanObject(base.DbTestCase):

    def setUp(self):
        super(TestActionPlanObject, self).setUp()
        self.fake_action_plan = utils.get_test_action_plan()

    def test_get_by_id(self):
        action_plan_id = self.fake_action_plan['id']
        with mock.patch.object(self.dbapi, 'get_action_plan_by_id',
                               autospec=True) as mock_get_action_plan:
            mock_get_action_plan.return_value = self.fake_action_plan
            action_plan = objects.ActionPlan.get(self.context, action_plan_id)
            mock_get_action_plan.assert_called_once_with(
                self.context, action_plan_id)
            self.assertEqual(self.context, action_plan._context)

    def test_get_by_uuid(self):
        uuid = self.fake_action_plan['uuid']
        with mock.patch.object(self.dbapi, 'get_action_plan_by_uuid',
                               autospec=True) as mock_get_action_plan:
            mock_get_action_plan.return_value = self.fake_action_plan
            action_plan = objects.ActionPlan.get(self.context, uuid)
            mock_get_action_plan.assert_called_once_with(self.context, uuid)
            self.assertEqual(self.context, action_plan._context)

    def test_get_bad_id_and_uuid(self):
        self.assertRaises(exception.InvalidIdentity,
                          objects.ActionPlan.get, self.context, 'not-a-uuid')

    def test_list(self):
        with mock.patch.object(self.dbapi, 'get_action_plan_list',
                               autospec=True) as mock_get_list:
            mock_get_list.return_value = [self.fake_action_plan]
            action_plans = objects.ActionPlan.list(self.context)
            self.assertEqual(1, mock_get_list.call_count)
            self.assertThat(action_plans, matchers.HasLength(1))
            self.assertIsInstance(action_plans[0], objects.ActionPlan)
            self.assertEqual(self.context, action_plans[0]._context)

    def test_create(self):
        with mock.patch.object(self.dbapi, 'create_action_plan',
                               autospec=True) as mock_create_action_plan:
            mock_create_action_plan.return_value = self.fake_action_plan
            action_plan = objects.ActionPlan(
                self.context, **self.fake_action_plan)
            action_plan.create()
            mock_create_action_plan.assert_called_once_with(
                self.fake_action_plan)
            self.assertEqual(self.context, action_plan._context)

    def test_destroy(self):
        efficacy_indicator = utils.get_test_efficacy_indicator(
            action_plan_id=self.fake_action_plan['id'])
        uuid = self.fake_action_plan['uuid']

        with mock.patch.multiple(
            self.dbapi, autospec=True,
            get_action_plan_by_uuid=mock.DEFAULT,
            destroy_action_plan=mock.DEFAULT,
            get_efficacy_indicator_list=mock.DEFAULT,
            destroy_efficacy_indicator=mock.DEFAULT,
        ) as m_dict:
            m_get_action_plan = m_dict['get_action_plan_by_uuid']
            m_destroy_action_plan = m_dict['destroy_action_plan']
            m_get_efficacy_indicator_list = (
                m_dict['get_efficacy_indicator_list'])
            m_destroy_efficacy_indicator = m_dict['destroy_efficacy_indicator']
            m_get_action_plan.return_value = self.fake_action_plan
            m_get_efficacy_indicator_list.return_value = [efficacy_indicator]
            action_plan = objects.ActionPlan.get_by_uuid(self.context, uuid)
            action_plan.destroy()
            m_get_action_plan.assert_called_once_with(self.context, uuid)
            m_get_efficacy_indicator_list.assert_called_once_with(
                self.context, filters={"action_plan_uuid": uuid},
                limit=None, marker=None, sort_dir=None, sort_key=None)
            m_destroy_action_plan.assert_called_once_with(uuid)
            m_destroy_efficacy_indicator.assert_called_once_with(
                efficacy_indicator['uuid'])
            self.assertEqual(self.context, action_plan._context)

    def test_soft_delete(self):
        efficacy_indicator = utils.get_test_efficacy_indicator(
            action_plan_id=self.fake_action_plan['id'])
        uuid = self.fake_action_plan['uuid']

        with mock.patch.multiple(
            self.dbapi, autospec=True,
            get_action_plan_by_uuid=mock.DEFAULT,
            soft_delete_action_plan=mock.DEFAULT,
            update_action_plan=mock.DEFAULT,
            get_efficacy_indicator_list=mock.DEFAULT,
            soft_delete_efficacy_indicator=mock.DEFAULT,
        ) as m_dict:
            m_get_action_plan = m_dict['get_action_plan_by_uuid']
            m_soft_delete_action_plan = m_dict['soft_delete_action_plan']
            m_get_efficacy_indicator_list = (
                m_dict['get_efficacy_indicator_list'])
            m_soft_delete_efficacy_indicator = (
                m_dict['soft_delete_efficacy_indicator'])
            m_update_action_plan = m_dict['update_action_plan']
            m_get_action_plan.return_value = self.fake_action_plan
            m_get_efficacy_indicator_list.return_value = [efficacy_indicator]
            action_plan = objects.ActionPlan.get_by_uuid(self.context, uuid)
            action_plan.soft_delete()
            m_get_action_plan.assert_called_once_with(self.context, uuid)
            m_get_efficacy_indicator_list.assert_called_once_with(
                self.context, filters={"action_plan_uuid": uuid},
                limit=None, marker=None, sort_dir=None, sort_key=None)
            m_soft_delete_action_plan.assert_called_once_with(uuid)
            m_soft_delete_efficacy_indicator.assert_called_once_with(
                efficacy_indicator['uuid'])
            m_update_action_plan.assert_called_once_with(
                uuid, {'state': 'DELETED'})
            self.assertEqual(self.context, action_plan._context)

    def test_save(self):
        uuid = self.fake_action_plan['uuid']
        with mock.patch.object(self.dbapi, 'get_action_plan_by_uuid',
                               autospec=True) as mock_get_action_plan:
            mock_get_action_plan.return_value = self.fake_action_plan
            with mock.patch.object(self.dbapi, 'update_action_plan',
                                   autospec=True) as mock_update_action_plan:
                action_plan = objects.ActionPlan.get_by_uuid(
                    self.context, uuid)
                action_plan.state = 'SUCCEEDED'
                action_plan.save()

                mock_get_action_plan.assert_called_once_with(
                    self.context, uuid)
                mock_update_action_plan.assert_called_once_with(
                    uuid, {'state': 'SUCCEEDED'})
                self.assertEqual(self.context, action_plan._context)

    def test_refresh(self):
        uuid = self.fake_action_plan['uuid']
        returns = [dict(self.fake_action_plan, state="first state"),
                   dict(self.fake_action_plan, state="second state")]
        expected = [mock.call(self.context, uuid),
                    mock.call(self.context, uuid)]
        with mock.patch.object(self.dbapi, 'get_action_plan_by_uuid',
                               side_effect=returns,
                               autospec=True) as mock_get_action_plan:
            action_plan = objects.ActionPlan.get(self.context, uuid)
            self.assertEqual("first state", action_plan.state)
            action_plan.refresh()
            self.assertEqual("second state", action_plan.state)
            self.assertEqual(expected, mock_get_action_plan.call_args_list)
            self.assertEqual(self.context, action_plan._context)
