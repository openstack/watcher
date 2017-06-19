# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from oslo_utils import uuidutils

import freezegun
import mock

from watcher.common import context as watcher_context
from watcher.common import utils
from watcher.db import purge
from watcher.db.sqlalchemy import api as dbapi
from watcher.tests.db import base
from watcher.tests.objects import utils as obj_utils


class TestPurgeCommand(base.DbTestCase):

    def setUp(self):
        super(TestPurgeCommand, self).setUp()
        self.cmd = purge.PurgeCommand()
        token_info = {
            'token': {
                'project': {
                    'id': 'fake_project'
                },
                'user': {
                    'id': 'fake_user'
                }
            }
        }
        self.context = watcher_context.RequestContext(
            auth_token_info=token_info,
            project_id='fake_project',
            user_id='fake_user',
            show_deleted=True,
        )

        self.fake_today = '2016-02-24T09:52:05.219414+00:00'
        self.expired_date = '2016-01-24T09:52:05.219414+00:00'

        self.m_input = mock.Mock()
        p = mock.patch("watcher.db.purge.input", self.m_input)
        self.m_input.return_value = 'y'
        p.start()
        self.addCleanup(p.stop)

        self._id_generator = None
        self._data_setup()

    def _generate_id(self):
        if self._id_generator is None:
            self._id_generator = self._get_id_generator()
        return next(self._id_generator)

    def _get_id_generator(self):
        seed = 1
        while True:
            yield seed
            seed += 1

    def generate_unique_name(self, prefix):
        return "%s%s" % (prefix, uuidutils.generate_uuid())

    def _data_setup(self):
        # All the 1's are soft_deleted and are expired
        # All the 2's are soft_deleted but are not expired
        # All the 3's are *not* soft_deleted

        # Number of days we want to keep in DB (no purge for them)
        self.cmd.age_in_days = 10
        self.cmd.max_number = None
        self.cmd.orphans = True

        goal1_name = "GOAL_1"
        goal2_name = "GOAL_2"
        goal3_name = "GOAL_3"

        strategy1_name = "strategy_1"
        strategy2_name = "strategy_2"
        strategy3_name = "strategy_3"

        self.audit_template1_name = self.generate_unique_name(
            prefix="Audit Template 1 ")
        self.audit_template2_name = self.generate_unique_name(
            prefix="Audit Template 2 ")
        self.audit_template3_name = self.generate_unique_name(
            prefix="Audit Template 3 ")

        self.audit1_name = self.generate_unique_name(
            prefix="Audit 1 ")
        self.audit2_name = self.generate_unique_name(
            prefix="Audit 2 ")
        self.audit3_name = self.generate_unique_name(
            prefix="Audit 3 ")

        with freezegun.freeze_time(self.expired_date):
            self.goal1 = obj_utils.create_test_goal(
                self.context, id=self._generate_id(),
                uuid=utils.generate_uuid(),
                name=goal1_name, display_name=goal1_name.lower())
            self.goal2 = obj_utils.create_test_goal(
                self.context, id=self._generate_id(),
                uuid=utils.generate_uuid(),
                name=goal2_name, display_name=goal2_name.lower())
            self.goal3 = obj_utils.create_test_goal(
                self.context, id=self._generate_id(),
                uuid=utils.generate_uuid(),
                name=goal3_name, display_name=goal3_name.lower())
            self.goal1.soft_delete()

        with freezegun.freeze_time(self.expired_date):
            self.strategy1 = obj_utils.create_test_strategy(
                self.context, id=self._generate_id(),
                uuid=utils.generate_uuid(),
                name=strategy1_name, display_name=strategy1_name.lower(),
                goal_id=self.goal1.id)
            self.strategy2 = obj_utils.create_test_strategy(
                self.context, id=self._generate_id(),
                uuid=utils.generate_uuid(),
                name=strategy2_name, display_name=strategy2_name.lower(),
                goal_id=self.goal2.id)
            self.strategy3 = obj_utils.create_test_strategy(
                self.context, id=self._generate_id(),
                uuid=utils.generate_uuid(),
                name=strategy3_name, display_name=strategy3_name.lower(),
                goal_id=self.goal3.id)
            self.strategy1.soft_delete()

        with freezegun.freeze_time(self.expired_date):
            self.audit_template1 = obj_utils.create_test_audit_template(
                self.context, name=self.audit_template1_name,
                id=self._generate_id(),
                uuid=utils.generate_uuid(), goal_id=self.goal1.id,
                strategy_id=self.strategy1.id)
            self.audit_template2 = obj_utils.create_test_audit_template(
                self.context, name=self.audit_template2_name,
                id=self._generate_id(),
                uuid=utils.generate_uuid(), goal_id=self.goal2.id,
                strategy_id=self.strategy2.id)
            self.audit_template3 = obj_utils.create_test_audit_template(
                self.context, name=self.audit_template3_name,
                id=self._generate_id(),
                uuid=utils.generate_uuid(), goal_id=self.goal3.id,
                strategy_id=self.strategy3.id)
            self.audit_template1.soft_delete()

        with freezegun.freeze_time(self.expired_date):
            self.audit1 = obj_utils.create_test_audit(
                self.context, id=self._generate_id(),
                uuid=utils.generate_uuid(), name=self.audit1_name,
                goal_id=self.goal1.id, strategy_id=self.strategy1.id)
            self.audit2 = obj_utils.create_test_audit(
                self.context, id=self._generate_id(),
                uuid=utils.generate_uuid(), name=self.audit2_name,
                goal_id=self.goal2.id, strategy_id=self.strategy2.id)
            self.audit3 = obj_utils.create_test_audit(
                self.context, id=self._generate_id(),
                uuid=utils.generate_uuid(), name=self.audit3_name,
                goal_id=self.goal3.id, strategy_id=self.strategy3.id)
            self.audit1.soft_delete()

        with freezegun.freeze_time(self.expired_date):
            self.action_plan1 = obj_utils.create_test_action_plan(
                self.context, audit_id=self.audit1.id,
                id=self._generate_id(), uuid=utils.generate_uuid(),
                strategy_id=self.strategy1.id)
            self.action_plan2 = obj_utils.create_test_action_plan(
                self.context, audit_id=self.audit2.id,
                id=self._generate_id(),
                strategy_id=self.strategy2.id,
                uuid=utils.generate_uuid())
            self.action_plan3 = obj_utils.create_test_action_plan(
                self.context, audit_id=self.audit3.id,
                id=self._generate_id(), uuid=utils.generate_uuid(),
                strategy_id=self.strategy3.id)

            self.action1 = obj_utils.create_test_action(
                self.context, action_plan_id=self.action_plan1.id,
                id=self._generate_id(),
                uuid=utils.generate_uuid())
            self.action2 = obj_utils.create_test_action(
                self.context, action_plan_id=self.action_plan2.id,
                id=self._generate_id(), uuid=utils.generate_uuid())
            self.action3 = obj_utils.create_test_action(
                self.context, action_plan_id=self.action_plan3.id,
                id=self._generate_id(), uuid=utils.generate_uuid())
            self.action_plan1.soft_delete()

    @mock.patch.object(dbapi.Connection, "destroy_action")
    @mock.patch.object(dbapi.Connection, "destroy_action_plan")
    @mock.patch.object(dbapi.Connection, "destroy_audit")
    @mock.patch.object(dbapi.Connection, "destroy_audit_template")
    @mock.patch.object(dbapi.Connection, "destroy_strategy")
    @mock.patch.object(dbapi.Connection, "destroy_goal")
    def test_execute_max_number_exceeded(self,
                                         m_destroy_goal,
                                         m_destroy_strategy,
                                         m_destroy_audit_template,
                                         m_destroy_audit,
                                         m_destroy_action_plan,
                                         m_destroy_action):
        self.cmd.age_in_days = None
        self.cmd.max_number = 10

        with freezegun.freeze_time(self.fake_today):
            self.goal2.soft_delete()
            self.strategy2.soft_delete()
            self.audit_template2.soft_delete()
            self.audit2.soft_delete()
            self.action_plan2.soft_delete()

        with freezegun.freeze_time(self.fake_today):
            self.cmd.execute()

        # The 1's and the 2's are purgeable (due to age of day set to 0),
        # but max_number = 10, and because of no Db integrity violation, we
        # should be able to purge only 6 objects.
        self.assertEqual(m_destroy_goal.call_count, 1)
        self.assertEqual(m_destroy_strategy.call_count, 1)
        self.assertEqual(m_destroy_audit_template.call_count, 1)
        self.assertEqual(m_destroy_audit.call_count, 1)
        self.assertEqual(m_destroy_action_plan.call_count, 1)
        self.assertEqual(m_destroy_action.call_count, 1)

    def test_find_deleted_entries(self):
        self.cmd.age_in_days = None

        with freezegun.freeze_time(self.fake_today):
            objects_map = self.cmd.find_objects_to_delete()

        self.assertEqual(len(objects_map.goals), 1)
        self.assertEqual(len(objects_map.strategies), 1)
        self.assertEqual(len(objects_map.audit_templates), 1)
        self.assertEqual(len(objects_map.audits), 1)
        self.assertEqual(len(objects_map.action_plans), 1)
        self.assertEqual(len(objects_map.actions), 1)

    def test_find_deleted_and_expired_entries(self):
        with freezegun.freeze_time(self.fake_today):
            self.goal2.soft_delete()
            self.strategy2.soft_delete()
            self.audit_template2.soft_delete()
            self.audit2.soft_delete()
            self.action_plan2.soft_delete()

        with freezegun.freeze_time(self.fake_today):
            objects_map = self.cmd.find_objects_to_delete()

        # The 1's are purgeable (due to age of day set to 10)
        self.assertEqual(len(objects_map.goals), 1)
        self.assertEqual(len(objects_map.strategies), 1)
        self.assertEqual(len(objects_map.audit_templates), 1)
        self.assertEqual(len(objects_map.audits), 1)
        self.assertEqual(len(objects_map.action_plans), 1)
        self.assertEqual(len(objects_map.actions), 1)

    def test_find_deleted_and_nonexpired_related_entries(self):
        with freezegun.freeze_time(self.fake_today):
            # orphan audit template
            audit_template4 = obj_utils.create_test_audit_template(
                self.context, goal_id=self.goal2.id,
                name=self.generate_unique_name(prefix="Audit Template 4 "),
                strategy_id=self.strategy1.id, id=self._generate_id(),
                uuid=utils.generate_uuid())
            audit4 = obj_utils.create_test_audit(
                self.context, audit_template_id=audit_template4.id,
                strategy_id=self.strategy1.id, id=self._generate_id(),
                uuid=utils.generate_uuid(),
                name=self.generate_unique_name(prefix="Audit 4 "))
            action_plan4 = obj_utils.create_test_action_plan(
                self.context,
                id=self._generate_id(), uuid=utils.generate_uuid(),
                audit_id=audit4.id, strategy_id=self.strategy1.id)
            action4 = obj_utils.create_test_action(
                self.context, action_plan_id=action_plan4.id,
                id=self._generate_id(),
                uuid=utils.generate_uuid())

            audit_template5 = obj_utils.create_test_audit_template(
                self.context, goal_id=self.goal1.id,
                name=self.generate_unique_name(prefix="Audit Template 5 "),
                strategy_id=None, id=self._generate_id(),
                uuid=utils.generate_uuid())
            audit5 = obj_utils.create_test_audit(
                self.context, audit_template_id=audit_template5.id,
                strategy_id=self.strategy1.id, id=self._generate_id(),
                uuid=utils.generate_uuid(),
                name=self.generate_unique_name(prefix="Audit 5 "))
            action_plan5 = obj_utils.create_test_action_plan(
                self.context,
                id=self._generate_id(), uuid=utils.generate_uuid(),
                audit_id=audit5.id, strategy_id=self.strategy1.id)
            action5 = obj_utils.create_test_action(
                self.context, action_plan_id=action_plan5.id,
                id=self._generate_id(),
                uuid=utils.generate_uuid())

            self.goal2.soft_delete()
            self.strategy2.soft_delete()
            self.audit_template2.soft_delete()
            self.audit2.soft_delete()
            self.action_plan2.soft_delete()

            # All the 4's should be purged as well because they are orphans
            # even though they were not deleted

            # All the 5's should be purged as well even though they are not
            # expired because their related audit template is itself expired
            audit_template5.soft_delete()
            audit5.soft_delete()
            action_plan5.soft_delete()

        with freezegun.freeze_time(self.fake_today):
            objects_map = self.cmd.find_objects_to_delete()

        self.assertEqual(len(objects_map.goals), 1)
        self.assertEqual(len(objects_map.strategies), 1)
        self.assertEqual(len(objects_map.audit_templates), 3)
        self.assertEqual(len(objects_map.audits), 3)
        self.assertEqual(len(objects_map.action_plans), 3)
        self.assertEqual(len(objects_map.actions), 3)
        self.assertEqual(
            set([self.action1.id, action4.id, action5.id]),
            set([entry.id for entry in objects_map.actions]))

    @mock.patch.object(dbapi.Connection, "destroy_action")
    @mock.patch.object(dbapi.Connection, "destroy_action_plan")
    @mock.patch.object(dbapi.Connection, "destroy_audit")
    @mock.patch.object(dbapi.Connection, "destroy_audit_template")
    @mock.patch.object(dbapi.Connection, "destroy_strategy")
    @mock.patch.object(dbapi.Connection, "destroy_goal")
    def test_purge_command(self, m_destroy_goal, m_destroy_strategy,
                           m_destroy_audit_template, m_destroy_audit,
                           m_destroy_action_plan, m_destroy_action):
        with freezegun.freeze_time(self.fake_today):
            self.cmd.execute()

        m_destroy_audit_template.assert_called_once_with(
            self.audit_template1.uuid)
        m_destroy_audit.assert_called_with(
            self.audit1.uuid)
        m_destroy_action_plan.assert_called_with(
            self.action_plan1.uuid)
        m_destroy_action.assert_called_with(
            self.action1.uuid)

    @mock.patch.object(dbapi.Connection, "destroy_action")
    @mock.patch.object(dbapi.Connection, "destroy_action_plan")
    @mock.patch.object(dbapi.Connection, "destroy_audit")
    @mock.patch.object(dbapi.Connection, "destroy_audit_template")
    @mock.patch.object(dbapi.Connection, "destroy_strategy")
    @mock.patch.object(dbapi.Connection, "destroy_goal")
    def test_purge_command_with_nonexpired_related_entries(
            self, m_destroy_goal, m_destroy_strategy,
            m_destroy_audit_template, m_destroy_audit,
            m_destroy_action_plan, m_destroy_action):
        with freezegun.freeze_time(self.fake_today):
            # orphan audit template
            audit_template4 = obj_utils.create_test_audit_template(
                self.context, goal_id=self.goal2.id,
                name=self.generate_unique_name(prefix="Audit Template 4 "),
                strategy_id=None, id=self._generate_id(),
                uuid=utils.generate_uuid())
            audit4 = obj_utils.create_test_audit(
                self.context,
                id=self._generate_id(), uuid=utils.generate_uuid(),
                audit_template_id=audit_template4.id,
                name=self.generate_unique_name(prefix="Audit 4 "))
            action_plan4 = obj_utils.create_test_action_plan(
                self.context,
                id=self._generate_id(), uuid=utils.generate_uuid(),
                audit_id=audit4.id, strategy_id=self.strategy1.id)
            action4 = obj_utils.create_test_action(
                self.context, action_plan_id=action_plan4.id,
                id=self._generate_id(),
                uuid=utils.generate_uuid())

            audit_template5 = obj_utils.create_test_audit_template(
                self.context, goal_id=self.goal1.id,
                name=self.generate_unique_name(prefix="Audit Template 5 "),
                strategy_id=None, id=self._generate_id(),
                uuid=utils.generate_uuid())
            audit5 = obj_utils.create_test_audit(
                self.context, audit_template_id=audit_template5.id,
                strategy_id=self.strategy1.id, id=self._generate_id(),
                uuid=utils.generate_uuid(),
                name=self.generate_unique_name(prefix="Audit 5 "))
            action_plan5 = obj_utils.create_test_action_plan(
                self.context,
                id=self._generate_id(), uuid=utils.generate_uuid(),
                audit_id=audit5.id, strategy_id=self.strategy1.id)
            action5 = obj_utils.create_test_action(
                self.context, action_plan_id=action_plan5.id,
                id=self._generate_id(),
                uuid=utils.generate_uuid())

            self.goal2.soft_delete()
            self.strategy2.soft_delete()
            self.audit_template2.soft_delete()
            self.audit2.soft_delete()
            self.action_plan2.soft_delete()

            # All the 4's should be purged as well because they are orphans
            # even though they were not deleted

            # All the 5's should be purged as well even though they are not
            # expired because their related audit template is itself expired
            audit_template5.soft_delete()
            audit5.soft_delete()
            action_plan5.soft_delete()

        with freezegun.freeze_time(self.fake_today):
            self.cmd.execute()

        self.assertEqual(m_destroy_goal.call_count, 1)
        self.assertEqual(m_destroy_strategy.call_count, 1)
        self.assertEqual(m_destroy_audit_template.call_count, 3)
        self.assertEqual(m_destroy_audit.call_count, 3)
        self.assertEqual(m_destroy_action_plan.call_count, 3)
        self.assertEqual(m_destroy_action.call_count, 3)

        m_destroy_audit_template.assert_any_call(self.audit_template1.uuid)
        m_destroy_audit.assert_any_call(self.audit1.uuid)
        m_destroy_audit.assert_any_call(audit4.uuid)
        m_destroy_action_plan.assert_any_call(self.action_plan1.uuid)
        m_destroy_action_plan.assert_any_call(action_plan4.uuid)
        m_destroy_action_plan.assert_any_call(action_plan5.uuid)
        m_destroy_action.assert_any_call(self.action1.uuid)
        m_destroy_action.assert_any_call(action4.uuid)
        m_destroy_action.assert_any_call(action5.uuid)

    @mock.patch.object(dbapi.Connection, "destroy_action")
    @mock.patch.object(dbapi.Connection, "destroy_action_plan")
    @mock.patch.object(dbapi.Connection, "destroy_audit")
    @mock.patch.object(dbapi.Connection, "destroy_audit_template")
    @mock.patch.object(dbapi.Connection, "destroy_strategy")
    @mock.patch.object(dbapi.Connection, "destroy_goal")
    def test_purge_command_with_strategy_uuid(
            self, m_destroy_goal, m_destroy_strategy,
            m_destroy_audit_template, m_destroy_audit,
            m_destroy_action_plan, m_destroy_action):
        self.cmd.exclude_orphans = False
        self.cmd.uuid = self.strategy1.uuid

        with freezegun.freeze_time(self.fake_today):
            self.cmd.execute()

        self.assertEqual(m_destroy_goal.call_count, 0)
        self.assertEqual(m_destroy_strategy.call_count, 1)
        self.assertEqual(m_destroy_audit_template.call_count, 1)
        self.assertEqual(m_destroy_audit.call_count, 1)
        self.assertEqual(m_destroy_action_plan.call_count, 1)
        self.assertEqual(m_destroy_action.call_count, 1)

    @mock.patch.object(dbapi.Connection, "destroy_action")
    @mock.patch.object(dbapi.Connection, "destroy_action_plan")
    @mock.patch.object(dbapi.Connection, "destroy_audit")
    @mock.patch.object(dbapi.Connection, "destroy_audit_template")
    @mock.patch.object(dbapi.Connection, "destroy_strategy")
    @mock.patch.object(dbapi.Connection, "destroy_goal")
    def test_purge_command_with_audit_template_not_expired(
            self, m_destroy_goal, m_destroy_strategy,
            m_destroy_audit_template, m_destroy_audit,
            m_destroy_action_plan, m_destroy_action):
        self.cmd.exclude_orphans = True
        self.cmd.uuid = self.audit_template2.uuid

        with freezegun.freeze_time(self.fake_today):
            self.cmd.execute()

        self.assertEqual(m_destroy_goal.call_count, 0)
        self.assertEqual(m_destroy_strategy.call_count, 0)
        self.assertEqual(m_destroy_audit_template.call_count, 0)
        self.assertEqual(m_destroy_audit.call_count, 0)
        self.assertEqual(m_destroy_action_plan.call_count, 0)
        self.assertEqual(m_destroy_action.call_count, 0)

    @mock.patch.object(dbapi.Connection, "destroy_action")
    @mock.patch.object(dbapi.Connection, "destroy_action_plan")
    @mock.patch.object(dbapi.Connection, "destroy_audit")
    @mock.patch.object(dbapi.Connection, "destroy_audit_template")
    @mock.patch.object(dbapi.Connection, "destroy_strategy")
    @mock.patch.object(dbapi.Connection, "destroy_goal")
    def test_purge_command_with_audit_template_not_soft_deleted(
            self, m_destroy_goal, m_destroy_strategy,
            m_destroy_audit_template, m_destroy_audit,
            m_destroy_action_plan, m_destroy_action):
        self.cmd.exclude_orphans = False
        self.cmd.uuid = self.audit_template3.uuid

        with freezegun.freeze_time(self.fake_today):
            self.cmd.execute()

        self.assertEqual(m_destroy_goal.call_count, 0)
        self.assertEqual(m_destroy_strategy.call_count, 0)
        self.assertEqual(m_destroy_audit_template.call_count, 0)
        self.assertEqual(m_destroy_audit.call_count, 0)
        self.assertEqual(m_destroy_action_plan.call_count, 0)
        self.assertEqual(m_destroy_action.call_count, 0)
