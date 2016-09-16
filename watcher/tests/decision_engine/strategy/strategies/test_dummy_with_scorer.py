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

import mock

from watcher.applier.loading import default
from watcher.common import utils
from watcher.decision_engine.model import model_root
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.model import faker_cluster_state


class TestDummyWithScorer(base.TestCase):

    def setUp(self):
        super(TestDummyWithScorer, self).setUp()
        # fake cluster
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

        p_model = mock.patch.object(
            strategies.DummyWithScorer, "compute_model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        self.m_model.return_value = model_root.ModelRoot()
        self.strategy = strategies.DummyWithScorer(config=mock.Mock())

    def test_dummy_with_scorer(self):
        dummy = strategies.DummyWithScorer(config=mock.Mock())
        dummy.input_parameters = utils.Struct()
        dummy.input_parameters.update({'param1': 4.0, 'param2': 'Hi'})
        solution = dummy.execute()
        self.assertEqual(4, len(solution.actions))

    def test_check_parameters(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model
        self.strategy.input_parameters = utils.Struct()
        self.strategy.input_parameters.update({'param1': 4.0, 'param2': 'Hi'})
        solution = self.strategy.execute()
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()
