# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
#

import mock
from watcher.metrics_engine.api.metrics_resource_collector import \
    AggregationFunction
from watcher.metrics_engine.framework.datasources.influxdb_collector import \
    InfluxDBCollector

from watcher.tests import base


class TestInfluxDB(base.TestCase):
    def get_databases(self):
        return {'name': 'indeed'}

    def test_get_measurement(self):
        influx = InfluxDBCollector()
        influx.get_client = mock.MagicMock()
        influx.get_client.get_list_database = self.get_databases
        result = influx.get_measurement("")
        self.assertEqual(result, [])

    def test_build_query(self):
        influx = InfluxDBCollector()
        influx.get_client = mock.MagicMock()
        query = influx.build_query("cpu_compute")
        self.assertEqual(str(query), "SELECT * FROM \"cpu_compute\" ;")

    def test_build_query_aggregate(self):
        influx = InfluxDBCollector()
        influx.get_client = mock.MagicMock()
        query = influx.build_query("cpu_compute",
                                   aggregation_function=AggregationFunction.
                                   COUNT)
        self.assertEqual(str(query),
                         "SELECT count(value) FROM \"cpu_compute\" ;")

    def test_build_query_aggregate_intervals(self):
        influx = InfluxDBCollector()
        influx.get_client = mock.MagicMock()
        query = influx.build_query("cpu_compute",
                                   aggregation_function=AggregationFunction.
                                   COUNT,
                                   intervals="5m")
        self.assertEqual(str(query),
                         "SELECT count(value) FROM \"cpu_compute\"  "
                         "group by time(5m);")

    def test_build_query_aggregate_filters(self):
        influx = InfluxDBCollector()
        influx.get_client = mock.MagicMock()
        filters = ['host=server1']
        query = influx.build_query("cpu_compute",
                                   aggregation_function=AggregationFunction.
                                   COUNT,
                                   intervals="5m",
                                   filters=filters)
        self.assertEqual(str(query), 'SELECT count(value) FROM'
                                     ' \"cpu_compute" WHERE'
                                     ' host = \'server1\' group by time(5m);')

    def test_get_qusurement_start(self):
        influx = InfluxDBCollector()
        influx.get_client = mock.MagicMock()
        influx.get_client.get_list_database = self.get_databases
        result = influx.get_measurement("cpu_compute", start_time='now',
                                        end_time="now")
        self.assertEqual(result, [])
