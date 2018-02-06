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
from watcher.datasource import gnocchi as gnocchi_helper
from watcher.tests import base

CONF = cfg.CONF


@mock.patch.object(clients.OpenStackClients, 'gnocchi')
class TestGnocchiHelper(base.BaseTestCase):

    def test_gnocchi_statistic_aggregation(self, mock_gnocchi):
        gnocchi = mock.MagicMock()
        expected_result = 5.5

        expected_measures = [["2017-02-02T09:00:00.000000", 360, 5.5]]

        gnocchi.metric.get_measures.return_value = expected_measures
        mock_gnocchi.return_value = gnocchi

        helper = gnocchi_helper.GnocchiHelper()
        result = helper.statistic_aggregation(
            resource_id='16a86790-327a-45f9-bc82-45839f062fdc',
            meter_name='cpu_util',
            period=300,
            granularity=360,
            dimensions=None,
            aggregation='mean',
            group_by='*'
        )
        self.assertEqual(expected_result, result)

    @mock.patch.object(gnocchi_helper.GnocchiHelper, 'statistic_aggregation')
    def test_get_host_cpu_usage(self, mock_aggregation, mock_gnocchi):
        helper = gnocchi_helper.GnocchiHelper()
        helper.get_host_cpu_usage('compute1', 600, 'mean', granularity=300)
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_cpu_usage'], 600, 300,
            aggregation='mean')

    @mock.patch.object(gnocchi_helper.GnocchiHelper, 'statistic_aggregation')
    def test_get_instance_cpu_usage(self, mock_aggregation, mock_gnocchi):
        helper = gnocchi_helper.GnocchiHelper()
        helper.get_instance_cpu_usage('compute1', 600, 'mean', granularity=300)
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['instance_cpu_usage'], 600, 300,
            aggregation='mean')

    @mock.patch.object(gnocchi_helper.GnocchiHelper, 'statistic_aggregation')
    def test_get_host_memory_usage(self, mock_aggregation, mock_gnocchi):
        helper = gnocchi_helper.GnocchiHelper()
        helper.get_host_memory_usage('compute1', 600, 'mean', granularity=300)
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_memory_usage'], 600, 300,
            aggregation='mean')

    @mock.patch.object(gnocchi_helper.GnocchiHelper, 'statistic_aggregation')
    def test_get_instance_memory_usage(self, mock_aggregation, mock_gnocchi):
        helper = gnocchi_helper.GnocchiHelper()
        helper.get_instance_memory_usage('compute1', 600, 'mean',
                                         granularity=300)
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['instance_ram_usage'], 600, 300,
            aggregation='mean')

    @mock.patch.object(gnocchi_helper.GnocchiHelper, 'statistic_aggregation')
    def test_get_instance_ram_allocated(self, mock_aggregation, mock_gnocchi):
        helper = gnocchi_helper.GnocchiHelper()
        helper.get_instance_ram_allocated('compute1', 600, 'mean',
                                          granularity=300)
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['instance_ram_allocated'], 600, 300,
            aggregation='mean')

    @mock.patch.object(gnocchi_helper.GnocchiHelper, 'statistic_aggregation')
    def test_get_instance_root_disk_allocated(self, mock_aggregation,
                                              mock_gnocchi):
        helper = gnocchi_helper.GnocchiHelper()
        helper.get_instance_root_disk_allocated('compute1', 600, 'mean',
                                                granularity=300)
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['instance_root_disk_size'], 600,
            300, aggregation='mean')

    @mock.patch.object(gnocchi_helper.GnocchiHelper, 'statistic_aggregation')
    def test_get_host_outlet_temperature(self, mock_aggregation, mock_gnocchi):
        helper = gnocchi_helper.GnocchiHelper()
        helper.get_host_outlet_temperature('compute1', 600, 'mean',
                                           granularity=300)
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_outlet_temp'], 600, 300,
            aggregation='mean')

    @mock.patch.object(gnocchi_helper.GnocchiHelper, 'statistic_aggregation')
    def test_get_host_inlet_temperature(self, mock_aggregation, mock_gnocchi):
        helper = gnocchi_helper.GnocchiHelper()
        helper.get_host_inlet_temperature('compute1', 600, 'mean',
                                          granularity=300)
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_inlet_temp'], 600, 300,
            aggregation='mean')

    @mock.patch.object(gnocchi_helper.GnocchiHelper, 'statistic_aggregation')
    def test_get_host_airflow(self, mock_aggregation, mock_gnocchi):
        helper = gnocchi_helper.GnocchiHelper()
        helper.get_host_airflow('compute1', 600, 'mean', granularity=300)
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_airflow'], 600, 300,
            aggregation='mean')

    @mock.patch.object(gnocchi_helper.GnocchiHelper, 'statistic_aggregation')
    def test_get_host_power(self, mock_aggregation, mock_gnocchi):
        helper = gnocchi_helper.GnocchiHelper()
        helper.get_host_power('compute1', 600, 'mean', granularity=300)
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_power'], 600, 300,
            aggregation='mean')

    def test_gnocchi_check_availability(self, mock_gnocchi):
        gnocchi = mock.MagicMock()
        gnocchi.status.get.return_value = True
        mock_gnocchi.return_value = gnocchi
        helper = gnocchi_helper.GnocchiHelper()
        result = helper.check_availability()
        self.assertEqual('available', result)

    def test_gnocchi_check_availability_with_failure(self, mock_gnocchi):
        cfg.CONF.set_override("query_max_retries", 1,
                              group='gnocchi_client')
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
                              group='gnocchi_client')
        gnocchi = mock.MagicMock()
        gnocchi.metric.list.side_effect = Exception()
        mock_gnocchi.return_value = gnocchi
        helper = gnocchi_helper.GnocchiHelper()
        self.assertFalse(helper.list_metrics())
