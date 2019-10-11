# -*- encoding: utf-8 -*-
# Copyright (c) 2019 European Organization for Nuclear Research (CERN)
#
# Authors: Corne Lukken <info@dantalion.nl>
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

from oslo_config import cfg
from oslo_log import log

from watcher.common import clients
from watcher.common import exception
from watcher.decision_engine.datasources import grafana
from watcher.tests import base

import requests

CONF = cfg.CONF
LOG = log.getLogger(__name__)


@mock.patch.object(clients.OpenStackClients, 'nova', mock.Mock())
class TestGrafana(base.BaseTestCase):
    """Test the GrafanaHelper datasource

    Objects under test are preceded with t_ and mocked objects are preceded
    with m_ , additionally, patched objects are preceded with p_ no object
    under test should be created in setUp this can influence the results.
    """

    def setUp(self):
        super(TestGrafana, self).setUp()

        self.p_conf = mock.patch.object(
            grafana, 'CONF',
            new_callable=mock.PropertyMock)
        self.m_conf = self.p_conf.start()
        self.addCleanup(self.p_conf.stop)

        self.m_conf.grafana_client.token = \
            "eyJrIjoiT0tTcG1pUlY2RnVKZTFVaDFsNFZXdE9ZWmNrMkZYbk=="
        self.m_conf.grafana_client.base_url = "https://grafana.proxy/api/"
        self.m_conf.grafana_client.project_id_map = {'host_cpu_usage': 7221}
        self.m_conf.grafana_client.database_map = \
            {'host_cpu_usage': 'mock_db'}
        self.m_conf.grafana_client.attribute_map = \
            {'host_cpu_usage': 'hostname'}
        self.m_conf.grafana_client.translator_map = \
            {'host_cpu_usage': 'influxdb'}
        self.m_conf.grafana_client.query_map = \
            {'host_cpu_usage': 'SELECT 100-{0}("{0}_value") FROM {3}.'
                               'cpu_percent WHERE ("host" =~ /^{1}$/ AND '
                               '"type_instance" =~/^idle$/ AND time > '
                               '(now()-{2}m)'}

        self.m_grafana = grafana.GrafanaHelper(osc=mock.Mock())
        stat_agg_patcher = mock.patch.object(
            self.m_grafana, 'statistic_aggregation',
            spec=grafana.GrafanaHelper.statistic_aggregation)
        self.mock_aggregation = stat_agg_patcher.start()
        self.addCleanup(stat_agg_patcher.stop)

        self.m_compute_node = mock.Mock(
            id='16a86790-327a-45f9-bc82-45839f062fdc',
            hostname='example.hostname.ch'
        )
        self.m_instance = mock.Mock(
            id='73b1ff78-aca7-404f-ac43-3ed16c1fa555',
            human_id='example.hostname'
        )

    def test_configured(self):
        """Initialize GrafanaHelper and check if configured is true"""

        t_grafana = grafana.GrafanaHelper(osc=mock.Mock())
        self.assertTrue(t_grafana.configured)

    def test_configured_error(self):
        """Butcher the required configuration and test if configured is false

        """

        self.m_conf.grafana_client.base_url = ""
        t_grafana = grafana.GrafanaHelper(osc=mock.Mock())
        self.assertFalse(t_grafana.configured)

    def test_configured_raise_error(self):
        """Test raising error when using improperly configured GrafanHelper

        Assure that the _get_metric method raises errors if the metric is
        missing from the map
        """

        # Clear the METRIC_MAP of Grafana since it is a static variable that
        # other tests might have set before this test runs.
        grafana.GrafanaHelper.METRIC_MAP = {}

        self.m_conf.grafana_client.base_url = ""

        t_grafana = grafana.GrafanaHelper(osc=mock.Mock())

        self.assertFalse(t_grafana.configured)
        self.assertEqual({}, t_grafana.METRIC_MAP)
        self.assertRaises(
            exception.MetricNotAvailable,
            t_grafana.get_host_cpu_usage,
            self.m_compute_node
        )

    @mock.patch.object(requests, 'get')
    def test_request_raise_error(self, m_request):
        """Test raising error when status code of request indicates problem

        Assure that the _request method raises errors if the response indicates
        problems.
        """

        m_request.return_value = mock.Mock(status_code=404)

        t_grafana = grafana.GrafanaHelper(osc=mock.Mock())

        self.assertIsNone(t_grafana.get_host_cpu_usage(self.m_compute_node))

    def test_no_metric_raise_error(self):
        """Test raising error when specified meter does not exist"""

        t_grafana = grafana.GrafanaHelper(osc=mock.Mock())

        self.assertRaises(exception.MetricNotAvailable,
                          t_grafana.statistic_aggregation,
                          self.m_compute_node,
                          'none existing meter', 60)

    @mock.patch.object(grafana.GrafanaHelper, '_request')
    def test_get_metric_raise_error(self, m_request):
        """Test raising error when endpoint unable to deliver data for metric

        """

        m_request.return_value.content = "{}"

        t_grafana = grafana.GrafanaHelper(osc=mock.Mock())

        self.assertRaises(exception.NoSuchMetricForHost,
                          t_grafana.get_host_cpu_usage,
                          self.m_compute_node, 60)

    def test_metric_builder(self):
        """Creates valid and invalid sets of configuration for metrics

        Ensures that a valid metric entry can be configured even if multiple
        invalid configurations exist for other metrics.
        """

        self.m_conf.grafana_client.project_id_map = {
            'host_cpu_usage': 7221,
            'host_ram_usage': 7221,
            'instance_ram_allocated': 7221,
        }
        self.m_conf.grafana_client.database_map = {
            'host_cpu_usage': 'mock_db',
            'instance_cpu_usage': 'mock_db',
            'instance_ram_allocated': 'mock_db',
        }
        self.m_conf.grafana_client.attribute_map = {
            'host_cpu_usage': 'hostname',
            'host_power': 'hostname',
            'instance_ram_allocated': 'human_id',
        }
        self.m_conf.grafana_client.translator_map = {
            'host_cpu_usage': 'influxdb',
            'host_inlet_temp': 'influxdb',
            # validate that invalid entries don't get added
            'instance_ram_usage': 'dummy',
            'instance_ram_allocated': 'influxdb',
        }
        self.m_conf.grafana_client.query_map = {
            'host_cpu_usage': 'SHOW SERIES',
            'instance_ram_usage': 'SHOW SERIES',
            'instance_ram_allocated': 'SHOW SERIES',
        }

        expected_result = {
            'host_cpu_usage': {
                'db': 'mock_db',
                'project': 7221,
                'attribute': 'hostname',
                'translator': 'influxdb',
                'query': 'SHOW SERIES'},
            'instance_ram_allocated': {
                'db': 'mock_db',
                'project': 7221,
                'attribute': 'human_id',
                'translator': 'influxdb',
                'query': 'SHOW SERIES'},
        }

        t_grafana = grafana.GrafanaHelper(osc=mock.Mock())
        self.assertEqual(t_grafana.METRIC_MAP, expected_result)

    @mock.patch.object(grafana.GrafanaHelper, '_request')
    def test_statistic_aggregation(self, m_request):
        m_request.return_value.content = "{ \"results\": [{ \"series\": [{ " \
                                         "\"columns\": [\"time\",\"mean\"]," \
                                         "\"values\": [[1552500855000, " \
                                         "67.3550078657577]]}]}]}"

        t_grafana = grafana.GrafanaHelper(osc=mock.Mock())

        result = t_grafana.statistic_aggregation(
            self.m_compute_node, 'compute_node', 'host_cpu_usage', 60)
        self.assertEqual(result, 67.3550078657577)

    def test_get_host_cpu_usage(self):
        self.m_grafana.get_host_cpu_usage(self.m_compute_node, 60, 'min', 15)
        self.mock_aggregation.assert_called_once_with(
            self.m_compute_node, 'compute_node', 'host_cpu_usage', 60, 'min',
            15)

    def test_get_host_ram_usage(self):
        self.m_grafana.get_host_ram_usage(self.m_compute_node, 60,
                                          'min', 15)
        self.mock_aggregation.assert_called_once_with(
            self.m_compute_node, 'compute_node', 'host_ram_usage', 60, 'min',
            15)

    def test_get_host_outlet_temperature(self):
        self.m_grafana.get_host_outlet_temp(self.m_compute_node, 60,
                                            'min', 15)
        self.mock_aggregation.assert_called_once_with(
            self.m_compute_node, 'compute_node', 'host_outlet_temp', 60, 'min',
            15)

    def test_get_host_inlet_temperature(self):
        self.m_grafana.get_host_inlet_temp(self.m_compute_node, 60,
                                           'min', 15)
        self.mock_aggregation.assert_called_once_with(
            self.m_compute_node, 'compute_node', 'host_inlet_temp', 60, 'min',
            15)

    def test_get_host_airflow(self):
        self.m_grafana.get_host_airflow(self.m_compute_node, 60,
                                        'min', 15)
        self.mock_aggregation.assert_called_once_with(
            self.m_compute_node, 'compute_node', 'host_airflow', 60, 'min',
            15)

    def test_get_host_power(self):
        self.m_grafana.get_host_power(self.m_compute_node, 60,
                                      'min', 15)
        self.mock_aggregation.assert_called_once_with(
            self.m_compute_node, 'compute_node', 'host_power', 60, 'min',
            15)

    def test_get_instance_cpu_usage(self):
        self.m_grafana.get_instance_cpu_usage(self.m_compute_node, 60,
                                              'min', 15)
        self.mock_aggregation.assert_called_once_with(
            self.m_compute_node, 'instance', 'instance_cpu_usage', 60,
            'min', 15)

    def test_get_instance_ram_usage(self):
        self.m_grafana.get_instance_ram_usage(self.m_compute_node, 60,
                                              'min', 15)
        self.mock_aggregation.assert_called_once_with(
            self.m_compute_node, 'instance', 'instance_ram_usage', 60,
            'min', 15)

    def test_get_instance_ram_allocated(self):
        self.m_grafana.get_instance_ram_allocated(self.m_compute_node, 60,
                                                  'min', 15)
        self.mock_aggregation.assert_called_once_with(
            self.m_compute_node, 'instance', 'instance_ram_allocated', 60,
            'min', 15)

    def test_get_instance_l3_cache_usage(self):
        self.m_grafana.get_instance_l3_cache_usage(self.m_compute_node, 60,
                                                   'min', 15)
        self.mock_aggregation.assert_called_once_with(
            self.m_compute_node, 'instance', 'instance_l3_cache_usage', 60,
            'min', 15)

    def test_get_instance_root_disk_allocated(self):
        self.m_grafana.get_instance_root_disk_size(self.m_compute_node, 60,
                                                   'min', 15)
        self.mock_aggregation.assert_called_once_with(
            self.m_compute_node, 'instance', 'instance_root_disk_size', 60,
            'min', 15)
