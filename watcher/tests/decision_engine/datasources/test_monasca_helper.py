# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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
from datetime import datetime
from unittest import mock

from oslo_config import cfg

from watcher.common import clients
from watcher.common import exception
from watcher.decision_engine.datasources import monasca as monasca_helper
from watcher.tests import base

CONF = cfg.CONF


@mock.patch.object(clients.OpenStackClients, 'monasca')
class TestMonascaHelper(base.BaseTestCase):

    def setUp(self):
        super(TestMonascaHelper, self).setUp()
        self.osc_mock = mock.Mock()
        self.helper = monasca_helper.MonascaHelper(osc=self.osc_mock)
        stat_agg_patcher = mock.patch.object(
            self.helper, 'statistic_aggregation',
            spec=monasca_helper.MonascaHelper.statistic_aggregation)
        self.mock_aggregation = stat_agg_patcher.start()
        self.addCleanup(stat_agg_patcher.stop)

    def test_monasca_statistic_aggregation(self, mock_monasca):
        monasca = mock.MagicMock()
        expected_stat = [{
            'columns': ['timestamp', 'avg'],
            'dimensions': {
                'hostname': 'rdev-indeedsrv001',
                'service': 'monasca'},
            'id': '0',
            'name': 'cpu.percent',
            'statistics': [
                ['2016-07-29T12:45:00Z', 0.0],
                ['2016-07-29T12:50:00Z', 0.9],
                ['2016-07-29T12:55:00Z', 0.9]]}]

        monasca.metrics.list_statistics.return_value = expected_stat
        mock_monasca.return_value = monasca

        helper = monasca_helper.MonascaHelper()
        result = helper.statistic_aggregation(
            resource=mock.Mock(id='NODE_UUID'),
            resource_type='compute_node',
            meter_name='host_cpu_usage',
            period=7200,
            granularity=300,
            aggregate='mean',
        )
        self.assertEqual(0.6, result)

    def test_monasca_statistic_series(self, mock_monasca):
        monasca = mock.MagicMock()
        expected_stat = [{
            'columns': ['timestamp', 'avg'],
            'dimensions': {
                'hostname': 'rdev-indeedsrv001',
                'service': 'monasca'},
            'id': '0',
            'name': 'cpu.percent',
            'statistics': [
                ['2016-07-29T12:45:00Z', 0.0],
                ['2016-07-29T12:50:00Z', 0.9],
                ['2016-07-29T12:55:00Z', 0.9]]}]

        expected_result = {
            '2016-07-29T12:45:00Z': 0.0,
            '2016-07-29T12:50:00Z': 0.9,
            '2016-07-29T12:55:00Z': 0.9,
        }

        monasca.metrics.list_statistics.return_value = expected_stat
        mock_monasca.return_value = monasca

        start = datetime(year=2016, month=7, day=29, hour=12, minute=45)
        end = datetime(year=2016, month=7, day=29, hour=12, minute=55)

        helper = monasca_helper.MonascaHelper()
        result = helper.statistic_series(
            resource=mock.Mock(id='NODE_UUID'),
            resource_type='compute_node',
            meter_name='host_cpu_usage',
            start_time=start,
            end_time=end,
            granularity=300,
        )
        self.assertEqual(expected_result, result)

    def test_statistic_aggregation_metric_unavailable(self, mock_monasca):
        helper = monasca_helper.MonascaHelper()

        # invalidate host_cpu_usage in metric map
        original_metric_value = helper.METRIC_MAP.get('host_cpu_usage')
        helper.METRIC_MAP.update(
            host_cpu_usage=None
        )

        self.assertRaises(
            exception.MetricNotAvailable, helper.statistic_aggregation,
            resource=mock.Mock(id='NODE_UUID'), resource_type='compute_node',
            meter_name='host_cpu_usage', period=7200, granularity=300,
            aggregate='mean',
        )

        # restore the metric map as it is a static attribute that does not get
        # restored between unit tests!
        helper.METRIC_MAP.update(
            instance_cpu_usage=original_metric_value
        )

    def test_check_availability(self, mock_monasca):
        monasca = mock.MagicMock()
        monasca.metrics.list.return_value = True
        mock_monasca.return_value = monasca
        helper = monasca_helper.MonascaHelper()
        result = helper.check_availability()
        self.assertEqual('available', result)

    def test_check_availability_with_failure(self, mock_monasca):
        monasca = mock.MagicMock()
        monasca.metrics.list.side_effect = Exception()
        mock_monasca.return_value = monasca
        helper = monasca_helper.MonascaHelper()
        self.assertEqual('not available', helper.check_availability())

    def test_get_host_cpu_usage(self, mock_monasca):
        self.mock_aggregation.return_value = 0.6
        node = mock.Mock(id='compute1')
        cpu_usage = self.helper.get_host_cpu_usage(node, 600, 'mean')
        self.assertEqual(0.6, cpu_usage)

    def test_get_instance_cpu_usage(self, mock_monasca):
        self.mock_aggregation.return_value = 0.6
        node = mock.Mock(id='vm1')
        cpu_usage = self.helper.get_instance_cpu_usage(node, 600, 'mean')
        self.assertEqual(0.6, cpu_usage)
