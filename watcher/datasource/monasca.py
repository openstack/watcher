# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
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

from monascaclient import exc

from watcher.common import clients
from watcher.common import exception
from watcher.datasource import base


class MonascaHelper(base.DataSourceBase):

    NAME = 'monasca'
    METRIC_MAP = base.DataSourceBase.METRIC_MAP['monasca']

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.monasca = self.osc.monasca()

    def query_retry(self, f, *args, **kwargs):
        try:
            return f(*args, **kwargs)
        except exc.Unauthorized:
            self.osc.reset_clients()
            self.monasca = self.osc.monasca()
            return f(*args, **kwargs)
        except Exception:
            raise

    def _format_time_params(self, start_time, end_time, period):
        """Format time-related params to the correct Monasca format

        :param start_time: Start datetime from which metrics will be used
        :param end_time: End datetime from which metrics will be used
        :param period: interval in seconds (int)
        :return: start ISO time, end ISO time, period
        """

        if not period:
            period = int(datetime.timedelta(hours=3).total_seconds())
        if not start_time:
            start_time = (
                datetime.datetime.utcnow() -
                datetime.timedelta(seconds=period))

        start_timestamp = None if not start_time else start_time.isoformat()
        end_timestamp = None if not end_time else end_time.isoformat()

        return start_timestamp, end_timestamp, period

    def check_availability(self):
        try:
            self.query_retry(self.monasca.metrics.list)
        except Exception:
            return 'not available'
        return 'available'

    def list_metrics(self):
        # TODO(alexchadin): this method should be implemented in accordance to
        # monasca API.
        pass

    def statistics_list(self, meter_name, dimensions, start_time=None,
                        end_time=None, period=None,):
        """List of statistics."""
        start_timestamp, end_timestamp, period = self._format_time_params(
            start_time, end_time, period
        )
        raw_kwargs = dict(
            name=meter_name,
            start_time=start_timestamp,
            end_time=end_timestamp,
            dimensions=dimensions,
        )

        kwargs = {k: v for k, v in raw_kwargs.items() if k and v}

        statistics = self.query_retry(
            f=self.monasca.metrics.list_measurements, **kwargs)

        return statistics

    def statistic_aggregation(self, resource_id=None, meter_name=None,
                              period=300, granularity=300, dimensions=None,
                              aggregation='avg', group_by='*'):
        """Representing a statistic aggregate by operators

        :param resource_id: id of resource to list statistics for.
                            This param isn't used in Monasca datasource.
        :param meter_name: meter names of which we want the statistics.
        :param period: Sampling `period`: In seconds. If no period is given,
                       only one aggregate statistic is returned. If given, a
                       faceted result will be returned, divided into given
                       periods. Periods with no data are ignored.
        :param granularity: frequency of marking metric point, in seconds.
                            This param isn't used in Ceilometer datasource.
        :param dimensions: dimensions (dict).
        :param aggregation: Should be either 'avg', 'count', 'min' or 'max'.
        :param group_by: list of columns to group the metrics to be returned.
        :return: A list of dict with each dict being a distinct result row
        """

        if dimensions is None:
            raise exception.UnsupportedDataSource(datasource='Monasca')

        stop_time = datetime.datetime.utcnow()
        start_time = stop_time - datetime.timedelta(seconds=(int(period)))

        if aggregation == 'mean':
            aggregation = 'avg'

        raw_kwargs = dict(
            name=meter_name,
            start_time=start_time.isoformat(),
            end_time=stop_time.isoformat(),
            dimensions=dimensions,
            period=period,
            statistics=aggregation,
            group_by=group_by,
        )

        kwargs = {k: v for k, v in raw_kwargs.items() if k and v}

        statistics = self.query_retry(
            f=self.monasca.metrics.list_statistics, **kwargs)

        cpu_usage = None
        for stat in statistics:
            avg_col_idx = stat['columns'].index(aggregation)
            values = [r[avg_col_idx] for r in stat['statistics']]
            value = float(sum(values)) / len(values)
            cpu_usage = value

        return cpu_usage

    def get_host_cpu_usage(self, resource_id, period, aggregate,
                           granularity=None):
        metric_name = self.METRIC_MAP.get('host_cpu_usage')
        node_uuid = resource_id.split('_')[0]
        return self.statistic_aggregation(
            meter_name=metric_name,
            dimensions=dict(hostname=node_uuid),
            period=period,
            aggregation=aggregate
        )

    def get_instance_cpu_usage(self, resource_id, period, aggregate,
                               granularity=None):
        metric_name = self.METRIC_MAP.get('instance_cpu_usage')

        return self.statistic_aggregation(
            meter_name=metric_name,
            dimensions=dict(resource_id=resource_id),
            period=period,
            aggregation=aggregate
        )

    def get_host_memory_usage(self, resource_id, period, aggregate,
                              granularity=None):
        raise NotImplementedError

    def get_instance_memory_usage(self, resource_id, period, aggregate,
                                  granularity=None):
        raise NotImplementedError

    def get_instance_l3_cache_usage(self, resource_id, period, aggregate,
                                    granularity=None):
        raise NotImplementedError

    def get_instance_ram_allocated(self, resource_id, period, aggregate,
                                   granularity=None):
        raise NotImplementedError

    def get_instance_root_disk_allocated(self, resource_id, period, aggregate,
                                         granularity=None):
        raise NotImplementedError

    def get_host_outlet_temperature(self, resource_id, period, aggregate,
                                    granularity=None):
        raise NotImplementedError

    def get_host_inlet_temperature(self, resource_id, period, aggregate,
                                   granularity=None):
        raise NotImplementedError

    def get_host_airflow(self, resource_id, period, aggregate,
                         granularity=None):
        raise NotImplementedError

    def get_host_power(self, resource_id, period, aggregate,
                       granularity=None):
        raise NotImplementedError
