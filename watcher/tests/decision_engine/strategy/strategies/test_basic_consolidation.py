# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
import copy
import mock

from watcher.applier.loading import default
from watcher.common import clients
from watcher.common import exception
from watcher.decision_engine.model import model_root
from watcher.decision_engine.strategy import strategies
from watcher.tests import base
from watcher.tests.decision_engine.model import ceilometer_metrics
from watcher.tests.decision_engine.model import faker_cluster_state
from watcher.tests.decision_engine.model import gnocchi_metrics
from watcher.tests.decision_engine.model import monasca_metrics


class TestBasicConsolidation(base.TestCase):

    scenarios = [
        ("Ceilometer",
         {"datasource": "ceilometer",
          "fake_datasource_cls": ceilometer_metrics.FakeCeilometerMetrics}),
        ("Monasca",
         {"datasource": "monasca",
          "fake_datasource_cls": monasca_metrics.FakeMonascaMetrics}),
        ("Gnocchi",
         {"datasource": "gnocchi",
          "fake_datasource_cls": gnocchi_metrics.FakeGnocchiMetrics}),
    ]

    def setUp(self):
        super(TestBasicConsolidation, self).setUp()
        # fake metrics
        self.fake_metrics = self.fake_datasource_cls()
        # fake cluster
        self.fake_cluster = faker_cluster_state.FakerModelCollector()

        p_osc = mock.patch.object(
            clients, "OpenStackClients")
        self.m_osc = p_osc.start()
        self.addCleanup(p_osc.stop)

        p_model = mock.patch.object(
            strategies.BasicConsolidation, "compute_model",
            new_callable=mock.PropertyMock)
        self.m_model = p_model.start()
        self.addCleanup(p_model.stop)

        p_datasource = mock.patch.object(
            strategies.BasicConsolidation, 'datasource_backend',
            new_callable=mock.PropertyMock)
        self.m_datasource = p_datasource.start()
        self.addCleanup(p_datasource.stop)

        p_audit_scope = mock.patch.object(
            strategies.BasicConsolidation, "audit_scope",
            new_callable=mock.PropertyMock
        )
        self.m_audit_scope = p_audit_scope.start()
        self.addCleanup(p_audit_scope.stop)

        self.m_audit_scope.return_value = mock.Mock()

        self.m_model.return_value = model_root.ModelRoot()
        self.m_datasource.return_value = mock.Mock(
            get_host_cpu_usage=self.fake_metrics.get_usage_node_cpu,
            get_instance_cpu_usage=self.fake_metrics.
            get_average_usage_instance_cpu
        )
        self.strategy = strategies.BasicConsolidation(
            config=mock.Mock(datasource=self.datasource))

    def test_cluster_size(self):
        size_cluster = len(
            self.fake_cluster.generate_scenario_1().get_all_compute_nodes())
        size_cluster_assert = 5
        self.assertEqual(size_cluster_assert, size_cluster)

    def test_basic_consolidation_score_node(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_1_score = 0.023333333333333317
        self.assertEqual(node_1_score, self.strategy.calculate_score_node(
            model.get_node_by_uuid("Node_1")))
        node_2_score = 0.26666666666666666
        self.assertEqual(node_2_score, self.strategy.calculate_score_node(
            model.get_node_by_uuid("Node_2")))
        node_0_score = 0.023333333333333317
        self.assertEqual(node_0_score, self.strategy.calculate_score_node(
            model.get_node_by_uuid("Node_0")))

    def test_basic_consolidation_score_instance(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        instance_0_score = 0.023333333333333317
        self.assertEqual(
            instance_0_score,
            self.strategy.calculate_score_instance(instance_0))

        instance_1 = model.get_instance_by_uuid("INSTANCE_1")
        instance_1_score = 0.023333333333333317
        self.assertEqual(
            instance_1_score,
            self.strategy.calculate_score_instance(instance_1))
        instance_2 = model.get_instance_by_uuid("INSTANCE_2")
        instance_2_score = 0.033333333333333326
        self.assertEqual(
            instance_2_score,
            self.strategy.calculate_score_instance(instance_2))
        instance_6 = model.get_instance_by_uuid("INSTANCE_6")
        instance_6_score = 0.02666666666666669
        self.assertEqual(
            instance_6_score,
            self.strategy.calculate_score_instance(instance_6))
        instance_7 = model.get_instance_by_uuid("INSTANCE_7")
        instance_7_score = 0.013333333333333345
        self.assertEqual(
            instance_7_score,
            self.strategy.calculate_score_instance(instance_7))

    def test_basic_consolidation_score_instance_disk(self):
        model = self.fake_cluster.generate_scenario_5_with_instance_disk_0()
        self.m_model.return_value = model
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        instance_0_score = 0.023333333333333355
        self.assertEqual(
            instance_0_score,
            self.strategy.calculate_score_instance(instance_0))

    def test_basic_consolidation_weight(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        instance_0 = model.get_instance_by_uuid("INSTANCE_0")
        cores = 16
        # 80 Go
        disk = 80
        # mem 8 Go
        mem = 8
        instance_0_weight_assert = 3.1999999999999997
        self.assertEqual(
            instance_0_weight_assert,
            self.strategy.calculate_weight(instance_0, cores, disk, mem))

    def test_exception_model(self):
        self.m_model.return_value = None
        self.assertRaises(
            exception.ClusterStateNotDefined, self.strategy.execute)

    def test_exception_cluster_empty(self):
        model = model_root.ModelRoot()
        self.m_model.return_value = model
        self.assertRaises(exception.ClusterEmpty, self.strategy.execute)

    def test_check_migration(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model

        all_instances = model.get_all_instances()
        all_nodes = model.get_all_compute_nodes()
        instance0 = all_instances[list(all_instances.keys())[0]]
        node0 = all_nodes[list(all_nodes.keys())[0]]

        self.strategy.check_migration(node0, node0, instance0)

    def test_threshold(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model

        all_nodes = model.get_all_compute_nodes()
        node0 = all_nodes[list(all_nodes.keys())[0]]

        self.assertFalse(self.strategy.check_threshold(
            node0, 1000, 1000, 1000))

    def test_basic_consolidation_works_on_model_copy(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = copy.deepcopy(model)

        self.assertTrue(model_root.ModelRoot.is_isomorphic(
            model, self.strategy.compute_model))
        self.assertIsNot(model, self.strategy.compute_model)

    def test_basic_consolidation_migration(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model

        solution = self.strategy.execute()

        actions_counter = collections.Counter(
            [action.get('action_type') for action in solution.actions])

        expected_num_migrations = 1
        expected_power_state = 1

        num_migrations = actions_counter.get("migrate", 0)
        num_node_state_change = actions_counter.get(
            "change_nova_service_state", 0)
        self.assertEqual(expected_num_migrations, num_migrations)
        self.assertEqual(expected_power_state, num_node_state_change)

    def test_basic_consolidation_execute_scenario_8_with_4_nodes(self):
        model = self.fake_cluster.generate_scenario_8_with_4_nodes()
        self.m_model.return_value = model

        solution = self.strategy.execute()

        actions_counter = collections.Counter(
            [action.get('action_type') for action in solution.actions])

        expected_num_migrations = 5
        expected_power_state = 3
        expected_global_efficacy = 75

        num_migrations = actions_counter.get("migrate", 0)
        num_node_state_change = actions_counter.get(
            "change_nova_service_state", 0)

        global_efficacy_value = solution.global_efficacy[0].get('value', 0)

        self.assertEqual(expected_num_migrations, num_migrations)
        self.assertEqual(expected_power_state, num_node_state_change)
        self.assertEqual(expected_global_efficacy, global_efficacy_value)

    def test_exception_stale_cdm(self):
        self.fake_cluster.set_cluster_data_model_as_stale()
        self.m_model.return_value = self.fake_cluster.cluster_data_model

        self.assertRaises(
            exception.ClusterStateNotDefined,
            self.strategy.execute)

    # calculate_weight
    def test_execute_no_workload(self):
        model = (
            self.fake_cluster
            .generate_scenario_4_with_1_node_no_instance())
        self.m_model.return_value = model

        with mock.patch.object(
            strategies.BasicConsolidation, 'calculate_weight'
        ) as mock_score_call:
            mock_score_call.return_value = 0
            solution = self.strategy.execute()

            self.assertEqual(0,
                             solution.efficacy.global_efficacy[0].get('value'))

    def test_check_parameters(self):
        model = self.fake_cluster.generate_scenario_3_with_2_nodes()
        self.m_model.return_value = model
        solution = self.strategy.execute()
        loader = default.DefaultActionLoader()
        for action in solution.actions:
            loaded_action = loader.load(action['action_type'])
            loaded_action.input_parameters = action['input_parameters']
            loaded_action.validate_parameters()

    """def test_periods(self):
        model = self.fake_cluster.generate_scenario_1()
        self.m_model.return_value = model
        node_1 = model.get_node_by_uuid("Node_1")
        p_ceilometer = mock.patch.object(
            strategies.BasicConsolidation, "ceilometer")
        m_ceilometer = p_ceilometer.start()
        self.addCleanup(p_ceilometer.stop)
        p_monasca = mock.patch.object(strategies.BasicConsolidation, "monasca")
        m_monasca = p_monasca.start()
        self.addCleanup(p_monasca.stop)
        p_gnocchi = mock.patch.object(strategies.BasicConsolidation, "gnocchi")
        m_gnocchi = p_gnocchi.start()
        self.addCleanup(p_gnocchi.stop)
        datetime_patcher = mock.patch.object(
            datetime, 'datetime',
            mock.Mock(wraps=datetime.datetime)
        )
        mocked_datetime = datetime_patcher.start()
        mocked_datetime.utcnow.return_value = datetime.datetime(
            2017, 3, 19, 18, 53, 11, 657417)
        self.addCleanup(datetime_patcher.stop)
        m_monasca.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        m_ceilometer.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        m_gnocchi.return_value = mock.Mock(
            statistic_aggregation=self.fake_metrics.mock_get_statistics)
        self.strategy.calculate_score_node(node_1)
        resource_id = "%s_%s" % (node_1.uuid, node_1.hostname)
        if self.strategy.config.datasource == "ceilometer":
            m_ceilometer.statistic_aggregation.assert_called_with(
                aggregate='avg', meter_name='compute.node.cpu.percent',
                period=7200, resource_id=resource_id)
        elif self.strategy.config.datasource == "monasca":
            m_monasca.statistic_aggregation.assert_called_with(
                aggregate='avg', meter_name='cpu.percent',
                period=7200, dimensions={'hostname': 'Node_1'})
        elif self.strategy.config.datasource == "gnocchi":
            stop_time = datetime.datetime.utcnow()
            start_time = stop_time - datetime.timedelta(
                seconds=int('7200'))
            m_gnocchi.statistic_aggregation.assert_called_with(
                resource_id=resource_id, metric='compute.node.cpu.percent',
                granularity=300, start_time=start_time, stop_time=stop_time,
                aggregation='mean')

        self.strategy.input_parameters.update({"period": 600})
        self.strategy.calculate_score_node(node_1)
        if self.strategy.config.datasource == "ceilometer":
            m_ceilometer.statistic_aggregation.assert_called_with(
                aggregate='avg', meter_name='compute.node.cpu.percent',
                period=600, resource_id=resource_id)
        elif self.strategy.config.datasource == "monasca":
            m_monasca.statistic_aggregation.assert_called_with(
                aggregate='avg', meter_name='cpu.percent',
                period=600, dimensions={'hostname': 'Node_1'})
        elif self.strategy.config.datasource == "gnocchi":
            stop_time = datetime.datetime.utcnow()
            start_time = stop_time - datetime.timedelta(
                seconds=int('600'))
            m_gnocchi.statistic_aggregation.assert_called_with(
                resource_id=resource_id, metric='compute.node.cpu.percent',
                granularity=300, start_time=start_time, stop_time=stop_time,
                aggregation='mean')"""
