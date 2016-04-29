# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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

from watcher.common import context
from watcher.common import utils
from watcher.decision_engine.strategy.loading import default
from watcher.decision_engine import sync
from watcher import objects
from watcher.tests.db import base
from watcher.tests.decision_engine import fake_strategies


class TestSyncer(base.DbTestCase):

    def setUp(self):
        super(TestSyncer, self).setUp()
        self.ctx = context.make_context()

        self.m_available_strategies = mock.Mock(return_value={
            fake_strategies.FakeDummy1Strategy1.get_name():
                fake_strategies.FakeDummy1Strategy1,
            fake_strategies.FakeDummy1Strategy2.get_name():
                fake_strategies.FakeDummy1Strategy2,
            fake_strategies.FakeDummy2Strategy3.get_name():
                fake_strategies.FakeDummy2Strategy3,
            fake_strategies.FakeDummy2Strategy4.get_name():
                fake_strategies.FakeDummy2Strategy4,
        })

        p_strategies = mock.patch.object(
            default.DefaultStrategyLoader, 'list_available',
            self.m_available_strategies)
        p_strategies.start()

        self.syncer = sync.Syncer()
        self.addCleanup(p_strategies.stop)

    @mock.patch.object(objects.Strategy, "soft_delete")
    @mock.patch.object(objects.Strategy, "save")
    @mock.patch.object(objects.Strategy, "create")
    @mock.patch.object(objects.Strategy, "list")
    @mock.patch.object(objects.Goal, "get_by_name")
    @mock.patch.object(objects.Goal, "soft_delete")
    @mock.patch.object(objects.Goal, "save")
    @mock.patch.object(objects.Goal, "create")
    @mock.patch.object(objects.Goal, "list")
    def test_sync_empty_db(
            self, m_g_list, m_g_create, m_g_save, m_g_soft_delete,
            m_g_get_by_name, m_s_list, m_s_create, m_s_save, m_s_soft_delete):
        m_g_get_by_name.side_effect = [
            objects.Goal(self.ctx, id=i) for i in range(1, 10)]
        m_g_list.return_value = []
        m_s_list.return_value = []

        self.syncer.sync()

        self.assertEqual(2, m_g_create.call_count)
        self.assertEqual(0, m_g_save.call_count)
        self.assertEqual(0, m_g_soft_delete.call_count)

        self.assertEqual(4, m_s_create.call_count)
        self.assertEqual(0, m_s_save.call_count)
        self.assertEqual(0, m_s_soft_delete.call_count)

    @mock.patch.object(objects.Strategy, "soft_delete")
    @mock.patch.object(objects.Strategy, "save")
    @mock.patch.object(objects.Strategy, "create")
    @mock.patch.object(objects.Strategy, "list")
    @mock.patch.object(objects.Goal, "get_by_name")
    @mock.patch.object(objects.Goal, "soft_delete")
    @mock.patch.object(objects.Goal, "save")
    @mock.patch.object(objects.Goal, "create")
    @mock.patch.object(objects.Goal, "list")
    def test_sync_with_existing_goal(
            self, m_g_list, m_g_create, m_g_save, m_g_soft_delete,
            m_g_get_by_name, m_s_list, m_s_create, m_s_save, m_s_soft_delete):
        m_g_get_by_name.side_effect = [
            objects.Goal(self.ctx, id=i) for i in range(1, 10)]
        m_g_list.return_value = [
            objects.Goal(self.ctx, id=1, uuid=utils.generate_uuid(),
                         name="DUMMY_1", display_name="Dummy 1")
        ]
        m_s_list.return_value = []

        self.syncer.sync()

        self.assertEqual(1, m_g_create.call_count)
        self.assertEqual(0, m_g_save.call_count)
        self.assertEqual(0, m_g_soft_delete.call_count)

        self.assertEqual(4, m_s_create.call_count)
        self.assertEqual(0, m_s_save.call_count)
        self.assertEqual(0, m_s_soft_delete.call_count)

    @mock.patch.object(objects.Strategy, "soft_delete")
    @mock.patch.object(objects.Strategy, "save")
    @mock.patch.object(objects.Strategy, "create")
    @mock.patch.object(objects.Strategy, "list")
    @mock.patch.object(objects.Goal, "get_by_name")
    @mock.patch.object(objects.Goal, "soft_delete")
    @mock.patch.object(objects.Goal, "save")
    @mock.patch.object(objects.Goal, "create")
    @mock.patch.object(objects.Goal, "list")
    def test_sync_with_existing_strategy(
            self, m_g_list, m_g_create, m_g_save, m_g_soft_delete,
            m_g_get_by_name, m_s_list, m_s_create, m_s_save, m_s_soft_delete):
        m_g_get_by_name.side_effect = [
            objects.Goal(self.ctx, id=i) for i in range(1, 10)]
        m_g_list.return_value = [
            objects.Goal(self.ctx, id=1, uuid=utils.generate_uuid(),
                         name="DUMMY_1", display_name="Dummy 1")
        ]
        m_s_list.return_value = [
            objects.Strategy(self.ctx, id=1, name="STRATEGY_1",
                             goal_id=1, display_name="Strategy 1")
        ]
        self.syncer.sync()

        self.assertEqual(1, m_g_create.call_count)
        self.assertEqual(0, m_g_save.call_count)
        self.assertEqual(0, m_g_soft_delete.call_count)

        self.assertEqual(3, m_s_create.call_count)
        self.assertEqual(0, m_s_save.call_count)
        self.assertEqual(0, m_s_soft_delete.call_count)

    @mock.patch.object(objects.Strategy, "soft_delete")
    @mock.patch.object(objects.Strategy, "save")
    @mock.patch.object(objects.Strategy, "create")
    @mock.patch.object(objects.Strategy, "list")
    @mock.patch.object(objects.Goal, "get_by_name")
    @mock.patch.object(objects.Goal, "soft_delete")
    @mock.patch.object(objects.Goal, "save")
    @mock.patch.object(objects.Goal, "create")
    @mock.patch.object(objects.Goal, "list")
    def test_sync_with_modified_goal(
            self, m_g_list, m_g_create, m_g_save, m_g_soft_delete,
            m_g_get_by_name, m_s_list, m_s_create, m_s_save, m_s_soft_delete):
        m_g_get_by_name.side_effect = [
            objects.Goal(self.ctx, id=i) for i in range(1, 10)]
        m_g_list.return_value = [
            objects.Goal(self.ctx, id=1, uuid=utils.generate_uuid(),
                         name="DUMMY_2", display_name="original")
        ]
        m_s_list.return_value = []
        self.syncer.sync()

        self.assertEqual(2, m_g_create.call_count)
        self.assertEqual(0, m_g_save.call_count)
        self.assertEqual(1, m_g_soft_delete.call_count)

        self.assertEqual(4, m_s_create.call_count)
        self.assertEqual(0, m_s_save.call_count)
        self.assertEqual(0, m_s_soft_delete.call_count)

    @mock.patch.object(objects.Strategy, "soft_delete")
    @mock.patch.object(objects.Strategy, "save")
    @mock.patch.object(objects.Strategy, "create")
    @mock.patch.object(objects.Strategy, "list")
    @mock.patch.object(objects.Goal, "get_by_name")
    @mock.patch.object(objects.Goal, "soft_delete")
    @mock.patch.object(objects.Goal, "save")
    @mock.patch.object(objects.Goal, "create")
    @mock.patch.object(objects.Goal, "list")
    def test_sync_with_modified_strategy(
            self, m_g_list, m_g_create, m_g_save, m_g_soft_delete,
            m_g_get_by_name, m_s_list, m_s_create, m_s_save, m_s_soft_delete):
        m_g_get_by_name.side_effect = [
            objects.Goal(self.ctx, id=i) for i in range(1, 10)]
        m_g_list.return_value = [
            objects.Goal(self.ctx, id=1, uuid=utils.generate_uuid(),
                         name="DUMMY_1", display_name="Dummy 1")
        ]
        m_s_list.return_value = [
            objects.Strategy(self.ctx, id=1, name="STRATEGY_1",
                             goal_id=1, display_name="original")
        ]
        self.syncer.sync()

        self.assertEqual(1, m_g_create.call_count)
        self.assertEqual(0, m_g_save.call_count)
        self.assertEqual(0, m_g_soft_delete.call_count)

        self.assertEqual(4, m_s_create.call_count)
        self.assertEqual(0, m_s_save.call_count)
        self.assertEqual(1, m_s_soft_delete.call_count)

    def test_end2end_sync_goals_with_modified_goal_and_strategy(self):
        goal = objects.Goal(self.ctx, id=1, uuid=utils.generate_uuid(),
                            name="DUMMY_1", display_name="Original")
        goal.create()
        strategy = objects.Strategy(
            self.ctx, id=1, name="STRATEGY_1",
            display_name="Original", goal_id=goal.id)
        strategy.create()
        # audit_template = objects.AuditTemplate(
        #     self.ctx, id=1, name="Synced AT", goal_id=goal.id,
        #     strategy_id=strategy.id)
        # audit_template.create()

        # before_audit_templates = objects.AuditTemplate.list(self.ctx)
        before_goals = objects.Goal.list(self.ctx)
        before_strategies = objects.Strategy.list(self.ctx)

        try:
            self.syncer.sync()
        except Exception as exc:
            self.fail(exc)

        # after_audit_templates = objects.AuditTemplate.list(self.ctx)
        after_goals = objects.Goal.list(self.ctx)
        after_strategies = objects.Strategy.list(self.ctx)

        self.assertEqual(1, len(before_goals))
        self.assertEqual(1, len(before_strategies))
        # self.assertEqual(1, len(before_audit_templates))
        self.assertEqual(2, len(after_goals))
        self.assertEqual(4, len(after_strategies))
        # self.assertEqual(1, len(after_audit_templates))
        self.assertEqual(
            {"DUMMY_1", "DUMMY_2"},
            set([g.name for g in after_goals]))
        self.assertEqual(
            {"STRATEGY_1", "STRATEGY_2", "STRATEGY_3", "STRATEGY_4"},
            set([s.name for s in after_strategies]))
        created_goals = [ag for ag in after_goals
                         if ag.uuid not in [bg.uuid for bg in before_goals]]
        created_strategies = [
            a_s for a_s in after_strategies
            if a_s.uuid not in [b_s.uuid for b_s in before_strategies]]

        self.assertEqual(2, len(created_goals))
        self.assertEqual(4, len(created_strategies))

        # synced_audit_template = after_audit_templates[0]
        # self.assertTrue(
        #     audit_template.goal_id != synced_audit_template.goal_id)
        # self.assertIn(synced_audit_template.goal_id,
        #               (g.id for g in after_goals))
