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

from concurrent.futures import ThreadPoolExecutor
import datetime
import parsedatetime

from influxdb import InfluxDBClient
from oslo_config import cfg
from watcher.metrics_engine.api.metrics_resource_collector import \
    AggregationFunction
from watcher.metrics_engine.api.metrics_resource_collector import Measure
from watcher.metrics_engine.api.metrics_resource_collector import \
    MetricsResourceCollector
from watcher.metrics_engine.framework.datasources.sql_ast.build_db_query import \
    DBQuery
from watcher.metrics_engine.framework.datasources.sql_ast.sql_ast import And
from watcher.metrics_engine.framework.datasources.sql_ast.sql_ast import \
    Condition
from watcher.openstack.common import log

LOG = log.getLogger(__name__)
CONF = cfg.CONF

WATCHER_INFLUXDB_COLLECTOR_OPTS = [
    cfg.StrOpt('hostname',
               default='localhost',
               help='The hostname to connect to InfluxDB'),
    cfg.IntOpt('port',
               default='8086',
               help='port to connect to InfluxDB, defaults to 8086'),
    cfg.StrOpt('username',
               default='root',
               help='user to connect, defaults to root'),
    cfg.StrOpt('password',
               default='root',
               help='password of the user, defaults to root'),
    cfg.StrOpt('database',
               default='indeed',
               help='database name to connect to'),
    cfg.BoolOpt('param ssl',
                default=False,
                help='use https instead of http to connect to InfluxDB'),
    cfg.IntOpt('timeout',
               default='5',
               help='number of seconds Requests'
                    'will wait for your client to establish a connection'),
    cfg.IntOpt('timeout',
               default='5',
               help='number of seconds Requests'
                    'will wait for your client to establish a connection'),
    cfg.BoolOpt('use_udp',
                default=False,
                help='use UDP to connect to InfluxDB'),
    cfg.IntOpt('udp_port',
               default='4444',
               help=' UDP port to connect to InfluxDB')
]

influxdb_collector_opt_group = cfg.OptGroup(
    name='watcher_influxdb_collector',
    title='Defines the parameters of the module collector')
CONF.register_group(influxdb_collector_opt_group)
CONF.register_opts(WATCHER_INFLUXDB_COLLECTOR_OPTS,
                   influxdb_collector_opt_group)


class InfluxDBCollector(MetricsResourceCollector):
    def __init__(self):
        self.executor = ThreadPoolExecutor(max_workers=3)

    def get_client(self):
        LOG.debug("InfluxDB " + str(CONF.watcher_influxdb_collector.hostname))
        influx = InfluxDBClient(CONF.watcher_influxdb_collector.hostname,
                                CONF.watcher_influxdb_collector.port,
                                CONF.watcher_influxdb_collector.username,
                                CONF.watcher_influxdb_collector.password,
                                CONF.watcher_influxdb_collector.database)
        if {u'name': u'' + CONF.watcher_influxdb_collector.database + ''} not \
                in influx.get_list_database():
            raise Exception("The selected database does not exist"
                            "or the user credentials supplied are wrong")
        return influx

    def convert(self, time):
        cal = parsedatetime.Calendar()
        time_struct, result = cal.parse(time)
        return datetime.datetime(*time_struct[:6]).ctime()

    def build_query(self,
                    measurement,
                    start_time=None,
                    end_time=None,
                    filters=None,
                    aggregation_function=None,
                    intervals=None):
        query = DBQuery(measurement)
        conditions = []
        if start_time is not None:
            c = Condition('time', '>', self.convert(start_time))
            conditions.append(c)
        if end_time is not None:
            c = Condition('time', '>', self.convert(end_time))
            conditions.append(c)
        if filters is not None:
            for f in filters:
                c = Condition(f.split('=')[0], '=', f.split('=')[1])
                conditions.append(c)
        if aggregation_function is not None:
            if aggregation_function == AggregationFunction.MEAN:
                query.select("mean(value)")
            elif aggregation_function == AggregationFunction.COUNT:
                query.select("count(value)")

        if intervals is not None:
            query.groupby("time(" + str(intervals) + ")")

        if len(conditions) == 1:
            query.where(conditions[0])
        elif len(conditions) != 0:
            _where = And(conditions[0], conditions[1])
            for i in range(2, len(conditions)):
                _where = And(_where, conditions[i])
            query.where(_where)
        LOG.debug(query)
        return query

    def get_measurement(self,
                        metric,
                        callback=None,
                        start_time=None,
                        end_time=None,
                        filters=None,
                        aggregation_function=None,
                        intervals=None):
        results = []
        client = self.get_client()
        query = self.build_query(metric, start_time, end_time, filters,
                                 aggregation_function, intervals)

        results_from_influx = client.query(query)

        for item in results_from_influx[None]:
            time = item.get('time', None)
            for field in ['value', 'count', 'min', 'max', 'mean']:
                value = item.get(field, None)
                if value is not None:
                    row = Measure(time, value)
                    if callback is not None:
                        self.executor.submit(callback, row)
                    else:
                        results.append(row)
        return results
