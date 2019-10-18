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

import datetime

from ceilometerclient import exc
from oslo_log import log
from oslo_utils import timeutils

from watcher._i18n import _
from watcher.common import clients
from watcher.common import exception
from watcher.datasource import base

LOG = log.getLogger(__name__)


class CeilometerHelper(base.DataSourceBase):

    NAME = 'ceilometer'
    METRIC_MAP = base.DataSourceBase.METRIC_MAP['ceilometer']

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.ceilometer = self.osc.ceilometer()

    @staticmethod
    def format_query(user_id, tenant_id, resource_id,
                     user_ids, tenant_ids, resource_ids):
        query = []

        def query_append(query, _id, _ids, field):
            if _id:
                _ids = [_id]
            for x_id in _ids:
                query.append({"field": field, "op": "eq", "value": x_id})

        query_append(query, user_id, (user_ids or []), "user_id")
        query_append(query, tenant_id, (tenant_ids or []), "project_id")
        query_append(query, resource_id, (resource_ids or []), "resource_id")

        return query

    def _timestamps(self, start_time, end_time):

        def _format_timestamp(_time):
            if _time:
                if isinstance(_time, datetime.datetime):
                    return _time.isoformat()
                return _time
            return None

        start_timestamp = _format_timestamp(start_time)
        end_timestamp = _format_timestamp(end_time)

        if ((start_timestamp is not None) and (end_timestamp is not None) and
                (timeutils.parse_isotime(start_timestamp) >
                 timeutils.parse_isotime(end_timestamp))):
            raise exception.Invalid(
                _("Invalid query: %(start_time)s > %(end_time)s") % dict(
                    start_time=start_timestamp, end_time=end_timestamp))
        return start_timestamp, end_timestamp

    def build_query(self, user_id=None, tenant_id=None, resource_id=None,
                    user_ids=None, tenant_ids=None, resource_ids=None,
                    start_time=None, end_time=None):
        """Returns query built from given parameters.

        This query can be then used for querying resources, meters and
        statistics.
        :param user_id: user_id, has a priority over list of ids
        :param tenant_id: tenant_id, has a priority over list of ids
        :param resource_id: resource_id, has a priority over list of ids
        :param user_ids: list of user_ids
        :param tenant_ids: list of tenant_ids
        :param resource_ids: list of resource_ids
        :param start_time: datetime from which measurements should be collected
        :param end_time: datetime until which measurements should be collected
        """

        query = self.format_query(user_id, tenant_id, resource_id,
                                  user_ids, tenant_ids, resource_ids)

        start_timestamp, end_timestamp = self._timestamps(start_time,
                                                          end_time)

        if start_timestamp:
            query.append({"field": "timestamp", "op": "ge",
                          "value": start_timestamp})
        if end_timestamp:
            query.append({"field": "timestamp", "op": "le",
                          "value": end_timestamp})
        return query

    def query_retry(self, f, *args, **kargs):
        try:
            return f(*args, **kargs)
        except exc.HTTPUnauthorized:
            self.osc.reset_clients()
            self.ceilometer = self.osc.ceilometer()
            return f(*args, **kargs)
        except Exception as e:
            LOG.exception(e)

    def check_availability(self):
        status = self.query_retry(self.ceilometer.resources.list)
        if status:
            return 'available'
        else:
            return 'not available'

    def query_sample(self, meter_name, query, limit=1):
        return self.query_retry(f=self.ceilometer.samples.list,
                                meter_name=meter_name,
                                limit=limit,
                                q=query)

    def statistic_list(self, meter_name, query=None, period=None):
        """List of statistics."""
        statistics = self.ceilometer.statistics.list(
            meter_name=meter_name,
            q=query,
            period=period)
        return statistics

    def list_metrics(self):
        """List the user's meters."""
        meters = self.query_retry(f=self.ceilometer.meters.list)
        if not meters:
            return set()
        else:
            return meters

    def statistic_aggregation(self, resource_id=None, meter_name=None,
                              period=300, granularity=300, dimensions=None,
                              aggregation='avg', group_by='*'):
        """Representing a statistic aggregate by operators

        :param resource_id: id of resource to list statistics for.
        :param meter_name: Name of meter to list statistics for.
        :param period: Period in seconds over which to group samples.
        :param granularity: frequency of marking metric point, in seconds.
                            This param isn't used in Ceilometer datasource.
        :param dimensions: dimensions (dict). This param isn't used in
                           Ceilometer datasource.
        :param aggregation: Available aggregates are: count, cardinality,
                            min, max, sum, stddev, avg. Defaults to avg.
        :param group_by: list of columns to group the metrics to be returned.
                         This param isn't used in Ceilometer datasource.
        :return: Return the latest statistical data, None if no data.
        """

        end_time = datetime.datetime.utcnow()
        if aggregation == 'mean':
            aggregation = 'avg'
        start_time = end_time - datetime.timedelta(seconds=int(period))
        query = self.build_query(
            resource_id=resource_id, start_time=start_time, end_time=end_time)
        statistic = self.query_retry(f=self.ceilometer.statistics.list,
                                     meter_name=meter_name,
                                     q=query,
                                     period=period,
                                     aggregates=[
                                         {'func': aggregation}])

        item_value = None
        if statistic:
            item_value = statistic[-1]._info.get('aggregate').get(aggregation)
        return item_value

    def get_last_sample_values(self, resource_id, meter_name, limit=1):
        samples = self.query_sample(
            meter_name=meter_name,
            query=self.build_query(resource_id=resource_id),
            limit=limit)
        values = []
        for index, sample in enumerate(samples):
            values.append(
                {'sample_%s' % index: {
                    'timestamp': sample._info['timestamp'],
                    'value': sample._info['counter_volume']}})
        return values

    def get_last_sample_value(self, resource_id, meter_name):
        samples = self.query_sample(
            meter_name=meter_name,
            query=self.build_query(resource_id=resource_id))
        if samples:
            return samples[-1]._info['counter_volume']
        else:
            return False

    def get_host_cpu_usage(self, resource_id, period, aggregate,
                           granularity=None):
        meter_name = self.METRIC_MAP.get('host_cpu_usage')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregate=aggregate)

    def get_instance_cpu_usage(self, resource_id, period, aggregate,
                               granularity=None):
        meter_name = self.METRIC_MAP.get('instance_cpu_usage')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregate=aggregate)

    def get_host_memory_usage(self, resource_id, period, aggregate,
                              granularity=None):
        meter_name = self.METRIC_MAP.get('host_memory_usage')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregate=aggregate)

    def get_instance_memory_usage(self, resource_id, period, aggregate,
                                  granularity=None):
        meter_name = self.METRIC_MAP.get('instance_ram_usage')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregate=aggregate)

    def get_instance_l3_cache_usage(self, resource_id, period, aggregate,
                                    granularity=None):
        meter_name = self.METRIC_MAP.get('instance_l3_cache_usage')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregate=aggregate)

    def get_instance_ram_allocated(self, resource_id, period, aggregate,
                                   granularity=None):
        meter_name = self.METRIC_MAP.get('instance_ram_allocated')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregate=aggregate)

    def get_instance_root_disk_allocated(self, resource_id, period, aggregate,
                                         granularity=None):
        meter_name = self.METRIC_MAP.get('instance_root_disk_size')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregate=aggregate)

    def get_host_outlet_temperature(self, resource_id, period, aggregate,
                                    granularity=None):
        meter_name = self.METRIC_MAP.get('host_outlet_temp')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregate=aggregate)

    def get_host_inlet_temperature(self, resource_id, period, aggregate,
                                   granularity=None):
        meter_name = self.METRIC_MAP.get('host_inlet_temp')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregate=aggregate)

    def get_host_airflow(self, resource_id, period, aggregate,
                         granularity=None):
        meter_name = self.METRIC_MAP.get('host_airflow')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregate=aggregate)

    def get_host_power(self, resource_id, period, aggregate,
                       granularity=None):
        meter_name = self.METRIC_MAP.get('host_power')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregate=aggregate)
