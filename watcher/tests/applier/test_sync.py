# -*- encoding: utf-8 -*-
# Copyright (c) 2018 SBCloud
#
# Authors: Alexander Chadin <aschadin@sbcloud.ru>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
# http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from oslo_config import cfg
from oslo_utils import uuidutils

from watcher.applier import sync
from watcher.decision_engine.strategy.strategies import dummy_strategy
from watcher.tests.db import base as db_base

from watcher import notifications
from watcher import objects
from watcher.tests.objects import utils as obj_utils


class TestCancelOngoingActionPlans(db_base.DbTestCase):

    def setUp(self):
        super(TestCancelOngoingActionPlans, self).setUp()
        p_audit_notifications = mock.patch.object(
            notifications, 'audit', autospec=True)
        self.m_audit_notifications = p_audit_notifications.start()
        self.addCleanup(p_audit_notifications.stop)

        self.goal = obj_utils.create_test_goal(
            self.context, id=1, name=dummy_strategy.DummyStrategy.get_name())
        self.strategy = obj_utils.create_test_strategy(
            self.context, name=dummy_strategy.DummyStrategy.get_name(),
            goal_id=self.goal.id)
        audit_template = obj_utils.create_test_audit_template(
            self.context, strategy_id=self.strategy.id)
        self.audit = obj_utils.create_test_audit(
            self.context,
            id=999,
            name='My Audit 999',
            uuid=uuidutils.generate_uuid(),
            audit_template_id=audit_template.id,
            goal_id=self.goal.id,
            audit_type=objects.audit.AuditType.ONESHOT.value,
            goal=self.goal,
            hostname='hostname1',
            state=objects.audit.State.ONGOING)
        self.actionplan = obj_utils.create_test_action_plan(
            self.context,
            state=objects.action_plan.State.ONGOING,
            audit_id=999,
            hostname='hostname1')
        self.action = obj_utils.create_test_action(
            self.context,
            action_plan_id=1,
            state=objects.action.State.PENDING)
        cfg.CONF.set_override("host", "hostname1")

    @mock.patch.object(objects.action.Action, 'save')
    @mock.patch.object(objects.action_plan.ActionPlan, 'save')
    @mock.patch.object(objects.action.Action, 'list')
    @mock.patch.object(objects.action_plan.ActionPlan, 'list')
    def test_cancel_ongoing_actionplans(self, m_plan_list, m_action_list,
                                        m_plan_save, m_action_save):
        m_plan_list.return_value = [self.actionplan]
        m_action_list.return_value = [self.action]
        syncer = sync.Syncer()

        syncer._cancel_ongoing_actionplans(self.context)
        m_plan_list.assert_called()
        m_action_list.assert_called()
        m_plan_save.assert_called()
        m_action_save.assert_called()
        self.assertEqual(self.action.state, objects.audit.State.CANCELLED)
