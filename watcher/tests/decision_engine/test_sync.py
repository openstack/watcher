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
from watcher.decision_engine.strategy.strategies import base as base_strategy
from watcher.decision_engine import sync
from watcher.objects import goal
from watcher.tests.db import base


class FakeStrategy(base_strategy.BaseStrategy):
    DEFAULT_NAME = ""
    DEFAULT_DESCRIPTION = ""

    def execute(self, original_model):
        pass


class FakeDummy1Strategy1(FakeStrategy):
    DEFAULT_NAME = "DUMMY_1"
    DEFAULT_DESCRIPTION = "Dummy 1"
    ID = "STRATEGY_1"


class FakeDummy1Strategy2(FakeStrategy):
    DEFAULT_NAME = "DUMMY_1"
    DEFAULT_DESCRIPTION = "Dummy 1"
    ID = "STRATEGY_2"


class FakeDummy2Strategy3(FakeStrategy):
    DEFAULT_NAME = "DUMMY_2"
    DEFAULT_DESCRIPTION = "Dummy 2"
    ID = "STRATEGY_3"


class FakeDummy2Strategy4(FakeStrategy):
    DEFAULT_NAME = "DUMMY_2"
    DEFAULT_DESCRIPTION = "Other Dummy 2"
    ID = "STRATEGY_4"


class TestSyncer(base.DbTestCase):

    def setUp(self):
        super(TestSyncer, self).setUp()
        self.ctx = context.make_context()

        self.m_available_strategies = mock.Mock(return_value={
            FakeDummy1Strategy1.DEFAULT_NAME: FakeDummy1Strategy1,
            FakeDummy1Strategy2.DEFAULT_NAME: FakeDummy1Strategy2,
            FakeDummy2Strategy3.DEFAULT_NAME: FakeDummy2Strategy3,
            FakeDummy2Strategy4.DEFAULT_NAME: FakeDummy2Strategy4,
        })

        p_strategies = mock.patch.object(
            default.DefaultStrategyLoader, 'list_available',
            self.m_available_strategies)
        p_strategies.start()

        self.syncer = sync.Syncer()
        self.addCleanup(p_strategies.stop)

    @mock.patch.object(goal.Goal, "soft_delete")
    @mock.patch.object(goal.Goal, "save")
    @mock.patch.object(goal.Goal, "create")
    @mock.patch.object(goal.Goal, "list")
    def test_sync_goals_empty_db(self, m_list, m_create,
                                 m_save, m_soft_delete):
        m_list.return_value = []

        self.syncer.sync()

        self.assertEqual(2, m_create.call_count)
        self.assertEqual(0, m_save.call_count)
        self.assertEqual(0, m_soft_delete.call_count)

    @mock.patch.object(goal.Goal, "soft_delete")
    @mock.patch.object(goal.Goal, "save")
    @mock.patch.object(goal.Goal, "create")
    @mock.patch.object(goal.Goal, "list")
    def test_sync_goals_with_existing_goal(self, m_list, m_create,
                                           m_save, m_soft_delete):
        m_list.return_value = [
            goal.Goal(self.ctx, id=1, uuid=utils.generate_uuid(),
                      name="DUMMY_1", display_name="Dummy 1")
        ]
        self.syncer.sync()

        self.assertEqual(1, m_create.call_count)
        self.assertEqual(0, m_save.call_count)
        self.assertEqual(0, m_soft_delete.call_count)

    @mock.patch.object(goal.Goal, "soft_delete")
    @mock.patch.object(goal.Goal, "save")
    @mock.patch.object(goal.Goal, "create")
    @mock.patch.object(goal.Goal, "list")
    def test_sync_goals_with_modified_goal(self, m_list, m_create,
                                           m_save, m_soft_delete):
        m_list.return_value = [
            goal.Goal(self.ctx, id=1, uuid=utils.generate_uuid(),
                      name="DUMMY_2", display_name="original")
        ]
        self.syncer.sync()

        self.assertEqual(2, m_create.call_count)
        self.assertEqual(0, m_save.call_count)
        self.assertEqual(1, m_soft_delete.call_count)

    def test_end2end_sync_goals_with_modified_goal(self):
        goal1 = goal.Goal(self.ctx, id=1, uuid=utils.generate_uuid(),
                          name="DUMMY_2", display_name="original")
        goal1.create()

        before_goals = goal.Goal.list(self.ctx)

        try:
            self.syncer.sync()
        except Exception as exc:
            self.fail(exc)

        after_goals = goal.Goal.list(self.ctx)
        self.assertEqual(1, len(before_goals))
        self.assertEqual(2, len(after_goals))
        self.assertEqual(
            {"DUMMY_1", "DUMMY_2"},
            set([g.name for g in after_goals]))
        created_goals = [ag for ag in after_goals
                         if ag.uuid not in [bg.uuid for bg in before_goals]]
        self.assertEqual(2, len(created_goals))
        # TODO(v-francoise): check that the audit templates are re-synced with
        # the new goal version
