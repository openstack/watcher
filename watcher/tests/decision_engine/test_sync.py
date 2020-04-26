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

from unittest import mock

from oslo_serialization import jsonutils

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

    @staticmethod
    def _find_created_modified_unmodified_ids(befores, afters):
        created = {
            a_item.id: a_item for a_item in afters
            if a_item.uuid not in (b_item.uuid for b_item in befores)
        }

        modified = {
            a_item.id: a_item for a_item in afters
            if a_item.as_dict() not in (
                b_items.as_dict() for b_items in befores)
        }

        unmodified = {
            a_item.id: a_item for a_item in afters
            if a_item.as_dict() in (
                b_items.as_dict() for b_items in befores)
        }

        return created, modified, unmodified

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
        # Should be modified after sync() because its related goal has been
        # modified
        strategy2 = objects.Strategy(
            self.ctx, id=2, name="strategy_2", uuid=utils.generate_uuid(),
            display_name="Strategy 2", goal_id=goal2.id)
        # Should be modified after sync() because its strategy name has been
        # modified
        strategy3 = objects.Strategy(
            self.ctx, id=3, name="strategy_3", uuid=utils.generate_uuid(),
            display_name="Original", goal_id=goal1.id)
        # Should be modified after sync() because both its related goal
        # and its strategy name have been modified
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
            self.ctx, id=1, name="Synced AT1", uuid=utils.generate_uuid(),
            goal_id=goal1.id, strategy_id=strategy1.id)
        # Should be modified by the sync() because its associated goal
        # has been modified (compared to the defined fake goals)
        audit_template2 = objects.AuditTemplate(
            self.ctx, id=2, name="Synced AT2", uuid=utils.generate_uuid(),
            goal_id=goal2.id, strategy_id=strategy2.id)
        # Should be modified by the sync() because its associated strategy
        # has been modified (compared to the defined fake strategies)
        audit_template3 = objects.AuditTemplate(
            self.ctx, id=3, name="Synced AT3", uuid=utils.generate_uuid(),
            goal_id=goal1.id, strategy_id=strategy3.id)
        # Modified because of both because its associated goal and associated
        # strategy should be modified
        audit_template4 = objects.AuditTemplate(
            self.ctx, id=4, name="Synced AT4", uuid=utils.generate_uuid(),
            goal_id=goal2.id, strategy_id=strategy4.id)
        audit_template1.create()
        audit_template2.create()
        audit_template3.create()
        audit_template4.create()

        # Should stay unmodified after sync()
        audit1 = objects.Audit(
            self.ctx, id=1, uuid=utils.generate_uuid(), name='audit_1',
            audit_type=objects.audit.AuditType.ONESHOT.value,
            state=objects.audit.State.PENDING,
            goal_id=goal1.id, strategy_id=strategy1.id, auto_trigger=False)
        # Should be modified by the sync() because its associated goal
        # has been modified (compared to the defined fake goals)
        audit2 = objects.Audit(
            self.ctx, id=2, uuid=utils.generate_uuid(), name='audit_2',
            audit_type=objects.audit.AuditType.ONESHOT.value,
            state=objects.audit.State.PENDING,
            goal_id=goal2.id, strategy_id=strategy2.id, auto_trigger=False)
        # Should be modified by the sync() because its associated strategy
        # has been modified (compared to the defined fake strategies)
        audit3 = objects.Audit(
            self.ctx, id=3, uuid=utils.generate_uuid(), name='audit_3',
            audit_type=objects.audit.AuditType.ONESHOT.value,
            state=objects.audit.State.PENDING,
            goal_id=goal1.id, strategy_id=strategy3.id, auto_trigger=False)
        # Modified because of both because its associated goal and associated
        # strategy should be modified (compared to the defined fake
        # goals/strategies)
        audit4 = objects.Audit(
            self.ctx, id=4, uuid=utils.generate_uuid(), name='audit_4',
            audit_type=objects.audit.AuditType.ONESHOT.value,
            state=objects.audit.State.PENDING,
            goal_id=goal2.id, strategy_id=strategy4.id, auto_trigger=False)

        audit1.create()
        audit2.create()
        audit3.create()
        audit4.create()

        # Should stay unmodified after sync()
        action_plan1 = objects.ActionPlan(
            self.ctx, id=1, uuid=utils.generate_uuid(),
            audit_id=audit1.id, strategy_id=strategy1.id,
            state='DOESNOTMATTER', global_efficacy=[])
        # Stale after syncing because the goal of the audit has been modified
        # (compared to the defined fake goals)
        action_plan2 = objects.ActionPlan(
            self.ctx, id=2, uuid=utils.generate_uuid(),
            audit_id=audit2.id, strategy_id=strategy2.id,
            state='DOESNOTMATTER', global_efficacy=[])
        # Stale after syncing because the strategy has been modified
        # (compared to the defined fake strategies)
        action_plan3 = objects.ActionPlan(
            self.ctx, id=3, uuid=utils.generate_uuid(),
            audit_id=audit3.id, strategy_id=strategy3.id,
            state='DOESNOTMATTER', global_efficacy=[])
        # Stale after syncing because both the strategy and the related audit
        # have been modified (compared to the defined fake goals/strategies)
        action_plan4 = objects.ActionPlan(
            self.ctx, id=4, uuid=utils.generate_uuid(),
            audit_id=audit4.id, strategy_id=strategy4.id,
            state='DOESNOTMATTER', global_efficacy=[])

        action_plan1.create()
        action_plan2.create()
        action_plan3.create()
        action_plan4.create()

        before_goals = objects.Goal.list(self.ctx)
        before_strategies = objects.Strategy.list(self.ctx)
        before_audit_templates = objects.AuditTemplate.list(self.ctx)
        before_audits = objects.Audit.list(self.ctx)
        before_action_plans = objects.ActionPlan.list(self.ctx)

        # ### Action under test ### #

        try:
            self.syncer.sync()
        except Exception as exc:
            self.fail(exc)

        # ### Assertions ### #

        after_goals = objects.Goal.list(self.ctx)
        after_strategies = objects.Strategy.list(self.ctx)
        after_audit_templates = objects.AuditTemplate.list(self.ctx)
        after_audits = objects.Audit.list(self.ctx)
        after_action_plans = objects.ActionPlan.list(self.ctx)

        self.assertEqual(2, len(before_goals))
        self.assertEqual(4, len(before_strategies))
        self.assertEqual(4, len(before_audit_templates))
        self.assertEqual(4, len(before_audits))
        self.assertEqual(4, len(before_action_plans))
        self.assertEqual(2, len(after_goals))
        self.assertEqual(4, len(after_strategies))
        self.assertEqual(4, len(after_audit_templates))
        self.assertEqual(4, len(after_audits))
        self.assertEqual(4, len(after_action_plans))

        self.assertEqual(
            {"dummy_1", "dummy_2"},
            set([g.name for g in after_goals]))
        self.assertEqual(
            {"strategy_1", "strategy_2", "strategy_3", "strategy_4"},
            set([s.name for s in after_strategies]))

        created_goals, modified_goals, unmodified_goals = (
            self._find_created_modified_unmodified_ids(
                before_goals, after_goals))

        created_strategies, modified_strategies, unmodified_strategies = (
            self._find_created_modified_unmodified_ids(
                before_strategies, after_strategies))

        (created_audit_templates, modified_audit_templates,
         unmodified_audit_templates) = (
             self._find_created_modified_unmodified_ids(
                 before_audit_templates, after_audit_templates))

        created_audits, modified_audits, unmodified_audits = (
            self._find_created_modified_unmodified_ids(
                before_audits, after_audits))

        (created_action_plans, modified_action_plans,
         unmodified_action_plans) = (
             self._find_created_modified_unmodified_ids(
                 before_action_plans, after_action_plans))

        dummy_1_spec = jsonutils.loads(
            self.goal1_spec.serialize_indicators_specs())
        dummy_2_spec = jsonutils.loads(
            self.goal2_spec.serialize_indicators_specs())
        self.assertEqual(
            [dummy_1_spec, dummy_2_spec],
            [g.efficacy_specification for g in after_goals])

        self.assertEqual(1, len(created_goals))
        self.assertEqual(3, len(created_strategies))
        self.assertEqual(0, len(created_audits))
        self.assertEqual(0, len(created_action_plans))

        self.assertEqual(2, strategy2.goal_id)

        self.assertNotEqual(
            set([strategy2.id, strategy3.id, strategy4.id]),
            set(modified_strategies))
        self.assertEqual(set([strategy1.id]), set(unmodified_strategies))

        self.assertEqual(
            set([audit_template2.id, audit_template3.id, audit_template4.id]),
            set(modified_audit_templates))
        self.assertEqual(set([audit_template1.id]),
                         set(unmodified_audit_templates))

        self.assertEqual(
            set([audit2.id, audit3.id, audit4.id]),
            set(modified_audits))
        self.assertEqual(set([audit1.id]), set(unmodified_audits))

        self.assertEqual(
            set([action_plan2.id, action_plan3.id, action_plan4.id]),
            set(modified_action_plans))
        self.assertTrue(
            all(ap.state == objects.action_plan.State.CANCELLED
                for ap in modified_action_plans.values()))
        self.assertEqual(set([action_plan1.id]), set(unmodified_action_plans))

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
        # To be removed by the sync() because strategy entry point does not
        # exist anymore
        strategy2 = objects.Strategy(
            self.ctx, id=2, name="strategy_2", uuid=utils.generate_uuid(),
            display_name="Strategy 2", goal_id=goal1.id)
        # To be removed by the sync() because the goal has been soft deleted
        # and because the strategy entry point does not exist anymore
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
            self.ctx, id=1, name="Synced AT1", uuid=utils.generate_uuid(),
            goal_id=goal1.id, strategy_id=strategy1.id)
        # Stale after syncing because the goal has been soft deleted
        audit_template2 = objects.AuditTemplate(
            self.ctx, id=2, name="Synced AT2", uuid=utils.generate_uuid(),
            goal_id=goal2.id, strategy_id=strategy2.id)

        audit_template1.create()
        audit_template2.create()

        # Should stay unmodified after sync()
        audit1 = objects.Audit(
            self.ctx, id=1, uuid=utils.generate_uuid(), name='audit_1',
            audit_type=objects.audit.AuditType.ONESHOT.value,
            state=objects.audit.State.PENDING,
            goal_id=goal1.id, strategy_id=strategy1.id, auto_trigger=False)
        # Stale after syncing because the goal has been soft deleted
        audit2 = objects.Audit(
            self.ctx, id=2, uuid=utils.generate_uuid(), name='audit_2',
            audit_type=objects.audit.AuditType.ONESHOT.value,
            state=objects.audit.State.PENDING,
            goal_id=goal2.id, strategy_id=strategy2.id, auto_trigger=False)
        audit1.create()
        audit2.create()

        # Stale after syncing because its related strategy has been be
        # soft deleted
        action_plan1 = objects.ActionPlan(
            self.ctx, id=1, uuid=utils.generate_uuid(),
            audit_id=audit1.id, strategy_id=strategy1.id,
            state='DOESNOTMATTER', global_efficacy=[])
        # Stale after syncing because its related goal has been soft deleted
        action_plan2 = objects.ActionPlan(
            self.ctx, id=2, uuid=utils.generate_uuid(),
            audit_id=audit2.id, strategy_id=strategy2.id,
            state='DOESNOTMATTER', global_efficacy=[])

        action_plan1.create()
        action_plan2.create()

        before_goals = objects.Goal.list(self.ctx)
        before_strategies = objects.Strategy.list(self.ctx)
        before_audit_templates = objects.AuditTemplate.list(self.ctx)
        before_audits = objects.Audit.list(self.ctx)
        before_action_plans = objects.ActionPlan.list(self.ctx)

        # ### Action under test ### #

        try:
            self.syncer.sync()
        except Exception as exc:
            self.fail(exc)

        # ### Assertions ### #

        after_goals = objects.Goal.list(self.ctx)
        after_strategies = objects.Strategy.list(self.ctx)
        after_audit_templates = objects.AuditTemplate.list(self.ctx)
        after_audits = objects.Audit.list(self.ctx)
        after_action_plans = objects.ActionPlan.list(self.ctx)

        self.assertEqual(2, len(before_goals))
        self.assertEqual(3, len(before_strategies))
        self.assertEqual(2, len(before_audit_templates))
        self.assertEqual(2, len(before_audits))
        self.assertEqual(2, len(before_action_plans))
        self.assertEqual(1, len(after_goals))
        self.assertEqual(1, len(after_strategies))
        self.assertEqual(2, len(after_audit_templates))
        self.assertEqual(2, len(after_audits))
        self.assertEqual(2, len(after_action_plans))
        self.assertEqual(
            {"dummy_1"},
            set([g.name for g in after_goals]))
        self.assertEqual(
            {"strategy_1"},
            set([s.name for s in after_strategies]))

        created_goals, modified_goals, unmodified_goals = (
            self._find_created_modified_unmodified_ids(
                before_goals, after_goals))

        created_strategies, modified_strategies, unmodified_strategies = (
            self._find_created_modified_unmodified_ids(
                before_strategies, after_strategies))

        (created_audit_templates, modified_audit_templates,
         unmodified_audit_templates) = (
             self._find_created_modified_unmodified_ids(
                 before_audit_templates, after_audit_templates))

        created_audits, modified_audits, unmodified_audits = (
            self._find_created_modified_unmodified_ids(
                before_audits, after_audits))

        (created_action_plans, modified_action_plans,
         unmodified_action_plans) = (
             self._find_created_modified_unmodified_ids(
                 before_action_plans, after_action_plans))

        self.assertEqual(0, len(created_goals))
        self.assertEqual(0, len(created_strategies))
        self.assertEqual(0, len(created_audits))
        self.assertEqual(0, len(created_action_plans))

        self.assertEqual(set([audit_template2.id]),
                         set(modified_audit_templates))
        self.assertEqual(set([audit_template1.id]),
                         set(unmodified_audit_templates))

        self.assertEqual(set([audit2.id]), set(modified_audits))
        self.assertEqual(set([audit1.id]), set(unmodified_audits))

        self.assertEqual(set([action_plan2.id]), set(modified_action_plans))
        self.assertTrue(
            all(ap.state == objects.action_plan.State.CANCELLED
                for ap in modified_action_plans.values()))
        self.assertEqual(set([action_plan1.id]), set(unmodified_action_plans))

    def test_sync_strategies_with_removed_goal(self):
        # ### Setup ### #

        goal1 = objects.Goal(
            self.ctx, id=1, uuid=utils.generate_uuid(),
            name="dummy_1", display_name="Dummy 1",
            efficacy_specification=self.goal1_spec.serialize_indicators_specs()
        )
        goal2 = objects.Goal(
            self.ctx, id=2, uuid=utils.generate_uuid(),
            name="dummy_2", display_name="Dummy 2",
            efficacy_specification=self.goal2_spec.serialize_indicators_specs()
        )
        goal1.create()
        goal2.create()

        strategy1 = objects.Strategy(
            self.ctx, id=1, name="strategy_1", uuid=utils.generate_uuid(),
            display_name="Strategy 1", goal_id=goal1.id)
        strategy2 = objects.Strategy(
            self.ctx, id=2, name="strategy_2", uuid=utils.generate_uuid(),
            display_name="Strategy 2", goal_id=goal2.id)
        strategy1.create()
        strategy2.create()
        # to be removed by some reasons
        goal2.soft_delete()

        before_goals = objects.Goal.list(self.ctx)
        before_strategies = objects.Strategy.list(self.ctx)

        # ### Action under test ### #

        try:
            self.syncer.sync()
        except Exception as exc:
            self.fail(exc)

        # ### Assertions ### #

        after_goals = objects.Goal.list(self.ctx)
        after_strategies = objects.Strategy.list(self.ctx)

        self.assertEqual(1, len(before_goals))
        self.assertEqual(2, len(before_strategies))
        self.assertEqual(2, len(after_goals))
        self.assertEqual(4, len(after_strategies))
        self.assertEqual(
            {"dummy_1", "dummy_2"},
            set([g.name for g in after_goals]))
        self.assertEqual(
            {"strategy_1", "strategy_2", "strategy_3", "strategy_4"},
            set([s.name for s in after_strategies]))
