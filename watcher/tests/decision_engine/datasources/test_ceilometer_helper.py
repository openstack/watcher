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
from watcher.common import exception
from watcher.decision_engine.datasources import ceilometer as ceilometer_helper
from watcher.tests import base


@mock.patch.object(clients.OpenStackClients, 'ceilometer')
class TestCeilometerHelper(base.BaseTestCase):

    def setUp(self):
        super(TestCeilometerHelper, self).setUp()
        self.osc_mock = mock.Mock()
        self.helper = ceilometer_helper.CeilometerHelper(osc=self.osc_mock)
        stat_agg_patcher = mock.patch.object(
            self.helper, 'statistic_aggregation',
            spec=ceilometer_helper.CeilometerHelper.statistic_aggregation)
        self.mock_aggregation = stat_agg_patcher.start()
        self.addCleanup(stat_agg_patcher.stop)

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
        ceilometer = mock.MagicMock()
        statistic = mock.MagicMock()
        expected_result = 100
        statistic[-1]._info = {'aggregate': {'avg': expected_result}}
        ceilometer.statistics.list.return_value = statistic
        mock_ceilometer.return_value = ceilometer
        cm = ceilometer_helper.CeilometerHelper()
        val = cm.statistic_aggregation(
            resource=mock.Mock(id="INSTANCE_ID"),
            resource_type='instance',
            meter_name="instance_cpu_usage",
            period="7300",
            granularity=None
        )
        self.assertEqual(expected_result, val)

    def test_statistic_aggregation_metric_unavailable(self, mock_ceilometer):
        helper = ceilometer_helper.CeilometerHelper()

        # invalidate instance_cpu_usage in metric map
        original_metric_value = helper.METRIC_MAP.get('instance_cpu_usage')
        helper.METRIC_MAP.update(
            instance_cpu_usage=None
        )

        self.assertRaises(
            exception.MetricNotAvailable,
            helper.statistic_aggregation, resource=mock.Mock(id="INSTANCE_ID"),
            resource_type='instance', meter_name="instance_cpu_usage",
            period="7300",
            granularity=None
        )

        # restore the metric map as it is a static attribute that does not get
        # restored between unit tests!
        helper.METRIC_MAP.update(
            instance_cpu_usage=original_metric_value
        )

    def test_get_host_cpu_usage(self, mock_ceilometer):
        self.helper.get_host_cpu_usage('compute1', 600, 'mean')
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_cpu_usage', 600, 'mean', None)

    def test_get_host_ram_usage(self, mock_ceilometer):
        self.helper.get_host_ram_usage('compute1', 600, 'mean')
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_ram_usage', 600, 'mean', None)

    def test_get_host_outlet_temp(self, mock_ceilometer):
        self.helper.get_host_outlet_temp('compute1', 600, 'mean')
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_outlet_temp', 600, 'mean', None)

    def test_get_host_inlet_temp(self, mock_ceilometer):
        self.helper.get_host_inlet_temp('compute1', 600, 'mean')
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_inlet_temp', 600, 'mean', None)

    def test_get_host_airflow(self, mock_ceilometer):
        self.helper.get_host_airflow('compute1', 600, 'mean')
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_airflow', 600, 'mean', None)

    def test_get_host_power(self, mock_ceilometer):
        self.helper.get_host_power('compute1', 600, 'mean')
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'compute_node', 'host_power', 600, 'mean', None)

    def test_get_instance_cpu_usage(self, mock_ceilometer):
        self.helper.get_instance_cpu_usage('compute1', 600, 'mean')
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'instance', 'instance_cpu_usage', 600, 'mean',
            None)

    def test_get_instance_ram_usage(self, mock_ceilometer):
        self.helper.get_instance_ram_usage('compute1', 600, 'mean')
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'instance', 'instance_ram_usage', 600, 'mean',
            None)

    def test_get_instance_ram_allocated(self, mock_ceilometer):
        self.helper.get_instance_ram_allocated('compute1', 600, 'mean')
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'instance', 'instance_ram_allocated', 600, 'mean',
            None)

    def test_get_instance_l3_cache_usage(self, mock_ceilometer):
        self.helper.get_instance_l3_cache_usage('compute1', 600, 'mean')
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'instance', 'instance_l3_cache_usage', 600, 'mean',
            None)

    def test_get_instance_root_disk_size(self, mock_ceilometer):
        self.helper.get_instance_root_disk_size('compute1', 600, 'mean')
        self.mock_aggregation.assert_called_once_with(
            'compute1', 'instance', 'instance_root_disk_size', 600, 'mean',
            None)

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
