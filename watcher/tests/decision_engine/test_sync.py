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
from watcher.decision_engine.loading import default
from watcher.decision_engine import sync
from watcher import objects
from watcher.tests.db import base
from watcher.tests.decision_engine import fake_goals
from watcher.tests.decision_engine import fake_strategies


class TestSyncer(base.DbTestCase):

    def setUp(self):
        super(TestSyncer, self).setUp()
        self.ctx = context.make_context()

        # This mock simulates the strategies discovery done in discover()
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

        self.m_available_goals = mock.Mock(return_value={
            fake_goals.FakeDummy1.get_name(): fake_goals.FakeDummy1,
            fake_goals.FakeDummy2.get_name(): fake_goals.FakeDummy2,
        })

        self.goal1_spec = fake_goals.FakeDummy1(
            config=mock.Mock()).get_efficacy_specification()
        self.goal2_spec = fake_goals.FakeDummy2(
            config=mock.Mock()).get_efficacy_specification()

        p_goals_load = mock.patch.object(
            default.DefaultGoalLoader, 'load',
            side_effect=lambda goal: self.m_available_goals()[goal]())
        p_goals = mock.patch.object(
            default.DefaultGoalLoader, 'list_available',
            self.m_available_goals)
        p_strategies = mock.patch.object(
            default.DefaultStrategyLoader, 'list_available',
            self.m_available_strategies)

        p_goals.start()
        p_goals_load.start()
        p_strategies.start()

        self.syncer = sync.Syncer()
        self.addCleanup(p_goals.stop)
        self.addCleanup(p_goals_load.stop)
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
                         name="dummy_1", display_name="Dummy 1",
                         efficacy_specification=(
                             self.goal1_spec.serialize_indicators_specs()))
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
                         name="dummy_1", display_name="Dummy 1",
                         efficacy_specification=(
                             self.goal1_spec.serialize_indicators_specs()))
        ]
        m_s_list.return_value = [
            objects.Strategy(self.ctx, id=1, name="strategy_1",
                             goal_id=1, display_name="Strategy 1",
                             parameters_spec='{}')
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
        m_g_list.return_value = [objects.Goal(
            self.ctx, id=1, uuid=utils.generate_uuid(),
            name="dummy_2", display_name="original",
            efficacy_specification=self.goal2_spec.serialize_indicators_specs()
        )]
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
                         name="dummy_1", display_name="Dummy 1",
                         efficacy_specification=(
                             self.goal1_spec.serialize_indicators_specs()))
        ]
        m_s_list.return_value = [
            objects.Strategy(self.ctx, id=1, name="strategy_1",
                             goal_id=1, display_name="original",
                             parameters_spec='{}')
        ]
        self.syncer.sync()

        self.assertEqual(1, m_g_create.call_count)
        self.assertEqual(0, m_g_save.call_count)
        self.assertEqual(0, m_g_soft_delete.call_count)

        self.assertEqual(4, m_s_create.call_count)
        self.assertEqual(0, m_s_save.call_count)
        self.assertEqual(1, m_s_soft_delete.call_count)

    def test_end2end_sync_goals_with_modified_goal_and_strategy(self):
        # ### Setup ### #

        # Here, we simulate goals and strategies already discovered in the past
        # that were saved in DB

        # Should stay unmodified after sync()
        goal1 = objects.Goal(
            self.ctx, id=1, uuid=utils.generate_uuid(),
            name="dummy_1", display_name="Dummy 1",
            efficacy_specification=(
                self.goal1_spec.serialize_indicators_specs()))
        # Should be modified by the sync()
        goal2 = objects.Goal(
            self.ctx, id=2, uuid=utils.generate_uuid(),
            name="dummy_2", display_name="Original",
            efficacy_specification=self.goal2_spec.serialize_indicators_specs()
        )
        goal1.create()
        goal2.create()

        # Should stay unmodified after sync()
        strategy1 = objects.Strategy(
            self.ctx, id=1, name="strategy_1", uuid=utils.generate_uuid(),
            display_name="Strategy 1", goal_id=goal1.id)
        # Should stay unmodified after sync()
        strategy2 = objects.Strategy(
            self.ctx, id=2, name="strategy_2", uuid=utils.generate_uuid(),
            display_name="Strategy 2", goal_id=goal2.id)
        # Should be modified by the sync()
        strategy3 = objects.Strategy(
            self.ctx, id=3, name="strategy_3", uuid=utils.generate_uuid(),
            display_name="Original", goal_id=goal2.id)
        # Should be modified by the sync()
        strategy4 = objects.Strategy(
            self.ctx, id=4, name="strategy_4", uuid=utils.generate_uuid(),
            display_name="Original", goal_id=goal2.id)
        strategy1.create()
        strategy2.create()
        strategy3.create()
        strategy4.create()

        # Here we simulate audit_templates that were already created in the
        # past and hence saved within the Watcher DB

        # Should stay unmodified after sync()
        audit_template1 = objects.AuditTemplate(
            self.ctx, id=1, uuid=utils.generate_uuid(),
            name="Synced AT1", goal_id=goal1.id, strategy_id=strategy1.id)
        # Should be modified by the sync() because its associated goal
        # should be modified
        audit_template2 = objects.AuditTemplate(
            self.ctx, id=2, name="Synced AT2", uuid=utils.generate_uuid(),
            goal_id=goal2.id, strategy_id=strategy2.id)
        # Should be modified by the sync() because its associated strategy
        # should be modified
        audit_template3 = objects.AuditTemplate(
            self.ctx, id=3, name="Synced AT3", uuid=utils.generate_uuid(),
            goal_id=goal2.id, strategy_id=strategy3.id)
        # Modified because of both because its associated goal and associated
        # strategy should be modified
        audit_template4 = objects.AuditTemplate(
            self.ctx, id=4, name="Synced AT4", uuid=utils.generate_uuid(),
            goal_id=goal2.id, strategy_id=strategy4.id)
        audit_template1.create()
        audit_template2.create()
        audit_template3.create()
        audit_template4.create()

        before_audit_templates = objects.AuditTemplate.list(self.ctx)
        before_goals = objects.Goal.list(self.ctx)
        before_strategies = objects.Strategy.list(self.ctx)

        # ### Action under test ### #

        try:
            self.syncer.sync()
        except Exception as exc:
            self.fail(exc)

        # ### Assertions ### #

        after_audit_templates = objects.AuditTemplate.list(self.ctx)
        after_goals = objects.Goal.list(self.ctx)
        after_strategies = objects.Strategy.list(self.ctx)

        self.assertEqual(2, len(before_goals))
        self.assertEqual(4, len(before_strategies))
        self.assertEqual(4, len(before_audit_templates))
        self.assertEqual(2, len(after_goals))
        self.assertEqual(4, len(after_strategies))
        self.assertEqual(4, len(after_audit_templates))
        self.assertEqual(
            {"dummy_1", "dummy_2"},
            set([g.name for g in after_goals]))
        self.assertEqual(
            {"strategy_1", "strategy_2", "strategy_3", "strategy_4"},
            set([s.name for s in after_strategies]))
        created_goals = {
            ag.name: ag for ag in after_goals
            if ag.uuid not in [bg.uuid for bg in before_goals]
        }
        created_strategies = {
            a_s.name: a_s for a_s in after_strategies
            if a_s.uuid not in [b_s.uuid for b_s in before_strategies]
        }

        dummy_1_spec = [
            {'description': 'Dummy indicator', 'name': 'dummy',
             'schema': 'Range(min=0, max=100, min_included=True, '
                       'max_included=True, msg=None)',
             'unit': '%'}]
        dummy_2_spec = []
        self.assertEqual(
            [dummy_1_spec, dummy_2_spec],
            [g.efficacy_specification for g in after_goals])

        self.assertEqual(1, len(created_goals))
        self.assertEqual(3, len(created_strategies))

        modified_audit_templates = {
            a_at.id for a_at in after_audit_templates
            if a_at.goal_id not in (
                # initial goal IDs
                b_at.goal_id for b_at in before_audit_templates) or
            a_at.strategy_id not in (
                # initial strategy IDs
                b_at.strategy_id for b_at in before_audit_templates
                if b_at.strategy_id is not None)
        }

        unmodified_audit_templates = {
            a_at.id for a_at in after_audit_templates
            if a_at.goal_id in (
                # initial goal IDs
                b_at.goal_id for b_at in before_audit_templates) and
            a_at.strategy_id in (
                # initial strategy IDs
                b_at.strategy_id for b_at in before_audit_templates
                if b_at.strategy_id is not None)
        }

        self.assertEqual(2, strategy2.goal_id)
        self.assertIn(strategy2.name, created_strategies)
        self.assertTrue(strategy2.id != created_strategies[strategy2.name].id)

        self.assertEqual(set([audit_template2.id,
                              audit_template3.id,
                              audit_template4.id]),
                         modified_audit_templates)
        self.assertEqual(set([audit_template1.id]),
                         unmodified_audit_templates)

    def test_end2end_sync_goals_with_removed_goal_and_strategy(self):
        # ### Setup ### #

        # We simulate the fact that we removed 2 strategies
        self.m_available_strategies.return_value = {
            fake_strategies.FakeDummy1Strategy1.get_name():
                fake_strategies.FakeDummy1Strategy1
        }
        # We simulate the fact that we removed the dummy_2 goal
        self.m_available_goals.return_value = {
            fake_goals.FakeDummy1.get_name(): fake_goals.FakeDummy1,
        }
        # Should stay unmodified after sync()
        goal1 = objects.Goal(
            self.ctx, id=1, uuid=utils.generate_uuid(),
            name="dummy_1", display_name="Dummy 1",
            efficacy_specification=self.goal1_spec.serialize_indicators_specs()
        )
        # To be removed by the sync()
        goal2 = objects.Goal(
            self.ctx, id=2, uuid=utils.generate_uuid(),
            name="dummy_2", display_name="Dummy 2",
            efficacy_specification=self.goal2_spec.serialize_indicators_specs()
        )
        goal1.create()
        goal2.create()

        # Should stay unmodified after sync()
        strategy1 = objects.Strategy(
            self.ctx, id=1, name="strategy_1", uuid=utils.generate_uuid(),
            display_name="Strategy 1", goal_id=goal1.id)
        # To be removed by the sync()
        strategy2 = objects.Strategy(
            self.ctx, id=2, name="strategy_2", uuid=utils.generate_uuid(),
            display_name="Strategy 2", goal_id=goal1.id)
        # To be removed by the sync()
        strategy3 = objects.Strategy(
            self.ctx, id=3, name="strategy_3", uuid=utils.generate_uuid(),
            display_name="Original", goal_id=goal2.id)
        strategy1.create()
        strategy2.create()
        strategy3.create()

        # Here we simulate audit_templates that were already created in the
        # past and hence saved within the Watcher DB

        # The strategy of this audit template will be dereferenced
        # as it does not exist anymore
        audit_template1 = objects.AuditTemplate(
            self.ctx, id=1, uuid=utils.generate_uuid(),
            name="Synced AT1", goal_id=goal1.id, strategy_id=strategy1.id)
        # Stale even after syncing because the goal has been soft deleted
        audit_template2 = objects.AuditTemplate(
            self.ctx, id=2, name="Synced AT2", uuid=utils.generate_uuid(),
            goal_id=goal2.id, strategy_id=strategy2.id)

        audit_template1.create()
        audit_template2.create()

        before_audit_templates = objects.AuditTemplate.list(self.ctx)
        before_goals = objects.Goal.list(self.ctx)
        before_strategies = objects.Strategy.list(self.ctx)

        # ### Action under test ### #

        try:
            self.syncer.sync()
        except Exception as exc:
            self.fail(exc)

        # ### Assertions ### #

        after_audit_templates = objects.AuditTemplate.list(self.ctx)
        after_goals = objects.Goal.list(self.ctx)
        after_strategies = objects.Strategy.list(self.ctx)

        self.assertEqual(2, len(before_goals))
        self.assertEqual(3, len(before_strategies))
        self.assertEqual(2, len(before_audit_templates))
        self.assertEqual(1, len(after_goals))
        self.assertEqual(1, len(after_strategies))
        self.assertEqual(2, len(after_audit_templates))
        self.assertEqual(
            {"dummy_1"},
            set([g.name for g in after_goals]))
        self.assertEqual(
            {"strategy_1"},
            set([s.name for s in after_strategies]))
        created_goals = [ag for ag in after_goals
                         if ag.uuid not in [bg.uuid for bg in before_goals]]
        created_strategies = [
            a_s for a_s in after_strategies
            if a_s.uuid not in [b_s.uuid for b_s in before_strategies]]

        self.assertEqual(0, len(created_goals))
        self.assertEqual(0, len(created_strategies))

        modified_audit_templates = {
            a_at.id for a_at in after_audit_templates
            if a_at.goal_id not in (
                # initial goal IDs
                b_at.goal_id for b_at in before_audit_templates) or
            a_at.strategy_id not in (
                # initial strategy IDs
                b_at.strategy_id for b_at in before_audit_templates
                if b_at.strategy_id is not None)
        }

        unmodified_audit_templates = {
            a_at.id for a_at in after_audit_templates
            if a_at.goal_id in (
                # initial goal IDs
                b_at.goal_id for b_at in before_audit_templates) and
            a_at.strategy_id in (
                # initial strategy IDs
                b_at.strategy_id for b_at in before_audit_templates
                if b_at.strategy_id is not None)
        }

        self.assertEqual(set([audit_template2.id]),
                         modified_audit_templates)
        self.assertEqual(set([audit_template1.id]),
                         unmodified_audit_templates)
