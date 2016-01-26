# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

from watcher.applier.actions.loading import default
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.strategy.strategies import \
    faker_cluster_state


class TestDummyStrategy(base.TestCase):
    def test_dummy_strategy(self):
        dummy = strategies.DummyStrategy("dummy", "Dummy strategy")
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_3_with_2_hypervisors()
        solution = dummy.execute(model)
        self.assertEqual(3, len(solution.actions))

    def test_check_parameters(self):
        dummy = strategies.DummyStrategy("dummy", "Dummy strategy")
        fake_cluster = faker_cluster_state.FakerModelCollector()
        model = fake_cluster.generate_scenario_3_with_2_hypervisors()
        solution = dummy.execute(model)
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()
