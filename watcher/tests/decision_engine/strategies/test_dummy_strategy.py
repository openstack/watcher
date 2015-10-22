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
from watcher.decision_engine.strategies.dummy_strategy import DummyStrategy
from watcher.tests import base
from watcher.tests.decision_engine.faker_cluster_state import \
    FakerStateCollector


class TestDummyStrategy(base.TestCase):
    def test_dummy_strategy(self):
        tactique = DummyStrategy("basic", "Basic offline consolidation")
        fake_cluster = FakerStateCollector()
        model = fake_cluster.generate_scenario_4_with_2_hypervisors()
        tactique.execute(model)
