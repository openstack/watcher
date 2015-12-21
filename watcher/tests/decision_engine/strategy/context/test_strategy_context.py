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

from watcher.decision_engine.solution.default import DefaultSolution
from watcher.decision_engine.strategy.context.default import \
    DefaultStrategyContext
from watcher.decision_engine.strategy.selection.default import \
    DefaultStrategySelector
from watcher.decision_engine.strategy.strategies.dummy_strategy import \
    DummyStrategy
from watcher.metrics_engine.cluster_model_collector.manager import \
    CollectorManager
from watcher.tests.db import base
from watcher.tests.objects import utils as obj_utils


class TestStrategyContext(base.DbTestCase):
    def setUp(self):
        super(TestStrategyContext, self).setUp()
        self.audit_template = obj_utils. \
            create_test_audit_template(self.context)
        self.audit = obj_utils. \
            create_test_audit(self.context,
                              audit_template_id=self.audit_template.id)

    strategy_context = DefaultStrategyContext()

    @mock.patch.object(DefaultStrategySelector, 'define_from_goal')
    @mock.patch.object(CollectorManager, "get_cluster_model_collector",
                       mock.Mock())
    def test_execute_strategy(self, mock_call):
        mock_call.return_value = DummyStrategy()
        solution = self.strategy_context.execute_strategy(self.audit.uuid,
                                                          self.context)
        self.assertIsInstance(solution, DefaultSolution)
