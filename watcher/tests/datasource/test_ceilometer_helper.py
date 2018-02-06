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

from __future__ import absolute_import
from __future__ import unicode_literals

import mock

from watcher.common import clients
from watcher.datasource import ceilometer as ceilometer_helper
from watcher.tests import base


@mock.patch.object(clients.OpenStackClients, 'ceilometer')
class TestCeilometerHelper(base.BaseTestCase):

    def test_build_query(self, mock_ceilometer):
        mock_ceilometer.return_value = mock.MagicMock()
        cm = ceilometer_helper.CeilometerHelper()
        expected = [{'field': 'user_id', 'op': 'eq', 'value': u'user_id'},
                    {'field': 'project_id', 'op': 'eq', 'value': u'tenant_id'},
                    {'field': 'resource_id', 'op': 'eq',
                     'value': u'resource_id'}]

        query = cm.build_query(user_id="user_id",
                               tenant_id="tenant_id",
                               resource_id="resource_id",
                               user_ids=["user_ids"],
                               tenant_ids=["tenant_ids"],
                               resource_ids=["resource_ids"])
        self.assertEqual(expected, query)

    def test_statistic_aggregation(self, mock_ceilometer):
        cm = ceilometer_helper.CeilometerHelper()
        ceilometer = mock.MagicMock()
        statistic = mock.MagicMock()
        expected_result = 100
        statistic[-1]._info = {'aggregate': {'avg': expected_result}}
        ceilometer.statistics.list.return_value = statistic
        mock_ceilometer.return_value = ceilometer
        cm = ceilometer_helper.CeilometerHelper()
        val = cm.statistic_aggregation(
            resource_id="INSTANCE_ID",
            meter_name="cpu_util",
            period="7300",
            granularity=None
        )
        self.assertEqual(expected_result, val)

    def test_get_last_sample(self, mock_ceilometer):
        ceilometer = mock.MagicMock()
        statistic = mock.MagicMock()
        expected_result = 100
        statistic[-1]._info = {'counter_volume': expected_result}
        ceilometer.samples.list.return_value = statistic
        mock_ceilometer.return_value = ceilometer
        cm = ceilometer_helper.CeilometerHelper()
        val = cm.get_last_sample_value(
            resource_id="id",
            meter_name="compute.node.percent"
        )
        self.assertEqual(expected_result, val)

    def test_get_last_sample_none(self, mock_ceilometer):
        ceilometer = mock.MagicMock()
        expected = []
        ceilometer.samples.list.return_value = expected
        mock_ceilometer.return_value = ceilometer
        cm = ceilometer_helper.CeilometerHelper()
        val = cm.get_last_sample_values(
            resource_id="id",
            meter_name="compute.node.percent"
        )
        self.assertEqual(expected, val)

    def test_statistic_list(self, mock_ceilometer):
        ceilometer = mock.MagicMock()
        expected_value = []
        ceilometer.statistics.list.return_value = expected_value
        mock_ceilometer.return_value = ceilometer
        cm = ceilometer_helper.CeilometerHelper()
        val = cm.statistic_list(meter_name="cpu_util")
        self.assertEqual(expected_value, val)

    @mock.patch.object(ceilometer_helper.CeilometerHelper,
                       'statistic_aggregation')
    def test_get_host_cpu_usage(self, mock_aggregation, mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()
        helper.get_host_cpu_usage('compute1', 600, 'mean')
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_cpu_usage'], 600, None,
            aggregate='mean')

    @mock.patch.object(ceilometer_helper.CeilometerHelper,
                       'statistic_aggregation')
    def test_get_instance_cpu_usage(self, mock_aggregation, mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()
        helper.get_instance_cpu_usage('compute1', 600, 'mean')
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['instance_cpu_usage'], 600, None,
            aggregate='mean')

    @mock.patch.object(ceilometer_helper.CeilometerHelper,
                       'statistic_aggregation')
    def test_get_host_memory_usage(self, mock_aggregation, mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()
        helper.get_host_memory_usage('compute1', 600, 'mean')
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_memory_usage'], 600, None,
            aggregate='mean')

    @mock.patch.object(ceilometer_helper.CeilometerHelper,
                       'statistic_aggregation')
    def test_get_instance_memory_usage(self, mock_aggregation,
                                       mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()
        helper.get_instance_memory_usage('compute1', 600, 'mean')
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['instance_ram_usage'], 600, None,
            aggregate='mean')

    @mock.patch.object(ceilometer_helper.CeilometerHelper,
                       'statistic_aggregation')
    def test_get_instance_l3_cache_usage(self, mock_aggregation,
                                         mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()
        helper.get_instance_l3_cache_usage('compute1', 600, 'mean')
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['instance_l3_cache_usage'], 600,
            None, aggregate='mean')

    @mock.patch.object(ceilometer_helper.CeilometerHelper,
                       'statistic_aggregation')
    def test_get_instance_ram_allocated(self, mock_aggregation,
                                        mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()
        helper.get_instance_ram_allocated('compute1', 600, 'mean')
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['instance_ram_allocated'], 600, None,
            aggregate='mean')

    @mock.patch.object(ceilometer_helper.CeilometerHelper,
                       'statistic_aggregation')
    def test_get_instance_root_disk_allocated(self, mock_aggregation,
                                              mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()
        helper.get_instance_root_disk_allocated('compute1', 600, 'mean')
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['instance_root_disk_size'], 600,
            None, aggregate='mean')

    @mock.patch.object(ceilometer_helper.CeilometerHelper,
                       'statistic_aggregation')
    def test_get_host_outlet_temperature(self, mock_aggregation,
                                         mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()
        helper.get_host_outlet_temperature('compute1', 600, 'mean')
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_outlet_temp'], 600, None,
            aggregate='mean')

    @mock.patch.object(ceilometer_helper.CeilometerHelper,
                       'statistic_aggregation')
    def test_get_host_inlet_temperature(self, mock_aggregation,
                                        mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()
        helper.get_host_inlet_temperature('compute1', 600, 'mean')
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_inlet_temp'], 600, None,
            aggregate='mean')

    @mock.patch.object(ceilometer_helper.CeilometerHelper,
                       'statistic_aggregation')
    def test_get_host_airflow(self, mock_aggregation, mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()
        helper.get_host_airflow('compute1', 600, 'mean')
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_airflow'], 600, None,
            aggregate='mean')

    @mock.patch.object(ceilometer_helper.CeilometerHelper,
                       'statistic_aggregation')
    def test_get_host_power(self, mock_aggregation, mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()
        helper.get_host_power('compute1', 600, 'mean')
        mock_aggregation.assert_called_once_with(
            'compute1', helper.METRIC_MAP['host_power'], 600, None,
            aggregate='mean')

    def test_check_availability(self, mock_ceilometer):
        ceilometer = mock.MagicMock()
        ceilometer.resources.list.return_value = True
        mock_ceilometer.return_value = ceilometer
        helper = ceilometer_helper.CeilometerHelper()
        result = helper.check_availability()
        self.assertEqual('available', result)

    def test_check_availability_with_failure(self, mock_ceilometer):
        ceilometer = mock.MagicMock()
        ceilometer.resources.list.side_effect = Exception()
        mock_ceilometer.return_value = ceilometer
        helper = ceilometer_helper.CeilometerHelper()

        self.assertEqual('not available', helper.check_availability())
