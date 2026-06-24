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

from unittest import mock

from oslo_config import cfg

from watcher.decision_engine.datasources import base as datasource
from watcher.tests.unit import base


CONF = cfg.CONF


class TestBaseDatasourceHelper(base.BaseTestCase):
    def test_query_retry(self):
        exc = Exception()
        method = mock.Mock()
        # first call will fail but second will succeed
        method.side_effect = [exc, True]
        # Max 2 attempts
        CONF.set_override("query_max_retries", 2, group='watcher_datasources')
        # Reduce sleep time to 0
        CONF.set_override("query_interval", 0, group='watcher_datasources')

        helper = datasource.DataSourceBase()
        helper.query_retry_reset = mock.Mock()

        self.assertTrue(helper.query_retry(f=method))
        helper.query_retry_reset.assert_called_once_with(exc)

    def test_query_retry_exception(self):
        exc = Exception()
        method = mock.Mock()
        # only third call will succeed
        method.side_effect = [exc, exc, True]
        # Max 2 attempts
        CONF.set_override("query_max_retries", 2, group='watcher_datasources')
        # Reduce sleep time to 0
        CONF.set_override("query_interval", 0, group='watcher_datasources')

        helper = datasource.DataSourceBase()
        helper.query_retry_reset = mock.Mock()

        # Maximum number of retries exceeded query_retry should return None
        self.assertIsNone(helper.query_retry(f=method))
        # query_retry_reset should be called twice
        helper.query_retry_reset.assert_has_calls(
            [mock.call(exc), mock.call(exc)]
        )


class TestDataSourceBaseCache(base.BaseTestCase):
    def setUp(self):
        super().setUp()
        self.helper = datasource.DataSourceBase()
        self.helper._statistic_aggregation = mock.Mock(return_value=42.0)
        self.helper.query_retry_reset = mock.Mock()
        self.resource = mock.Mock(uuid='test-uuid-1')

    def test_statistic_aggregation_delegates_on_miss(self):
        result = self.helper.statistic_aggregation(
            resource=self.resource,
            resource_type='compute_node',
            meter_name='host_cpu_usage',
            period=300,
            aggregate='mean',
            granularity=300,
        )
        self.assertEqual(42.0, result)
        self.helper._statistic_aggregation.assert_called_once_with(
            resource=self.resource,
            resource_type='compute_node',
            meter_name='host_cpu_usage',
            period=300,
            aggregate='mean',
            granularity=300,
        )

    def test_statistic_aggregation_cache_hit(self):
        kwargs = dict(
            resource=self.resource,
            resource_type='compute_node',
            meter_name='host_cpu_usage',
            period=300,
            aggregate='mean',
            granularity=300,
        )
        first = self.helper.statistic_aggregation(**kwargs)
        second = self.helper.statistic_aggregation(**kwargs)
        self.assertEqual(42.0, first)
        self.assertEqual(42.0, second)
        # first gets from datasource, second from cache
        self.helper._statistic_aggregation.assert_called_once_with(
            resource=self.resource,
            resource_type='compute_node',
            meter_name='host_cpu_usage',
            period=300,
            aggregate='mean',
            granularity=300,
        )

    def test_inject_metric_returned_on_cache_hit(self):
        self.helper.inject_metric(
            resource_uuid=self.resource.uuid,
            metric='host_cpu_usage',
            aggregation='mean',
            period=300,
            value=75.5,
        )
        result = self.helper.statistic_aggregation(
            resource=self.resource,
            resource_type='compute_node',
            meter_name='host_cpu_usage',
            period=300,
            aggregate='mean',
        )
        self.assertEqual(75.5, result)
        self.helper._statistic_aggregation.assert_not_called()

    def test_inject_metric_simulated_flag_stored(self):
        self.helper.inject_metric(
            resource_uuid=self.resource.uuid,
            metric='host_cpu_usage',
            aggregation='mean',
            period=300,
            value=42.0,
            simulated=True,
        )
        self.assertTrue(
            self.helper._metric_cache.is_simulated(
                self.resource.uuid,
                'host_cpu_usage',
                aggregate='mean',
                period=300,
                granularity=300,
            )
        )

    def test_inject_metric_default_not_simulated(self):
        self.helper.inject_metric(
            resource_uuid=self.resource.uuid,
            metric='host_cpu_usage',
            aggregation='mean',
            period=300,
            value=42.0,
        )
        self.assertFalse(
            self.helper._metric_cache.is_simulated(
                self.resource.uuid,
                'host_cpu_usage',
                aggregate='mean',
                period=300,
                granularity=300,
            )
        )

    def test_statistic_aggregation_no_uuid_skips_cache(self):
        resource_no_uuid = mock.Mock(spec=[])
        self.helper._statistic_aggregation.return_value = 55.0
        result = self.helper.statistic_aggregation(
            resource=resource_no_uuid,
            resource_type='compute_node',
            meter_name='host_cpu_usage',
            period=300,
            aggregate='mean',
        )
        self.assertEqual(55.0, result)
        self.helper._statistic_aggregation.assert_called_once_with(
            resource=resource_no_uuid,
            resource_type='compute_node',
            meter_name='host_cpu_usage',
            period=300,
            aggregate='mean',
            granularity=300,
        )
        self.assertEqual(0, len(self.helper._metric_cache))
