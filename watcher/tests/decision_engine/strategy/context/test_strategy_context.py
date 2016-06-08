# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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
import mock

from watcher.common import utils
from watcher.decision_engine.solution import default
from watcher.decision_engine.strategy.context import default as d_strategy_ctx
from watcher.decision_engine.strategy.selection import default as d_selector
from watcher.decision_engine.strategy import strategies
from watcher.metrics_engine.cluster_model_collector import manager
from watcher.tests.db import base
from watcher.tests.objects import utils as obj_utils


class TestStrategyContext(base.DbTestCase):
    def setUp(self):
        super(TestStrategyContext, self).setUp()
        obj_utils.create_test_goal(self.context, id=1, name="DUMMY")
        audit_template = obj_utils.create_test_audit_template(
            self.context, uuid=utils.generate_uuid())
        self.audit = obj_utils.create_test_audit(
            self.context, audit_template_id=audit_template.id)

    strategy_context = d_strategy_ctx.DefaultStrategyContext()

    @mock.patch.object(strategies.DummyStrategy, 'model',
                       new_callable=mock.PropertyMock)
    @mock.patch.object(d_selector.DefaultStrategySelector, 'select')
    def test_execute_strategy(self, mock_call, m_model):
        m_model.return_value = mock.Mock()
        mock_call.return_value = strategies.DummyStrategy(
            config=mock.Mock())
        solution = self.strategy_context.execute_strategy(
            self.audit.uuid, self.context)
        self.assertIsInstance(solution, default.DefaultSolution)

    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector",
                       mock.Mock())
    def test_execute_force_dummy(self):
        obj_utils.create_test_goal(self.context, id=50,
                                   uuid=utils.generate_uuid(),
                                   name="my_goal")

        strategy = obj_utils.create_test_strategy(self.context,
                                                  id=42,
                                                  uuid=utils.generate_uuid(),
                                                  name="dummy")

        audit_template = obj_utils.create_test_audit_template(
            self.context,
            uuid=utils.generate_uuid(),
            strategy_id=strategy.id,
            name="my_template")

        audit = obj_utils.create_test_audit(
            self.context,
            audit_template_id=audit_template.id,
            uuid=utils.generate_uuid(),
        )

        solution = self.strategy_context.execute_strategy(
            audit.uuid, self.context)

        self.assertEqual(len(solution.actions), 3)

    @mock.patch.object(strategies.BasicConsolidation, "execute")
    @mock.patch.object(manager.CollectorManager, "get_cluster_model_collector",
                       mock.Mock())
    def test_execute_force_basic(self, mock_call):
        expected_strategy = "basic"
        mock_call.return_value = expected_strategy

        obj_utils.create_test_goal(self.context, id=50,
                                   uuid=utils.generate_uuid(),
                                   name="my_goal")

        strategy = obj_utils.create_test_strategy(self.context,
                                                  id=42,
                                                  uuid=utils.generate_uuid(),
                                                  name=expected_strategy)

        audit_template = obj_utils.create_test_audit_template(
            self.context,
            uuid=utils.generate_uuid(),
            strategy_id=strategy.id,
            name="my_template")

        audit = obj_utils.create_test_audit(
            self.context,
            audit_template_id=audit_template.id,
            uuid=utils.generate_uuid(),
        )

        solution = self.strategy_context.execute_strategy(
            audit.uuid, self.context)

        self.assertEqual(solution, expected_strategy)
