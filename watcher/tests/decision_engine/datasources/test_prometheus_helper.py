# Copyright 2024 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#
from unittest import mock

from observabilityclient import prometheus_client
from oslo_config import cfg

from watcher.common import exception
from watcher.decision_engine.datasources import prometheus as prometheus_helper
from watcher.tests import base


class TestPrometheusHelper(base.BaseTestCase):

    def setUp(self):
        super(TestPrometheusHelper, self).setUp()
        with mock.patch.object(
                prometheus_client.PrometheusAPIClient, '_get',
                return_value={'data': {'activeTargets': [
                    {'labels': {
                        'fqdn': 'marios-env.controlplane.domain',
                        'instance': '10.0.1.2:9100', 'job': 'node',
                    }},
                    {'labels': {
                        'fqdn': 'marios-env-again.controlplane.domain',
                        'instance': 'localhost:9100', 'job': 'node'
                    }}
                ]}}):
            cfg.CONF.prometheus_client.host = "foobarbaz"
            cfg.CONF.prometheus_client.port = "1234"
            self.helper = prometheus_helper.PrometheusHelper()
        stat_agg_patcher = mock.patch.object(
            self.helper, 'statistic_aggregation',
            spec=prometheus_helper.PrometheusHelper.statistic_aggregation)
        self.mock_aggregation = stat_agg_patcher.start()
        self.addCleanup(stat_agg_patcher.stop)
        self.mock_instance = mock.Mock(
            uuid='uuid-0',
            memory=512,
            disk=2,
            vcpus=2)

    def test_unset_missing_prometheus_host(self):
        cfg.CONF.prometheus_client.port = '123'
        cfg.CONF.prometheus_client.host = None
        self.assertRaisesRegex(
            exception.MissingParameter, 'prometheus host and port must be '
                                        'set in watcher.conf',
            prometheus_helper.PrometheusHelper
        )
        cfg.CONF.prometheus_client.host = ''
        self.assertRaisesRegex(
            exception.MissingParameter, 'prometheus host and port must be '
                                        'set in watcher.conf',
            prometheus_helper.PrometheusHelper
        )

    def test_unset_missing_prometheus_port(self):
        cfg.CONF.prometheus_client.host = 'some.host.domain'
        cfg.CONF.prometheus_client.port = None
        self.assertRaisesRegex(
            exception.MissingParameter, 'prometheus host and port must be '
                                        'set in watcher.conf',
            prometheus_helper.PrometheusHelper
        )
        cfg.CONF.prometheus_client.port = ''
        self.assertRaisesRegex(
            exception.MissingParameter, 'prometheus host and port must be '
                                        'set in watcher.conf',
            prometheus_helper.PrometheusHelper
        )

    def test_invalid_prometheus_port(self):
        cfg.CONF.prometheus_client.host = "hostOK"
        cfg.CONF.prometheus_client.port = "123badPort"
        self.assertRaisesRegex(
            exception.InvalidParameter, "missing or invalid port number "
                                        "'123badPort'",
            prometheus_helper.PrometheusHelper
        )
        cfg.CONF.prometheus_client.port = "123456"
        self.assertRaisesRegex(
            exception.InvalidParameter, "missing or invalid port number "
                                        "'123456'",
            prometheus_helper.PrometheusHelper
        )

    def test_invalid_prometheus_host(self):
        cfg.CONF.prometheus_client.port = "123"
        cfg.CONF.prometheus_client.host = "-badhost"
        self.assertRaisesRegex(
            exception.InvalidParameter, "hostname '-badhost' "
                                        "failed regex match",
            prometheus_helper.PrometheusHelper
        )
        too_long_hostname = ("a" * 256)
        cfg.CONF.prometheus_client.host = too_long_hostname
        self.assertRaisesRegex(
            exception.InvalidParameter, ("hostname is too long: " +
                                         "'" + too_long_hostname + "'"),
            prometheus_helper.PrometheusHelper
        )

    @mock.patch.object(prometheus_client.PrometheusAPIClient, 'query')
    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_prometheus_statistic_aggregation(self, mock_prometheus_get,
                                              mock_prometheus_query):
        mock_node = mock.Mock(
            uuid='1234',
            hostname='marios-env.controlplane.domain')

        expected_cpu_usage = 3.2706140350701673

        mock_prom_metric = mock.Mock(
            labels={'instance': '10.0.1.2:9100'},
            timestamp=1731065985.408,
            value=expected_cpu_usage
        )

        mock_prometheus_query.return_value = [mock_prom_metric]
        mock_prometheus_get.return_value = {'data': {'activeTargets': [
            {'labels': {
                'fqdn': 'marios-env.controlplane.domain',
                'instance': '10.0.1.2:9100', 'job': 'node',
            }}]}}
        helper = prometheus_helper.PrometheusHelper()
        result = helper.statistic_aggregation(
            resource=mock_node,
            resource_type='compute_node',
            meter_name='host_cpu_usage',
            period=300,
            aggregate='mean',
            granularity=300,
        )
        self.assertEqual(expected_cpu_usage, result)
        mock_prometheus_query.assert_called_once_with(
            "100 - (avg by (fqdn)(rate(node_cpu_seconds_total"
            "{mode='idle',fqdn='marios-env.controlplane.domain'}[300s]))"
            " * 100)")

    @mock.patch.object(prometheus_client.PrometheusAPIClient, 'query')
    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_get_instance_cpu_usage(self, mock_prometheus_get,
                                    mock_prometheus_query):
        mock_instance = self.mock_instance
        expected_cpu_usage = 13.2706140350701673

        mock_prom_metric = mock.Mock(
            labels={'resource': 'uuid-0'},
            timestamp=1731065985.408,
            value=expected_cpu_usage
        )
        mock_prometheus_query.return_value = [mock_prom_metric]
        helper = prometheus_helper.PrometheusHelper()

        cpu_usage = helper.get_instance_cpu_usage(mock_instance)
        self.assertIsInstance(cpu_usage, float)
        self.assertEqual(expected_cpu_usage, cpu_usage)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, 'query')
    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_get_instance_ram_usage(self, mock_prometheus_get,
                                    mock_prometheus_query):

        mock_instance = self.mock_instance
        expected_ram_usage = 49.86

        mock_prom_metric = mock.Mock(
            labels={'resource': 'uuid-0'},
            timestamp=1731065985.408,
            value=expected_ram_usage
        )
        mock_prometheus_query.return_value = [mock_prom_metric]
        helper = prometheus_helper.PrometheusHelper()

        ram_usage = helper.get_instance_ram_usage(
            mock_instance, period=222, aggregate="max",
            granularity=200)
        self.assertIsInstance(ram_usage, float)
        self.assertEqual(expected_ram_usage, ram_usage)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, 'query')
    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_get_instance_ram_allocated(self, mock_prometheus_get,
                                        mock_prometheus_query):

        mock_instance = self.mock_instance
        helper = prometheus_helper.PrometheusHelper()
        ram_allocated = helper.get_instance_ram_allocated(mock_instance,
                                                          period=222,
                                                          aggregate="max")
        self.assertIsInstance(ram_allocated, float)
        self.assertEqual(512, ram_allocated)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, 'query')
    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_get_instance_root_disk_size(self, mock_prometheus_get,
                                         mock_prometheus_query):

        mock_instance = self.mock_instance
        helper = prometheus_helper.PrometheusHelper()
        disk_size = helper.get_instance_root_disk_size(mock_instance,
                                                       period=331,
                                                       aggregate="avg")
        self.assertIsInstance(disk_size, float)
        self.assertEqual(2, disk_size)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, 'query')
    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_prometheus_stt_agg_instance_cpu_usage(self, mock_prometheus_get,
                                                   mock_prometheus_query):
        mock_instance = self.mock_instance
        expected_cpu_usage = 13.2706140350701673

        mock_prom_metric = mock.Mock(
            labels={'resource': 'uuid-0'},
            timestamp=1731065985.408,
            value=expected_cpu_usage
        )
        mock_prometheus_query.return_value = [mock_prom_metric]
        helper = prometheus_helper.PrometheusHelper()
        result_cpu = helper.statistic_aggregation(
            resource=mock_instance,
            resource_type='instance',
            meter_name='instance_cpu_usage',
            period=300,
            granularity=300,
            aggregate='mean',
        )
        self.assertEqual(expected_cpu_usage, result_cpu)
        self.assertIsInstance(result_cpu, float)
        mock_prometheus_query.assert_called_once_with(
            "clamp_max((avg by (resource)(rate("
            "ceilometer_cpu{resource='uuid-0'}[300s]))"
            "/10e+8) *(100/2), 100)"
        )

    @mock.patch.object(prometheus_client.PrometheusAPIClient, 'query')
    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_prometheus_stt_agg_instance_ram_usage(self, mock_prometheus_get,
                                                   mock_prometheus_query):
        mock_instance = self.mock_instance
        expected_ram_usage = 49.86

        mock_prom_metric = mock.Mock(
            labels={'resource': 'uuid-0'},
            timestamp=1731065985.408,
            value=expected_ram_usage
        )
        mock_prometheus_query.return_value = [mock_prom_metric]
        helper = prometheus_helper.PrometheusHelper()
        result_ram_usage = helper.statistic_aggregation(
            resource=mock_instance,
            resource_type='instance',
            meter_name='instance_ram_usage',
            period=300,
            granularity=300,
            aggregate='mean',
        )
        self.assertEqual(expected_ram_usage, result_ram_usage)
        self.assertIsInstance(result_ram_usage, float)
        mock_prometheus_query.assert_called_with(
            "avg_over_time(ceilometer_memory_usage{resource='uuid-0'}[300s])"
        )

    @mock.patch.object(prometheus_client.PrometheusAPIClient, 'query')
    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_prometheus_stt_agg_instance_root_size(self, mock_prometheus_get,
                                                   mock_prometheus_query):
        mock_instance = self.mock_instance

        helper = prometheus_helper.PrometheusHelper()
        result_disk = helper.statistic_aggregation(
            resource=mock_instance,
            resource_type='instance',
            meter_name='instance_root_disk_size',
            period=300,
            granularity=300,
            aggregate='mean',
        )
        self.assertEqual(2, result_disk)
        self.assertIsInstance(result_disk, float)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, 'query')
    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_prometheus_stt_agg_instance_ram_alloc(self, mock_prometheus_get,
                                                   mock_prometheus_query):
        mock_instance = self.mock_instance

        helper = prometheus_helper.PrometheusHelper()
        result_memory = helper.statistic_aggregation(
            resource=mock_instance,
            resource_type='instance',
            meter_name='instance_ram_allocated',
            period=300,
            granularity=300,
            aggregate='mean',
        )
        self.assertEqual(512, result_memory)
        self.assertIsInstance(result_memory, float)

    def test_statistic_aggregation_metric_unavailable(self):
        self.assertRaisesRegex(
            NotImplementedError, 'does not support statistic_series',
            self.helper.statistic_series
        )

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_prometheus_list_metrics(self, mock_prometheus_get):
        expected_metrics = set(
            ['go_gc_duration_seconds', 'go_gc_duration_seconds_count',
             'go_gc_duration_seconds_sum', 'go_goroutines',]
        )
        mock_prometheus_get.return_value = {
            'status': 'success', 'data': [
                'go_gc_duration_seconds', 'go_gc_duration_seconds_count',
                'go_gc_duration_seconds_sum', 'go_goroutines',
            ]
        }
        result = self.helper.list_metrics()
        self.assertEqual(expected_metrics, result)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_prometheus_list_metrics_error(self, mock_prometheus_get):
        mock_prometheus_get.side_effect = (
            prometheus_client.PrometheusAPIClientError("nope"))
        result = self.helper.list_metrics()
        self.assertEqual(set(), result)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_prometheus_check_availability(self, mock_prometheus_get):
        mock_prometheus_get.return_value = {
            'status': 'success',
            'data': {
                'startTime': '2024-11-05T12:59:56.962333207Z',
                'CWD': '/prometheus', 'reloadConfigSuccess': True,
                'lastConfigTime': '2024-11-05T12:59:56Z',
                'corruptionCount': 0, 'goroutineCount': 30,
                'GOMAXPROCS': 8, 'GOMEMLIMIT': 9223372036854775807,
                'GOGC': '75', 'GODEBUG': '', 'storageRetention': '15d'
            }
        }
        result = self.helper.check_availability()
        self.assertEqual('available', result)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_prometheus_check_availability_error(self, mock_prometheus_get):
        mock_prometheus_get.side_effect = (
            prometheus_client.PrometheusAPIClientError("nope"))
        result = self.helper.check_availability()
        self.assertEqual('not available', result)

    def test_get_host_cpu_usage(self):
        cpu_use = self.helper.get_host_cpu_usage('someNode', 345, 'mean', 300)
        self.assertIsInstance(cpu_use, float)
        self.mock_aggregation.assert_called_once_with(
            'someNode', 'compute_node', 'host_cpu_usage', period=345,
            granularity=300, aggregate='mean')

    def test_get_host_cpu_usage_none(self):
        self.mock_aggregation.return_value = None
        cpu_use = self.helper.get_host_cpu_usage('someNode', 345, 'mean', 300)
        self.assertIsNone(cpu_use)

    def test_get_host_cpu_usage_max(self):
        cpu_use = self.helper.get_host_cpu_usage('theNode', 223, 'max', 100)
        self.assertIsInstance(cpu_use, float)
        self.mock_aggregation.assert_called_once_with(
            'theNode', 'compute_node', 'host_cpu_usage', period=223,
            granularity=100, aggregate='min')

    def test_get_host_cpu_usage_min(self):
        cpu_use = self.helper.get_host_cpu_usage('theNode', 223, 'min', 100)
        self.assertIsInstance(cpu_use, float)
        self.mock_aggregation.assert_called_once_with(
            'theNode', 'compute_node', 'host_cpu_usage', period=223,
            granularity=100, aggregate='max')

    def test_get_host_ram_usage(self):
        ram_use = self.helper.get_host_ram_usage(
            'anotherNode', 456, 'mean', 300)
        self.assertIsInstance(ram_use, float)
        self.mock_aggregation.assert_called_once_with(
            'anotherNode', 'compute_node', 'host_ram_usage', period=456,
            granularity=300, aggregate='mean')

    def test_get_host_ram_usage_none(self):
        self.mock_aggregation.return_value = None
        ram_use = self.helper.get_host_ram_usage('NOPE', 234, 'mean', 567)
        self.assertIsNone(ram_use, float)
        self.mock_aggregation.assert_called()
        self.mock_aggregation.assert_called_once_with(
            'NOPE', 'compute_node', 'host_ram_usage', period=234,
            granularity=567, aggregate='mean')

    def test_get_host_ram_usage_max(self):
        ram_use = self.helper.get_host_ram_usage(
            'aNode', 456, 'max', 300)
        self.assertIsInstance(ram_use, float)
        self.mock_aggregation.assert_called_once_with(
            'aNode', 'compute_node', 'host_ram_usage', period=456,
            granularity=300, aggregate='min')

    def test_get_host_ram_usage_min(self):
        ram_use = self.helper.get_host_ram_usage(
            'aNode', 456, 'min', 300)
        self.assertIsInstance(ram_use, float)
        self.mock_aggregation.assert_called_once_with(
            'aNode', 'compute_node', 'host_ram_usage', period=456,
            granularity=300, aggregate='max')

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_build_prometheus_fqdn_host_instance_map(
            self, mock_prometheus_get):
        mock_prometheus_get.return_value = {'data': {'activeTargets': [
            {'labels': {
                'fqdn': 'foo.controlplane.domain',
                'instance': '10.1.2.1:9100', 'job': 'node',
            }},
            {'labels': {
                'fqdn': 'bar.controlplane.domain',
                'instance': '10.1.2.2:9100', 'job': 'node',
            }},
            {'labels': {
                'fqdn': 'baz.controlplane.domain',
                'instance': '10.1.2.3:9100', 'job': 'node',
            }},
        ]}}
        expected_fqdn_list = {'foo.controlplane.domain',
                              'bar.controlplane.domain',
                              'baz.controlplane.domain'}
        expected_host_map = {'foo': 'foo.controlplane.domain',
                             'bar': 'bar.controlplane.domain',
                             'baz': 'baz.controlplane.domain'}
        helper = prometheus_helper.PrometheusHelper()
        self.assertEqual(helper.prometheus_fqdn_labels,
                         expected_fqdn_list)
        self.assertEqual(helper.prometheus_host_instance_map,
                         expected_host_map)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_build_prometheus_fqdn_host_instance_map_dupl_fqdn(
            self, mock_prometheus_get):
        mock_prometheus_get.return_value = {'data': {'activeTargets': [
            {'labels': {
                'fqdn': 'foo.controlplane.domain',
                'instance': '10.1.2.1:9100', 'job': 'node',
            }},
            {'labels': {
                'fqdn': 'foo.controlplane.domain',
                'instance': '10.1.2.1:9229', 'job': 'podman',
            }},
            {'labels': {
                'fqdn': 'bar.controlplane.domain',
                'instance': '10.1.2.2:9100', 'job': 'node',
            }},
            {'labels': {
                'fqdn': 'baz.controlplane.domain',
                'instance': '10.1.2.3:9100', 'job': 'node',
            }},
        ]}}
        expected_fqdn_list = {'foo.controlplane.domain',
                              'bar.controlplane.domain',
                              'baz.controlplane.domain'}
        expected_host_map = {'foo': 'foo.controlplane.domain',
                             'bar': 'bar.controlplane.domain',
                             'baz': 'baz.controlplane.domain'}
        helper = prometheus_helper.PrometheusHelper()
        self.assertEqual(helper.prometheus_fqdn_labels,
                         expected_fqdn_list)
        self.assertEqual(helper.prometheus_host_instance_map,
                         expected_host_map)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_missing_prometheus_fqdn_label(self, mock_prometheus_get):
        mock_prometheus_get.return_value = {'data': {'activeTargets': [
            {'labels': {
                'instance': '10.1.2.1:9100', 'job': 'node',
            }},
            {'labels': {
                'instance': '10.1.2.2:9100', 'job': 'node',
            }},
        ]}}
        helper = prometheus_helper.PrometheusHelper()
        self.assertEqual(set(), helper.prometheus_fqdn_labels)
        self.assertEqual({}, helper.prometheus_host_instance_map)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_using_hostnames_not_fqdn(self, mock_prometheus_get):
        mock_prometheus_get.return_value = {'data': {'activeTargets': [
            {'labels': {
                'fqdn': 'ena',
                'instance': '10.1.2.1:9100', 'job': 'node',
            }},
            {'labels': {
                'fqdn': 'dyo',
                'instance': '10.1.2.2:9100', 'job': 'node',
            }},
        ]}}
        helper = prometheus_helper.PrometheusHelper()
        expected_fqdn_list = {'ena', 'dyo'}
        self.assertEqual(
            helper.prometheus_fqdn_labels, expected_fqdn_list)
        self.assertEqual({}, helper.prometheus_host_instance_map)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_using_ips_not_fqdn(self, mock_prometheus_get):
        mock_prometheus_get.return_value = {'data': {'activeTargets': [
            {'labels': {
                'ip_label': '10.1.2.1',
                'instance': '10.1.2.1:9100', 'job': 'node',
            }},
            {'labels': {
                'ip_label': '10.1.2.2',
                'instance': '10.1.2.2:9100', 'job': 'node',
            }},
        ]}}
        cfg.CONF.prometheus_client.fqdn_label = 'ip_label'
        helper = prometheus_helper.PrometheusHelper()
        expected_fqdn_list = {'10.1.2.1', '10.1.2.2'}
        self.assertEqual(
            helper.prometheus_fqdn_labels, expected_fqdn_list)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_override_prometheus_fqdn_label(self, mock_prometheus_get):
        mock_prometheus_get.return_value = {'data': {'activeTargets': [
            {'labels': {
                'custom_fqdn_label': 'foo.controlplane.domain',
                'instance': '10.1.2.1:9100', 'job': 'node',
            }},
            {'labels': {
                'custom_fqdn_label': 'bar.controlplane.domain',
                'instance': '10.1.2.2:9100', 'job': 'node',
            }},
        ]}}
        expected_fqdn_list = {'foo.controlplane.domain',
                              'bar.controlplane.domain'}
        expected_host_map = {'foo': 'foo.controlplane.domain',
                             'bar': 'bar.controlplane.domain'}
        cfg.CONF.prometheus_client.fqdn_label = 'custom_fqdn_label'
        helper = prometheus_helper.PrometheusHelper()
        self.assertEqual(helper.prometheus_fqdn_labels,
                         expected_fqdn_list)
        self.assertEqual(helper.prometheus_host_instance_map,
                         expected_host_map)

    def test_resolve_prometheus_instance_label(self):
        expected_instance_label = 'marios-env.controlplane.domain'
        result = self.helper._resolve_prometheus_instance_label(
            'marios-env.controlplane.domain')
        self.assertEqual(result, expected_instance_label)
        result = self.helper._resolve_prometheus_instance_label(
            'marios-env')
        self.assertEqual(result, expected_instance_label)

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_resolve_prometheus_instance_label_none(self,
                                                    mock_prometheus_get):
        mock_prometheus_get.return_value = {'data': {'activeTargets': []}}
        result = self.helper._resolve_prometheus_instance_label('nope')
        self.assertIsNone(result)
        mock_prometheus_get.assert_called_once_with("targets?state=active")

    def test_build_prometheus_query_node_cpu_avg_agg(self):
        expected_query = (
            "100 - (avg by (fqdn)(rate(node_cpu_seconds_total"
            "{mode='idle',fqdn='a_host'}[111s])) * 100)")
        result = self.helper._build_prometheus_query(
            'avg', 'node_cpu_seconds_total', 'a_host', '111')
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_node_cpu_max_agg(self):
        expected_query = (
            "100 - (max by (fqdn)(rate(node_cpu_seconds_total"
            "{mode='idle',fqdn='b_host'}[444s])) * 100)")
        result = self.helper._build_prometheus_query(
            'max', 'node_cpu_seconds_total', 'b_host', '444')
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_node_memory_avg_agg(self):
        expected_query = (
            "(node_memory_MemTotal_bytes{fqdn='c_host'} - avg_over_time"
            "(node_memory_MemAvailable_bytes{fqdn='c_host'}[555s])) "
            "/ 1024")
        result = self.helper._build_prometheus_query(
            'avg', 'node_memory_MemAvailable_bytes', 'c_host', '555')
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_node_memory_min_agg(self):
        expected_query = (
            "(node_memory_MemTotal_bytes{fqdn='d_host'} - min_over_time"
            "(node_memory_MemAvailable_bytes{fqdn='d_host'}[222s])) "
            "/ 1024")
        result = self.helper._build_prometheus_query(
            'min', 'node_memory_MemAvailable_bytes', 'd_host', '222')
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_node_cpu_avg_agg_custom_label(self):
        self.helper.prometheus_fqdn_label = 'custom_fqdn_label'
        expected_query = (
            "100 - (avg by (custom_fqdn_label)(rate(node_cpu_seconds_total"
            "{mode='idle',custom_fqdn_label='a_host'}[111s])) * 100)")
        result = self.helper._build_prometheus_query(
            'avg', 'node_cpu_seconds_total', 'a_host', '111')
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_node_memory_min_agg_custom_label(self):
        self.helper.prometheus_fqdn_label = 'custom_fqdn'
        expected_query = (
            "(node_memory_MemTotal_bytes{custom_fqdn='d_host'} - min_over_time"
            "(node_memory_MemAvailable_bytes{custom_fqdn='d_host'}[222s])) "
            "/ 1024")
        result = self.helper._build_prometheus_query(
            'min', 'node_memory_MemAvailable_bytes', 'd_host', '222')
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_instance_memory_avg_agg(self):
        expected_query = (
            "avg_over_time(ceilometer_memory_usage{resource='uuid-0'}[555s])"
        )
        result = self.helper._build_prometheus_query(
            'avg', 'ceilometer_memory_usage', 'uuid-0', '555')
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_instance_memory_min_agg(self):
        expected_query = (
            "min_over_time(ceilometer_memory_usage{resource='uuid-0'}[222s])"
        )
        result = self.helper._build_prometheus_query(
            'min', 'ceilometer_memory_usage', 'uuid-0', '222')
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_instance_cpu_avg_agg(self):
        expected_query = (
            "clamp_max((avg by (resource)(rate("
            "ceilometer_cpu{resource='uuid-0'}[222s]))"
            "/10e+8) *(100/2), 100)"
        )
        result = self.helper._build_prometheus_query(
            'avg', 'ceilometer_cpu', 'uuid-0', '222',
            resource=self.mock_instance)
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_instance_cpu_max_agg(self):
        expected_query = (
            "clamp_max((max by (resource)(rate("
            "ceilometer_cpu{resource='uuid-0'}[555s]))"
            "/10e+8) *(100/4), 100)"
        )
        mock_instance = mock.Mock(
            uuid='uuid-0',
            memory=512,
            disk=2,
            vcpus=4)
        result = self.helper._build_prometheus_query(
            'max', 'ceilometer_cpu', 'uuid-0', '555', resource=mock_instance)
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_error(self):
        self.assertRaisesRegex(
            exception.InvalidParameter, 'Cannot process prometheus meter NOPE',
            self.helper._build_prometheus_query,
            'min', 'NOPE', 'the_host', '222'
        )
        self.assertRaisesRegex(
            exception.InvalidParameter, 'instance_label None, period 333',
            self.helper._build_prometheus_query,
            'min', 'node_cpu_seconds_total', None, '333'
        )

    def test_resolve_prometheus_aggregate_vanilla(self):
        result = self.helper._resolve_prometheus_aggregate('mean', 'foo')
        self.assertEqual(result, 'avg')
        result = self.helper._resolve_prometheus_aggregate('count', 'foo')
        self.assertEqual(result, 'avg')
        result = self.helper._resolve_prometheus_aggregate('max', 'foometric')
        self.assertEqual(result, 'max')
        result = self.helper._resolve_prometheus_aggregate('min', 'barmetric')
        self.assertEqual(result, 'min')

    def test_resolve_prometheus_aggregate_unknown(self):
        self.assertRaisesRegex(
            exception.InvalidParameter, 'Unknown Watcher aggregate NOPE.',
            self.helper._resolve_prometheus_aggregate, 'NOPE', 'some_meter')

    @mock.patch.object(prometheus_client.PrometheusAPIClient, '_get')
    def test_prometheus_query_custom_uuid_label(self, mock_prometheus_get):
        cfg.CONF.prometheus_client.instance_uuid_label = 'custom_uuid_label'
        expected_query = (
            "clamp_max((max by (custom_uuid_label)"
            "(rate(ceilometer_cpu{custom_uuid_label='uuid-0'}[555s]))"
            "/10e+8) *(100/4), 100)"
        )
        mock_instance = mock.Mock(
            uuid='uuid-0',
            memory=512,
            disk=2,
            vcpus=4)
        result = self.helper._build_prometheus_query(
            'max', 'ceilometer_cpu', 'uuid-0', '555', resource=mock_instance)
        self.assertEqual(result, expected_query)
