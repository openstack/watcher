# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Intel Corp
#
# Authors: Prudhvi Rao Shedimbi <prudhvi.rao.shedimbi@intel.com>
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

import collections
import mock

from watcher.applier.loading import default
from watcher.common import utils
from watcher.decision_engine.strategy import strategies
from watcher.tests.decision_engine.model import ceilometer_metrics
from watcher.tests.decision_engine.model import gnocchi_metrics
from watcher.tests.decision_engine.strategy.strategies.test_base \
    import TestBaseStrategy


class TestNoisyNeighbor(TestBaseStrategy):

    scenarios = [
        ("Ceilometer",
         {"datasource": "ceilometer",
          "fake_datasource_cls": ceilometer_metrics.FakeCeilometerMetrics}),
        ("Gnocchi",
         {"datasource": "gnocchi",
          "fake_datasource_cls": gnocchi_metrics.FakeGnocchiMetrics}),
    ]

    def setUp(self):
        super(TestNoisyNeighbor, self).setUp()
        # fake metrics
        self.f_metrics = self.fake_datasource_cls()

        p_datasource = mock.patch.object(
            strategies.NoisyNeighbor, "datasource_backend",
            new_callable=mock.PropertyMock)
        self.m_datasource = p_datasource.start()
        self.addCleanup(p_datasource.stop)

        self.m_datasource.return_value = mock.Mock(
            get_instance_l3_cache_usage=self.f_metrics.mock_get_statistics_nn)
        self.strategy = strategies.NoisyNeighbor(config=mock.Mock())

        self.strategy.input_parameters = utils.Struct()
        self.strategy.input_parameters.update({'cache_threshold': 35})
        self.strategy.threshold = 35
        self.strategy.input_parameters.update({'period': 100})
        self.strategy.threshold = 100

    def test_calc_used_resource(self):
        model = self.fake_c_cluster.generate_scenario_3_with_2_nodes()
        self.m_c_model.return_value = model
        node = model.get_node_by_uuid("fa69c544-906b-4a6a-a9c6-c1f7a8078c73")
        cores_used, mem_used, disk_used = self.strategy.calc_used_resource(
            node)

        self.assertEqual((10, 2, 20), (cores_used, mem_used, disk_used))

    def test_group_hosts(self):
        self.strategy.cache_threshold = 35
        self.strategy.period = 100
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        node_uuid = 'Node_1'
        n1, n2 = self.strategy.group_hosts()
        self.assertTrue(node_uuid in n1)
        self.assertEqual(n1[node_uuid]['priority_vm'].uuid, 'INSTANCE_3')
        self.assertEqual(n1[node_uuid]['noisy_vm'].uuid, 'INSTANCE_4')
        self.assertEqual('Node_0', n2[0].uuid)

    def test_find_priority_instance(self):
        self.strategy.cache_threshold = 35
        self.strategy.period = 100
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        potential_prio_inst = model.get_instance_by_uuid('INSTANCE_3')
        inst_res = self.strategy.find_priority_instance(potential_prio_inst)
        self.assertEqual('INSTANCE_3', inst_res.uuid)

    def test_find_noisy_instance(self):
        self.strategy.cache_threshold = 35
        self.strategy.period = 100
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        potential_noisy_inst = model.get_instance_by_uuid('INSTANCE_4')
        inst_res = self.strategy.find_noisy_instance(potential_noisy_inst)
        self.assertEqual('INSTANCE_4', inst_res.uuid)

    def test_filter_destination_hosts(self):
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
        self.m_c_model.return_value = model
        self.strategy.cache_threshold = 35
        self.strategy.period = 100
        n1, n2 = self.strategy.group_hosts()
        mig_source_node = max(n1.keys(), key=lambda a:
                              n1[a]['priority_vm'])
        instance_to_mig = n1[mig_source_node]['noisy_vm']
        dest_hosts = self.strategy.filter_dest_servers(
            n2, instance_to_mig)

        self.assertEqual(1, len(dest_hosts))
        self.assertEqual('Node_0', dest_hosts[0].uuid)

    def test_execute_no_workload(self):
        self.strategy.cache_threshold = 35
        self.strategy.period = 100
        model = self.fake_c_cluster.\
            generate_scenario_4_with_1_node_no_instance()
        self.m_c_model.return_value = model

        solution = self.strategy.execute()
        self.assertEqual([], solution.actions)

    def test_execute(self):
        self.strategy.cache_threshold = 35
        self.strategy.period = 100
        model = self.fake_c_cluster.generate_scenario_7_with_2_nodes()
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
