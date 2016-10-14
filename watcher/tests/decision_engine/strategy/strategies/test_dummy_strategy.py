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


class TestDummyStrategy(base.TestCase):

    def setUp(self):
        super(TestDummyStrategy, self).setUp()
        # fake cluster
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

        p_model = mock.patch.object(
            strategies.DummyStrategy, "compute_model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        p_audit_scope = mock.patch.object(
            strategies.DummyStrategy, "audit_scope",
            new_callable=mock.PropertyMock
        )
        self.m_audit_scope = p_audit_scope.start()
        self.addCleanup(p_audit_scope.stop)

        self.m_audit_scope.return_value = mock.Mock()

        self.m_model.return_value = model_root.ModelRoot()
        self.strategy = strategies.DummyStrategy(config=mock.Mock())

        self.m_model.return_value = model_root.ModelRoot()
        self.strategy = strategies.DummyStrategy(config=mock.Mock())

    def test_dummy_strategy(self):
        dummy = strategies.DummyStrategy(config=mock.Mock())
        dummy.input_parameters = utils.Struct()
        dummy.input_parameters.update({'para1': 4.0, 'para2': 'Hi'})
        solution = dummy.execute()
        self.assertEqual(3, len(solution.actions))

    def test_check_parameters(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model
        self.strategy.input_parameters = utils.Struct()
        self.strategy.input_parameters.update({'para1': 4.0, 'para2': 'Hi'})
        solution = self.strategy.execute()
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()
