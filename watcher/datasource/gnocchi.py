# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica
#
# Authors: Alexander Chadin <a.chadin@servionica.ru>
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

from datetime import datetime
from datetime import timedelta
import time

from oslo_config import cfg
from oslo_log import log

from watcher.common import clients
from watcher.common import utils as common_utils
from watcher.datasource import base

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class GnocchiHelper(base.DataSourceBase):

    NAME = 'gnocchi'
    METRIC_MAP = base.DataSourceBase.METRIC_MAP['gnocchi']

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.gnocchi = self.osc.gnocchi()

    def query_retry(self, f, *args, **kwargs):
        for i in range(CONF.gnocchi_client.query_max_retries):
            try:
                return f(*args, **kwargs)
            except Exception as e:
                LOG.exception(e)
                time.sleep(CONF.gnocchi_client.query_timeout)

    def check_availability(self):
        status = self.query_retry(self.gnocchi.status.get)
        if status:
            return 'available'
        else:
            return 'not available'

    def list_metrics(self):
        """List the user's meters."""
        response = self.query_retry(f=self.gnocchi.metric.list)
        if not response:
            return set()
        else:
            return set([metric['name'] for metric in response])

    def statistic_aggregation(self, resource_id=None, meter_name=None,
                              period=300, granularity=300, dimensions=None,
                              aggregation='mean', group_by='*'):
        """Representing a statistic aggregate by operators

        :param resource_id: id of resource to list statistics for.
        :param meter_name: meter name of which we want the statistics.
        :param period: Period in seconds over which to group samples.
        :param granularity: frequency of marking metric point, in seconds.
        :param dimensions: dimensions (dict). This param isn't used in
                           Gnocchi datasource.
        :param aggregation: Should be chosen in accordance with policy
                            aggregations.
        :param group_by: list of columns to group the metrics to be returned.
                         This param isn't used in Gnocchi datasource.
        :return: value of aggregated metric
        """

        stop_time = datetime.utcnow()
        start_time = stop_time - timedelta(seconds=(int(period)))

        if not common_utils.is_uuid_like(resource_id):
            kwargs = dict(query={"=": {"original_resource_id": resource_id}},
                          limit=1)
            resources = self.query_retry(
                f=self.gnocchi.resource.search, **kwargs)

            if not resources:
                LOG.warning("The {0} resource {1} could not be "
                            "found".format(self.NAME, resource_id))
                return

            resource_id = resources[0]['id']

        raw_kwargs = dict(
            metric=meter_name,
            start=start_time,
            stop=stop_time,
            resource_id=resource_id,
            granularity=granularity,
            aggregation=aggregation,
        )

        kwargs = {k: v for k, v in raw_kwargs.items() if k and v}

        statistics = self.query_retry(
            f=self.gnocchi.metric.get_measures, **kwargs)

        if statistics:
            # return value of latest measure
            # measure has structure [time, granularity, value]
            return statistics[-1][2]

    def get_host_cpu_usage(self, resource_id, period, aggregate,
                           granularity=300):
        meter_name = self.METRIC_MAP.get('host_cpu_usage')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregation=aggregate)

    def get_instance_cpu_usage(self, resource_id, period, aggregate,
                               granularity=300):
        meter_name = self.METRIC_MAP.get('instance_cpu_usage')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregation=aggregate)

    def get_host_memory_usage(self, resource_id, period, aggregate,
                              granularity=300):
        meter_name = self.METRIC_MAP.get('host_memory_usage')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregation=aggregate)

    def get_instance_memory_usage(self, resource_id, period, aggregate,
                                  granularity=300):
        meter_name = self.METRIC_MAP.get('instance_ram_usage')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregation=aggregate)

    def get_instance_l3_cache_usage(self, resource_id, period, aggregate,
                                    granularity=300):
        meter_name = self.METRIC_MAP.get('instance_l3_cache_usage')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregation=aggregate)

    def get_instance_ram_allocated(self, resource_id, period, aggregate,
                                   granularity=300):
        meter_name = self.METRIC_MAP.get('instance_ram_allocated')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregation=aggregate)

    def get_instance_root_disk_allocated(self, resource_id, period, aggregate,
                                         granularity=300):
        meter_name = self.METRIC_MAP.get('instance_root_disk_size')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregation=aggregate)

    def get_host_outlet_temperature(self, resource_id, period, aggregate,
                                    granularity=300):
        meter_name = self.METRIC_MAP.get('host_outlet_temp')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregation=aggregate)

    def get_host_inlet_temperature(self, resource_id, period, aggregate,
                                   granularity=300):
        meter_name = self.METRIC_MAP.get('host_inlet_temp')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregation=aggregate)

    def get_host_airflow(self, resource_id, period, aggregate,
                         granularity=300):
        meter_name = self.METRIC_MAP.get('host_airflow')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregation=aggregate)

    def get_host_power(self, resource_id, period, aggregate,
                       granularity=300):
        meter_name = self.METRIC_MAP.get('host_power')
        return self.statistic_aggregation(resource_id, meter_name, period,
                                          granularity, aggregation=aggregate)
