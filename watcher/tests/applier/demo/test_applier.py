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

"""
from oslo_config import cfg

from watcher.applier.framework.default_applier import DefaultApplier

from watcher.common import utils
from watcher.decision_engine.framework.default_planner import DefaultPlanner
from watcher.decision_engine.strategies.basic_consolidation import \
    BasicConsolidation
from watcher.openstack.common import log
from watcher.tests.db import base
from watcher.tests.db import utils as db_utils
from watcher.tests.decision_engine.faker_cluster_state import \
    FakerStateCollector
from watcher.tests.decision_engine.faker_metrics_collector import \
    FakerMetricsCollector

from oslo_config import cfg

CONF = cfg.CONF
""
class TestApplier(base.DbTestCase):
    default_planner = DefaultPlanner()

    def create_solution(self):
        metrics = FakerMetricsCollector()
        current_state_cluster = FakerStateCollector()
        sercon = BasicConsolidation()
        sercon.set_metrics_resource_collector(metrics)
        return sercon.execute(current_state_cluster.generate_scenario_1())

    def test_scheduler_w(self):
        CONF.debug = True
        log.setup('watcher-sercon-demo')

        CONF.keystone_authtoken.auth_uri = "http://10.50.0.105:5000/v3"
        CONF.keystone_authtoken.admin_user = "admin"
        CONF.keystone_authtoken.admin_password = "openstacktest"
        CONF.keystone_authtoken.admin_tenant_name = "test"

        audit = db_utils.create_test_audit(uuid=utils.generate_uuid())

        action_plan = self.default_planner.schedule(self.context,
                                                    audit.id,
                                                    self.create_solution())

        applier = DefaultApplier()
        applier.execute(self.context, action_plan.uuid)
"""""
