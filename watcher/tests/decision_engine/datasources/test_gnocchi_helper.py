# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock
from oslo_config import cfg

from watcher.common import clients
from watcher.common import exception
from watcher.decision_engine.datasources import gnocchi as gnocchi_helper
from watcher.tests import base

CONF = cfg.CONF


@mock.patch.object(clients.OpenStackClients, 'gnocchi')
class TestGnocchiHelper(base.BaseTestCase):

    def setUp(self):
        super(TestGnocchiHelper, self).setUp()
        self.osc_mock = mock.Mock()
        self.helper = gnocchi_helper.GnocchiHelper(osc=self.osc_mock)
        stat_agg_patcher = mock.patch.object(
            self.helper, 'statistic_aggregation',
            spec=gnocchi_helper.GnocchiHelper.statistic_aggregation)
        self.mock_aggregation = stat_agg_patcher.start()
        self.addCleanup(stat_agg_patcher.stop)

    def test_gnocchi_statistic_aggregation(self, mock_gnocchi):
        gnocchi = mock.MagicMock()
        expected_result = 5.5

        expected_measures = [["2017-02-02T09:00:00.000000", 360, 5.5]]

        gnocchi.metric.get_measures.return_value = expected_measures
        mock_gnocchi.return_value = gnocchi

        helper = gnocchi_helper.GnocchiHelper()
        result = helper.statistic_aggregation(
            resource=mock.Mock(id='16a86790-327a-45f9-bc82-45839f062fdc'),
            resource_type='instance',
            meter_name='instance_cpu_usage',
            period=300,
            granularity=360,
            aggregate='mean',
        )
        self.assertEqual(expected_result, result)

    def test_statistic_aggregation_metric_unavailable(self, mock_gnocchi):
        helper = gnocchi_helper.GnocchiHelper()

        # invalidate instance_cpu_usage in metric map
        original_metric_value = helper.METRIC_MAP.get('instance_cpu_usage')
        helper.METRIC_MAP.update(
            instance_cpu_usage=None
        )

        self.assertRaises(
            exception.MetricNotAvailable, helper.statistic_aggregation,
            resource=mock.Mock(id='16a86790-327a-45f9-bc82-45839f062fdc'),
            resource_type='instance', meter_name='instance_cpu_usage',
            period=300, granularity=360, aggregate='mean',
        )

        # restore the metric map as it is a static attribute that does not get
        # restored between unit tests!
        helper.METRIC_MAP.update(
            instance_cpu_usage=original_metric_value
        )

    def test_get_host_cpu_usage(self, mock_gnocchi):
        self.helper.get_host_cpu_usage('compute1', 600, 'mean', 300)
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_cpu_usage', 600, 'mean',
            300)

    def test_get_host_ram_usage(self, mock_gnocchi):
        self.helper.get_host_ram_usage('compute1', 600, 'mean', 300)
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_ram_usage', 600, 'mean',
            300)

    def test_get_host_outlet_temperature(self, mock_gnocchi):
        self.helper.get_host_outlet_temp('compute1', 600, 'mean', 300)
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_outlet_temp', 600, 'mean',
            300)

    def test_get_host_inlet_temperature(self, mock_gnocchi):
        self.helper.get_host_inlet_temp('compute1', 600, 'mean', 300)
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_inlet_temp', 600, 'mean',
            300)

    def test_get_host_airflow(self, mock_gnocchi):
        self.helper.get_host_airflow('compute1', 600, 'mean', 300)
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_airflow', 600, 'mean',
            300)

    def test_get_host_power(self, mock_gnocchi):
        self.helper.get_host_power('compute1', 600, 'mean', 300)
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_power', 600, 'mean',
            300)

    def test_get_instance_cpu_usage(self, mock_gnocchi):
        self.helper.get_instance_cpu_usage('compute1', 600, 'mean', 300)
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'instance', 'instance_cpu_usage', 600, 'mean',
            300)

    def test_get_instance_memory_usage(self, mock_gnocchi):
        self.helper.get_instance_ram_usage('compute1', 600, 'mean', 300)
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'instance', 'instance_ram_usage', 600, 'mean',
            300)

    def test_get_instance_ram_allocated(self, mock_gnocchi):
        self.helper.get_instance_ram_allocated('compute1', 600, 'mean', 300)
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'instance', 'instance_ram_allocated', 600, 'mean',
            300)

    def test_get_instance_root_disk_allocated(self, mock_gnocchi):
        self.helper.get_instance_root_disk_size('compute1', 600, 'mean', 300)
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'instance', 'instance_root_disk_size', 600, 'mean',
            300)

    def test_gnocchi_check_availability(self, mock_gnocchi):
        gnocchi = mock.MagicMock()
        gnocchi.status.get.return_value = True
        mock_gnocchi.return_value = gnocchi
        helper = gnocchi_helper.GnocchiHelper()
        result = helper.check_availability()
        self.assertEqual('available', result)

    def test_gnocchi_check_availability_with_failure(self, mock_gnocchi):
        cfg.CONF.set_override("query_max_retries", 1,
                              group='watcher_datasources')
        gnocchi = mock.MagicMock()
        gnocchi.status.get.side_effect = Exception()
        mock_gnocchi.return_value = gnocchi
        helper = gnocchi_helper.GnocchiHelper()

        self.assertEqual('not available', helper.check_availability())

    def test_gnocchi_list_metrics(self, mock_gnocchi):
        gnocchi = mock.MagicMock()
        metrics = [{"name": "metric1"}, {"name": "metric2"}]
        expected_metrics = set(["metric1", "metric2"])
        gnocchi.metric.list.return_value = metrics
        mock_gnocchi.return_value = gnocchi
        helper = gnocchi_helper.GnocchiHelper()
        result = helper.list_metrics()
        self.assertEqual(expected_metrics, result)

    def test_gnocchi_list_metrics_with_failure(self, mock_gnocchi):
        cfg.CONF.set_override("query_max_retries", 1,
                              group='watcher_datasources')
        gnocchi = mock.MagicMock()
        gnocchi.metric.list.side_effect = Exception()
        mock_gnocchi.return_value = gnocchi
        helper = gnocchi_helper.GnocchiHelper()
        self.assertFalse(helper.list_metrics())
