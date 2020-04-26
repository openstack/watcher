# -*- encoding: utf-8 -*-
# Copyright (c) 2015 Intel Corp
#
# Authors: Zhenzan Zhou <zhenzan.zhou@intel.com>
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
#
import collections
from unittest import mock

from watcher.applier.loading import default
from watcher.common import utils
from watcher.decision_engine.strategy import strategies
from watcher.tests.decision_engine.model import ceilometer_metrics
from watcher.tests.decision_engine.model import gnocchi_metrics
from watcher.tests.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy


class TestOutletTempControl(TestBaseStrategy):

    scenarios = [
        ("Ceilometer",
         {"datasource": "ceilometer",
          "fake_datasource_cls": ceilometer_metrics.FakeCeilometerMetrics}),
        ("Gnocchi",
         {"datasource": "gnocchi",
          "fake_datasource_cls": gnocchi_metrics.FakeGnocchiMetrics}),
    ]

    def setUp(self):
        super(TestOutletTempControl, self).setUp()
        # fake metrics
        self.fake_metrics = self.fake_datasource_cls()

        p_datasource = mock.patch.object(
            strategies.OutletTempControl, 'datasource_backend',
            new_callable=mock.PropertyMock)
        self.m_datasource = p_datasource.start()
        self.addCleanup(p_datasource.stop)

        self.m_datasource.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics,
            NAME=self.fake_metrics.NAME)
        self.strategy = strategies.OutletTempControl(
            config=mock.Mock(datasource=self.datasource))

        self.strategy.input_parameters = utils.Struct()
        self.strategy.input_parameters.update({'threshold': 34.3})
        self.strategy.threshold = 34.3

    def test_group_hosts_by_outlet_temp(self):
        model = self.fake_c_cluster.generate_scenario_3_with_2_nodes()
        self.m_c_model.return_value = model
        n1, n2 = self.strategy.group_hosts_by_outlet_temp()
        self.assertEqual("af69c544-906b-4a6a-a9c6-c1f7a8078c73",
                         n1[0]['compute_node'].uuid)
        self.assertEqual("fa69c544-906b-4a6a-a9c6-c1f7a8078c73",
                         n2[0]['compute_node'].uuid)

    def test_choose_instance_to_migrate(self):
        model = self.fake_c_cluster.generate_scenario_3_with_2_nodes()
        self.m_c_model.return_value = model
        n1, n2 = self.strategy.group_hosts_by_outlet_temp()
        instance_to_mig = self.strategy.choose_instance_to_migrate(n1)
        self.assertEqual('af69c544-906b-4a6a-a9c6-c1f7a8078c73',
                         instance_to_mig[0].uuid)
        self.assertEqual('a4cab39b-9828-413a-bf88-f76921bf1517',
                         instance_to_mig[1].uuid)

    def test_filter_dest_servers(self):
        model = self.fake_c_cluster.generate_scenario_3_with_2_nodes()
        self.m_c_model.return_value = model
        n1, n2 = self.strategy.group_hosts_by_outlet_temp()
        instance_to_mig = self.strategy.choose_instance_to_migrate(n1)
        dest_hosts = self.strategy.filter_dest_servers(n2, instance_to_mig[1])
        self.assertEqual(1, len(dest_hosts))
        self.assertEqual("fa69c544-906b-4a6a-a9c6-c1f7a8078c73",
                         dest_hosts[0]['compute_node'].uuid)

    def test_execute_no_workload(self):
        model = self.fake_c_cluster.\
            generate_scenario_4_with_1_node_no_instance()
        self.m_c_model.return_value = model

        solution = self.strategy.execute()
        self.assertEqual([], solution.actions)

    def test_execute(self):
        model = self.fake_c_cluster.generate_scenario_3_with_2_nodes()
        self.m_c_model.return_value = model
        solution = self.strategy.execute()
        actions_counter = collections.Counter(
            [action.get('action_type') for action in solution.actions])

        num_migrations = actions_counter.get("migrate", 0)
        self.assertEqual(1, num_migrations)

    def test_check_parameters(self):
        model = self.fake_c_cluster.generate_scenario_3_with_2_nodes()
        self.m_c_model.return_value = model
        solution = self.strategy.execute()
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()
