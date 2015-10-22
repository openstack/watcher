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
from watcher.common.exception import MetaActionNotFound
from watcher.common import utils
from watcher.db import api as db_api
from watcher.decision_engine.framework.default_planner import DefaultPlanner
from watcher.decision_engine.strategies.basic_consolidation import \
    BasicConsolidation
from watcher.tests.db import base
from watcher.tests.db import utils as db_utils
from watcher.tests.decision_engine.faker_cluster_state import \
    FakerStateCollector
from watcher.tests.decision_engine.faker_metrics_collector import \
    FakerMetricsCollector
from watcher.tests.objects import utils as obj_utils


class SolutionFaker(object):
    @staticmethod
    def build():
        metrics = FakerMetricsCollector()
        current_state_cluster = FakerStateCollector()
        sercon = BasicConsolidation("basic", "Basic offline consolidation")
        sercon.set_metrics_resource_collector(metrics)
        return sercon.execute(current_state_cluster.generate_scenario_1())


class SolutionFakerSingleHyp(object):
    @staticmethod
    def build():
        metrics = FakerMetricsCollector()
        current_state_cluster = FakerStateCollector()
        sercon = BasicConsolidation("basic", "Basic offline consolidation")
        sercon.set_metrics_resource_collector(metrics)
        return sercon.execute(
            current_state_cluster.generate_scenario_4_with_2_hypervisors())


class TestDefaultPlanner(base.DbTestCase):
    default_planner = DefaultPlanner()

    def setUp(self):
        super(TestDefaultPlanner, self).setUp()
        obj_utils.create_test_audit_template(self.context)

        p = mock.patch.object(db_api.Connection, 'create_action_plan')
        self.mock_create_action_plan = p.start()
        self.mock_create_action_plan.side_effect = (
            self._simulate_action_plan_create)
        self.addCleanup(p.stop)

        q = mock.patch.object(db_api.Connection, 'create_action')
        self.mock_create_action = q.start()
        self.mock_create_action.side_effect = (
            self._simulate_action_create)
        self.addCleanup(q.stop)

    def _simulate_action_plan_create(self, action_plan):
        action_plan.create()
        return action_plan

    def _simulate_action_create(self, action):
        action.create()
        return action

    def test_scheduler_w(self):
        audit = db_utils.create_test_audit(uuid=utils.generate_uuid())
        fake_solution = SolutionFaker.build()
        action_plan = self.default_planner.schedule(self.context,
                                                    audit.id, fake_solution)
        self.assertIsNotNone(action_plan.uuid)

    def test_schedule_raise(self):
        audit = db_utils.create_test_audit(uuid=utils.generate_uuid())
        fake_solution = SolutionFaker.build()
        fake_solution._meta_actions[0] = "valeur_qcq"
        self.assertRaises(MetaActionNotFound, self.default_planner.schedule,
                          self.context, audit.id, fake_solution)

    def test_schedule_scheduled_empty(self):
        audit = db_utils.create_test_audit(uuid=utils.generate_uuid())
        fake_solution = SolutionFakerSingleHyp.build()
        action_plan = self.default_planner.schedule(self.context,
                                                    audit.id, fake_solution)
        self.assertIsNotNone(action_plan.uuid)

    def test_scheduler_warning_empty_action_plan(self):
        audit = db_utils.create_test_audit(uuid=utils.generate_uuid())
        fake_solution = SolutionFaker.build()
        action_plan = self.default_planner.schedule(self.context,
                                                    audit.id, fake_solution)
        self.assertIsNotNone(action_plan.uuid)
