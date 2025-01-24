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
            "100 - (avg by (instance)(rate(node_cpu_seconds_total"
            "{mode='idle',instance='10.0.1.2:9100'}[300s])) * 100)")

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
        expected_fqdn_map = {'foo.controlplane.domain': '10.1.2.1:9100',
                             'bar.controlplane.domain': '10.1.2.2:9100',
                             'baz.controlplane.domain': '10.1.2.3:9100'}
        expected_host_map = {'foo': '10.1.2.1:9100',
                             'bar': '10.1.2.2:9100',
                             'baz': '10.1.2.3:9100'}
        helper = prometheus_helper.PrometheusHelper()
        self.assertEqual(helper.prometheus_fqdn_instance_map,
                         expected_fqdn_map)
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
        self.assertEqual({}, helper.prometheus_fqdn_instance_map)
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
        expected_fqdn_map = {'ena': '10.1.2.1:9100',
                             'dyo': '10.1.2.2:9100'}
        self.assertEqual(
            helper.prometheus_fqdn_instance_map, expected_fqdn_map)
        self.assertEqual({}, helper.prometheus_host_instance_map)

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
        expected_fqdn_map = {'foo.controlplane.domain': '10.1.2.1:9100',
                             'bar.controlplane.domain': '10.1.2.2:9100'}
        expected_host_map = {'foo': '10.1.2.1:9100',
                             'bar': '10.1.2.2:9100'}
        cfg.CONF.prometheus_client.fqdn_label = 'custom_fqdn_label'
        helper = prometheus_helper.PrometheusHelper()
        self.assertEqual(helper.prometheus_fqdn_instance_map,
                         expected_fqdn_map)
        self.assertEqual(helper.prometheus_host_instance_map,
                         expected_host_map)

    def test_resolve_prometheus_instance_label(self):
        expected_instance_label = '10.0.1.2:9100'
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
            "100 - (avg by (instance)(rate(node_cpu_seconds_total"
            "{mode='idle',instance='a_host'}[111s])) * 100)")
        result = self.helper._build_prometheus_query(
            'avg', 'node_cpu_seconds_total', 'a_host', '111')
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_node_cpu_max_agg(self):
        expected_query = (
            "100 - (max by (instance)(rate(node_cpu_seconds_total"
            "{mode='idle',instance='b_host'}[444s])) * 100)")
        result = self.helper._build_prometheus_query(
            'max', 'node_cpu_seconds_total', 'b_host', '444')
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_node_memory_avg_agg(self):
        expected_query = (
            "(node_memory_MemTotal_bytes{instance='c_host'} - avg_over_time"
            "(node_memory_MemAvailable_bytes{instance='c_host'}[555s])) "
            "/ 1024 / 1024")
        result = self.helper._build_prometheus_query(
            'avg', 'node_memory_MemAvailable_bytes', 'c_host', '555')
        self.assertEqual(result, expected_query)

    def test_build_prometheus_query_node_memory_min_agg(self):
        expected_query = (
            "(node_memory_MemTotal_bytes{instance='d_host'} - min_over_time"
            "(node_memory_MemAvailable_bytes{instance='d_host'}[222s])) "
            "/ 1024 / 1024")
        result = self.helper._build_prometheus_query(
            'min', 'node_memory_MemAvailable_bytes', 'd_host', '222')
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
