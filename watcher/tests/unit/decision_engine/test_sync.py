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
from watcher.tests.unit.db import base
from watcher.tests.unit.decision_engine import fake_goals
from watcher.tests.unit.decision_engine import fake_strategies


class TestSyncer(base.DbTestCase):

    def setUp(self):
        super().setUp()
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
    def _find_created_modified_unmodified_ids(before, after):
        created = {
            a_item.id: a_item for a_item in after
            if a_item.uuid not in (b_item.uuid for b_item in before)
        }

        modified = {
            a_item.id: a_item for a_item in after
            if a_item.as_dict() not in (
                b_items.as_dict() for b_items in before)
        }

        unmodified = {
            a_item.id: a_item for a_item in after
            if a_item.as_dict() in (
                b_items.as_dict() for b_items in before)
        }

        return created, modified, unmodified

    def _create_audit(self, audit_id, goal_id, strategy_id, state):
        audit = objects.Audit(
            self.ctx,
            id=audit_id,
            uuid=utils.generate_uuid(),
            name=f'audit_{audit_id}',
            audit_type=objects.audit.AuditType.ONESHOT.value,
            state=state,
            goal_id=goal_id,
            strategy_id=strategy_id,
            auto_trigger=False,
        )
        audit.create()
        return audit

    def _create_action_plan(
        self, action_plan_id, audit_id, strategy_id, state
    ):
        action_plan = objects.ActionPlan(
            self.ctx,
            id=action_plan_id,
            uuid=utils.generate_uuid(),
            audit_id=audit_id,
            strategy_id=strategy_id,
            state=state,
            global_efficacy=[],
        )
        action_plan.create()
        return action_plan

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

        # Unchanged goal/strategy: should stay unmodified
        audit1 = self._create_audit(
            1, goal1.id, strategy1.id, objects.audit.State.PENDING
        )
        # Terminal audits whose goal was modified: left untouched
        audit_goal_succeeded = self._create_audit(
            2, goal2.id, strategy2.id, objects.audit.State.SUCCEEDED
        )
        audit_goal_failed = self._create_audit(
            7, goal2.id, strategy2.id, objects.audit.State.FAILED
        )
        audit_goal_cancelled = self._create_audit(
            8, goal2.id, strategy2.id, objects.audit.State.CANCELLED
        )
        # Non-terminal audits whose goal/strategy was modified: cancelled
        audit_goal_ongoing = self._create_audit(
            5, goal2.id, strategy2.id, objects.audit.State.ONGOING
        )
        audit_goal_suspended = self._create_audit(
            6, goal2.id, strategy2.id, objects.audit.State.SUSPENDED
        )
        # Non-terminal audits whose strategy was modified: cancelled
        audit_strategy_pending = self._create_audit(
            3, goal1.id, strategy3.id, objects.audit.State.PENDING
        )
        audit_strategy_ongoing = self._create_audit(
            9, goal1.id, strategy3.id, objects.audit.State.ONGOING
        )
        # Terminal audits whose strategy was modified: left untouched
        audit_strategy_succeeded = self._create_audit(
            10, goal1.id, strategy3.id, objects.audit.State.SUCCEEDED
        )
        audit_strategy_failed = self._create_audit(
            11, goal1.id, strategy3.id, objects.audit.State.FAILED
        )
        audit_strategy_cancelled = self._create_audit(
            12, goal1.id, strategy3.id, objects.audit.State.CANCELLED
        )
        # Non-terminal audits whose both goal and strategy were modified:
        # cancelled
        audit_both_pending = self._create_audit(
            4, goal2.id, strategy4.id, objects.audit.State.PENDING
        )
        audit_both_ongoing = self._create_audit(
            13, goal2.id, strategy4.id, objects.audit.State.ONGOING
        )
        audit_both_cancelled = self._create_audit(
            14, goal2.id, strategy4.id, objects.audit.State.CANCELLED
        )
        # Terminal audits whose both goal and strategy were modified:
        # left untouched
        audit_both_succeeded = self._create_audit(
            15, goal2.id, strategy4.id, objects.audit.State.SUCCEEDED
        )
        audit_both_failed = self._create_audit(
            16, goal2.id, strategy4.id, objects.audit.State.FAILED
        )

        # Baseline AP on unchanged audit/strategy
        action_plan1 = self._create_action_plan(
            1, audit1.id, strategy1.id, objects.action_plan.State.RECOMMENDED
        )
        # Non-terminal APs on terminal audits with a modified goal: cancelled
        ap_term_recommended = self._create_action_plan(
            2,
            audit_goal_succeeded.id,
            strategy2.id,
            objects.action_plan.State.RECOMMENDED,
        )
        ap_term_pending = self._create_action_plan(
            6,
            audit_goal_ongoing.id,
            strategy2.id,
            objects.action_plan.State.PENDING,
        )
        ap_term_ongoing = self._create_action_plan(
            7,
            audit_goal_cancelled.id,
            strategy2.id,
            objects.action_plan.State.ONGOING,
        )
        ap_term_cancelling = self._create_action_plan(
            8,
            audit_goal_succeeded.id,
            strategy2.id,
            objects.action_plan.State.CANCELLING,
        )
        # Terminal APs on terminal audits with a modified goal: left untouched
        ap_term_succeeded = self._create_action_plan(
            5,
            audit_goal_succeeded.id,
            strategy2.id,
            objects.action_plan.State.SUCCEEDED,
        )
        ap_term_failed = self._create_action_plan(
            9,
            audit_goal_failed.id,
            strategy2.id,
            objects.action_plan.State.FAILED,
        )
        ap_term_cancelled = self._create_action_plan(
            10,
            audit_goal_cancelled.id,
            strategy2.id,
            objects.action_plan.State.CANCELLED,
        )
        ap_term_superseded = self._create_action_plan(
            11,
            audit_goal_succeeded.id,
            strategy2.id,
            objects.action_plan.State.SUPERSEDED,
        )
        # Non-terminal AP cancelled because its strategy was modified
        ap_strategy_recommended = self._create_action_plan(
            3,
            audit_strategy_succeeded.id,
            strategy3.id,
            objects.action_plan.State.RECOMMENDED,
        )
        # Terminal AP kept even though its strategy was modified
        ap_strategy_succeeded = self._create_action_plan(
            13,
            audit_strategy_ongoing.id,
            strategy3.id,
            objects.action_plan.State.SUCCEEDED,
        )
        # Non-terminal AP cancelled because its audit becomes stale
        ap_on_stale_audit = self._create_action_plan(
            12,
            audit_goal_ongoing.id,
            strategy2.id,
            objects.action_plan.State.PENDING,
        )
        # Both goal and strategy modified: cancelled
        ap_both = self._create_action_plan(
            4,
            audit_both_succeeded.id,
            strategy4.id,
            objects.action_plan.State.RECOMMENDED,
        )

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
        self.assertEqual(16, len(before_audits))
        self.assertEqual(13, len(before_action_plans))
        self.assertEqual(2, len(after_goals))
        self.assertEqual(4, len(after_strategies))
        self.assertEqual(4, len(after_audit_templates))
        self.assertEqual(16, len(after_audits))
        self.assertEqual(13, len(after_action_plans))

        self.assertEqual(
            {"dummy_1", "dummy_2"},
            {g.name for g in after_goals})
        self.assertEqual(
            {"strategy_1", "strategy_2", "strategy_3", "strategy_4"},
            {s.name for s in after_strategies})

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

        self.assertEqual({strategy1.id}, set(unmodified_strategies))

        self.assertEqual(
            {audit_template2.id, audit_template3.id, audit_template4.id},
            set(modified_audit_templates))
        self.assertEqual({audit_template1.id},
                         set(unmodified_audit_templates))

        cancelled_audits = {
            audit_strategy_pending.id,
            audit_strategy_ongoing.id,
            audit_both_pending.id,
            audit_both_ongoing.id,
            audit_goal_ongoing.id,
            audit_goal_suspended.id,
        }
        untouched_audits = {
            audit1.id,
            audit_goal_succeeded.id,
            audit_goal_failed.id,
            audit_goal_cancelled.id,
            audit_strategy_succeeded.id,
            audit_strategy_failed.id,
            audit_strategy_cancelled.id,
            audit_both_succeeded.id,
            audit_both_failed.id,
            audit_both_cancelled.id,
        }
        self.assertEqual(cancelled_audits, set(modified_audits))
        self.assertEqual(untouched_audits, set(unmodified_audits))
        self.assertTrue(
            all(
                audit.state == objects.audit.State.CANCELLED
                for audit in modified_audits.values()
            )
        )

        cancelled_action_plans = {
            ap_term_recommended.id,
            ap_term_pending.id,
            ap_term_ongoing.id,
            ap_term_cancelling.id,
            ap_strategy_recommended.id,
            ap_on_stale_audit.id,
            ap_both.id,
        }
        untouched_action_plans = {
            action_plan1.id,
            ap_term_succeeded.id,
            ap_term_failed.id,
            ap_term_cancelled.id,
            ap_term_superseded.id,
            ap_strategy_succeeded.id,
        }
        self.assertEqual(cancelled_action_plans, set(modified_action_plans))
        self.assertTrue(
            all(
                ap.state == objects.action_plan.State.CANCELLED
                for ap in modified_action_plans.values()
            )
        )
        self.assertEqual(untouched_action_plans, set(unmodified_action_plans))
        self.assertEqual(
            ap_term_succeeded.state, objects.action_plan.State.SUCCEEDED
        )
        self.assertEqual(
            ap_term_failed.state, objects.action_plan.State.FAILED
        )
        self.assertEqual(
            ap_term_cancelled.state, objects.action_plan.State.CANCELLED
        )
        self.assertEqual(
            ap_term_superseded.state, objects.action_plan.State.SUPERSEDED
        )
        self.assertEqual(
            ap_strategy_succeeded.state, objects.action_plan.State.SUCCEEDED
        )

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

        # Unchanged goal/strategy: should stay unmodified
        audit1 = self._create_audit(
            1, goal1.id, strategy1.id, objects.audit.State.PENDING
        )
        # Non-terminal audits whose goal was removed: cancelled
        audit_goal_pending = self._create_audit(
            2, goal2.id, strategy3.id, objects.audit.State.PENDING
        )
        audit_goal_ongoing = self._create_audit(
            3, goal2.id, strategy3.id, objects.audit.State.ONGOING
        )
        # Terminal audits whose goal was removed: left untouched
        audit_goal_succeeded = self._create_audit(
            4, goal2.id, strategy3.id, objects.audit.State.SUCCEEDED
        )
        audit_goal_failed = self._create_audit(
            5, goal2.id, strategy3.id, objects.audit.State.FAILED
        )
        # Non-terminal audits whose strategy was removed: cancelled
        audit_strategy_pending = self._create_audit(
            6, goal1.id, strategy2.id, objects.audit.State.PENDING
        )
        audit_strategy_suspended = self._create_audit(
            7, goal1.id, strategy2.id, objects.audit.State.SUSPENDED
        )
        audit_strategy_ongoing = self._create_audit(
            8, goal1.id, strategy2.id, objects.audit.State.ONGOING
        )
        # Terminal audit whose strategy was removed: left untouched
        audit_strategy_cancelled = self._create_audit(
            9, goal1.id, strategy2.id, objects.audit.State.CANCELLED
        )
        audit_strategy_failed = self._create_audit(
            10, goal1.id, strategy2.id, objects.audit.State.FAILED
        )
        audit_strategy_succeeded = self._create_audit(
            11, goal1.id, strategy2.id, objects.audit.State.SUCCEEDED
        )

        # Baseline AP on unchanged audit/strategy
        action_plan1 = self._create_action_plan(
            1, audit1.id, strategy1.id, objects.action_plan.State.RECOMMENDED
        )
        # Non-terminal APs whose strategy was removed: cancelled
        ap_strategy_recommended = self._create_action_plan(
            2,
            audit_goal_ongoing.id,
            strategy3.id,
            objects.action_plan.State.RECOMMENDED,
        )
        ap_strategy_pending = self._create_action_plan(
            3,
            audit_strategy_ongoing.id,
            strategy2.id,
            objects.action_plan.State.PENDING,
        )
        ap_strategy_ongoing = self._create_action_plan(
            4,
            audit_strategy_suspended.id,
            strategy2.id,
            objects.action_plan.State.ONGOING,
        )
        ap_strategy_cancelling = self._create_action_plan(
            5,
            audit_strategy_succeeded.id,
            strategy2.id,
            objects.action_plan.State.CANCELLING,
        )
        # Non-terminal AP on a terminal audit whose strategy was removed
        ap_on_term_audit = self._create_action_plan(
            10,
            audit_goal_succeeded.id,
            strategy3.id,
            objects.action_plan.State.RECOMMENDED,
        )
        ap_on_term_audit_ongoing = self._create_action_plan(
            11,
            audit_goal_ongoing.id,
            strategy3.id,
            objects.action_plan.State.ONGOING,
        )
        # Terminal APs whose strategy was removed: left untouched
        ap_strategy_succeeded = self._create_action_plan(
            6,
            audit_strategy_ongoing.id,
            strategy2.id,
            objects.action_plan.State.SUCCEEDED,
        )
        ap_strategy_failed = self._create_action_plan(
            7,
            audit_strategy_ongoing.id,
            strategy2.id,
            objects.action_plan.State.FAILED,
        )
        ap_strategy_cancelled = self._create_action_plan(
            8,
            audit_strategy_cancelled.id,
            strategy2.id,
            objects.action_plan.State.CANCELLED,
        )
        ap_strategy_superseded = self._create_action_plan(
            9,
            audit_strategy_ongoing.id,
            strategy2.id,
            objects.action_plan.State.SUPERSEDED,
        )

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
        self.assertEqual(11, len(before_audits))
        self.assertEqual(11, len(before_action_plans))
        self.assertEqual(1, len(after_goals))
        self.assertEqual(1, len(after_strategies))
        self.assertEqual(2, len(after_audit_templates))
        self.assertEqual(11, len(after_audits))
        self.assertEqual(11, len(after_action_plans))
        self.assertEqual({"dummy_1"}, {g.name for g in after_goals})
        self.assertEqual({"strategy_1"}, {s.name for s in after_strategies})

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

        self.assertEqual({audit_template2.id},
                         set(modified_audit_templates))
        self.assertEqual({audit_template1.id},
                         set(unmodified_audit_templates))

        cancelled_audits = {
            audit_goal_pending.id,
            audit_goal_ongoing.id,
            audit_strategy_pending.id,
            audit_strategy_suspended.id,
            audit_strategy_ongoing.id,
        }
        untouched_audits = {
            audit1.id,
            audit_goal_succeeded.id,
            audit_goal_failed.id,
            audit_strategy_cancelled.id,
            audit_strategy_succeeded.id,
            audit_strategy_failed.id,
        }
        self.assertEqual(cancelled_audits, set(modified_audits))
        self.assertEqual(untouched_audits, set(unmodified_audits))
        self.assertTrue(
            all(
                audit.state == objects.audit.State.CANCELLED
                for audit in modified_audits.values()
            )
        )

        self.assertEqual(
            audit_goal_succeeded.state, objects.audit.State.SUCCEEDED
        )
        self.assertEqual(audit_goal_failed.state, objects.audit.State.FAILED)
        self.assertEqual(
            audit_strategy_succeeded.state, objects.audit.State.SUCCEEDED
        )
        self.assertEqual(
            audit_strategy_failed.state, objects.audit.State.FAILED
        )
        self.assertEqual(
            audit_strategy_cancelled.state, objects.audit.State.CANCELLED
        )

        cancelled_action_plans = {
            ap_strategy_recommended.id,
            ap_strategy_pending.id,
            ap_strategy_ongoing.id,
            ap_strategy_cancelling.id,
            ap_on_term_audit.id,
            ap_on_term_audit_ongoing.id,
        }
        untouched_action_plans = {
            action_plan1.id,
            ap_strategy_succeeded.id,
            ap_strategy_failed.id,
            ap_strategy_cancelled.id,
            ap_strategy_superseded.id,
        }
        self.assertEqual(cancelled_action_plans, set(modified_action_plans))
        self.assertTrue(
            all(
                ap.state == objects.action_plan.State.CANCELLED
                for ap in modified_action_plans.values()
            )
        )
        self.assertEqual(untouched_action_plans, set(unmodified_action_plans))
        self.assertEqual(
            ap_strategy_succeeded.state, objects.action_plan.State.SUCCEEDED
        )
        self.assertEqual(
            ap_strategy_failed.state, objects.action_plan.State.FAILED
        )
        self.assertEqual(
            ap_strategy_cancelled.state, objects.action_plan.State.CANCELLED
        )
        self.assertEqual(
            ap_strategy_superseded.state, objects.action_plan.State.SUPERSEDED
        )

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
            {g.name for g in after_goals})
        self.assertEqual(
            {"strategy_1", "strategy_2", "strategy_3", "strategy_4"},
            {s.name for s in after_strategies})
