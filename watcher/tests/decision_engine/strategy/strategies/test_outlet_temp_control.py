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
import mock

from watcher.applier.loading import default
from watcher.common import exception
from watcher.common import utils
from watcher.decision_engine.model import model_root
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.model import ceilometer_metrics
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.decision_engine.model import gnocchi_metrics


class TestOutletTempControl(base.TestCase):

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

        # fake cluster
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

        p_model = mock.patch.object(
            strategies.OutletTempControl, "compute_model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        p_datasource = mock.patch.object(
            strategies.OutletTempControl, 'datasource_backend',
            new_callable=mock.PropertyMock)
        self.m_datasource = p_datasource.start()
        self.addCleanup(p_datasource.stop)

        p_audit_scope = mock.patch.object(
            strategies.OutletTempControl, "audit_scope",
            new_callable=mock.PropertyMock
        )
        self.m_audit_scope = p_audit_scope.start()
        self.addCleanup(p_audit_scope.stop)

        self.m_audit_scope.return_value = mock.Mock()

        self.m_model.return_value = model_root.ModelRoot()
        self.m_datasource.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        self.strategy = strategies.OutletTempControl(
            config=mock.Mock(datasource=self.datasource))

        self.strategy.input_parameters = utils.Struct()
        self.strategy.input_parameters.update({'threshold': 34.3})
        self.strategy.threshold = 34.3

    def test_calc_used_resource(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model
        node = model.get_node_by_uuid('Node_0')
        cores_used, mem_used, disk_used = self.strategy.calc_used_resource(
            node)

        self.assertEqual((10, 2, 20), (cores_used, mem_used, disk_used))

    def test_group_hosts_by_outlet_temp(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model
        n1, n2 = self.strategy.group_hosts_by_outlet_temp()
        self.assertEqual('Node_1', n1[0]['node'].uuid)
        self.assertEqual('Node_0', n2[0]['node'].uuid)

    def test_choose_instance_to_migrate(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model
        n1, n2 = self.strategy.group_hosts_by_outlet_temp()
        instance_to_mig = self.strategy.choose_instance_to_migrate(n1)
        self.assertEqual('Node_1', instance_to_mig[0].uuid)
        self.assertEqual('a4cab39b-9828-413a-bf88-f76921bf1517',
                         instance_to_mig[1].uuid)

    def test_filter_dest_servers(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model
        n1, n2 = self.strategy.group_hosts_by_outlet_temp()
        instance_to_mig = self.strategy.choose_instance_to_migrate(n1)
        dest_hosts = self.strategy.filter_dest_servers(n2, instance_to_mig[1])
        self.assertEqual(1, len(dest_hosts))
        self.assertEqual('Node_0', dest_hosts[0]['node'].uuid)

    def test_exception_model(self):
        self.m_model.return_value = None
        self.assertRaises(
            exception.ClusterStateNotDefined, self.strategy.execute)

    def test_exception_cluster_empty(self):
        model = model_root.ModelRoot()
        self.m_model.return_value = model
        self.assertRaises(exception.ClusterEmpty, self.strategy.execute)

    def test_exception_stale_cdm(self):
        self.fake_cluster.set_cluster_data_model_as_stale()
        self.m_model.return_value = self.fake_cluster.cluster_data_model

        self.assertRaises(
            exception.ClusterStateNotDefined,
            self.strategy.execute)

    def test_execute_cluster_empty(self):
        model = model_root.ModelRoot()
        self.m_model.return_value = model
        self.assertRaises(exception.ClusterEmpty, self.strategy.execute)

    def test_execute_no_workload(self):
        model = self.fake_cluster.generate_scenario_4_with_1_node_no_instance()
        self.m_model.return_value = model

        solution = self.strategy.execute()
        self.assertEqual([], solution.actions)

    def test_execute(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model
        solution = self.strategy.execute()
        actions_counter = collections.Counter(
            [action.get('action_type') for action in solution.actions])

        num_migrations = actions_counter.get("migrate", 0)
        self.assertEqual(1, num_migrations)

    def test_check_parameters(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model
        solution = self.strategy.execute()
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()
