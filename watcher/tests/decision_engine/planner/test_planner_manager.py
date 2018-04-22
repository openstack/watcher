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

from oslo_config import cfg

from watcher.decision_engine.planner import manager as planner
from watcher.decision_engine.planner import weight
from watcher.tests import base


class TestPlannerManager(base.TestCase):
    def test_load(self):
        cfg.CONF.set_override('planner', "weight", group='watcher_planner')
        manager = planner.PlannerManager()
        selected_planner = cfg.CONF.watcher_planner.planner
        self.assertIsInstance(manager.load(selected_planner),
                              weight.WeightPlanner)
