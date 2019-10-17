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

from oslo_config import cfg
from oslo_log import log

from watcher.common import clients
from watcher.common import exception
from watcher.decision_engine.datasources import base

CONF = cfg.CONF
LOG = log.getLogger(__name__)


class GnocchiHelper(base.DataSourceBase):

    NAME = 'gnocchi'
    METRIC_MAP = dict(host_cpu_usage='compute.node.cpu.percent',
                      host_ram_usage='hardware.memory.used',
                      host_outlet_temp='hardware.ipmi.node.outlet_temperature',
                      host_inlet_temp='hardware.ipmi.node.temperature',
                      host_airflow='hardware.ipmi.node.airflow',
                      host_power='hardware.ipmi.node.power',
                      instance_cpu_usage='cpu_util',
                      instance_ram_usage='memory.resident',
                      instance_ram_allocated='memory',
                      instance_l3_cache_usage='cpu_l3_cache',
                      instance_root_disk_size='disk.root.size',
                      )

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.gnocchi = self.osc.gnocchi()

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

    def statistic_aggregation(self, resource=None, resource_type=None,
                              meter_name=None, period=300, aggregate='mean',
                              granularity=300):
        stop_time = datetime.utcnow()
        start_time = stop_time - timedelta(seconds=(int(period)))

        meter = self.METRIC_MAP.get(meter_name)
        if meter is None:
            raise exception.MetricNotAvailable(metric=meter_name)

        if aggregate == 'count':
            aggregate = 'mean'
            LOG.warning('aggregate type count not supported by gnocchi,'
                        ' replaced with mean.')

        resource_id = resource.uuid
        if resource_type == 'compute_node':
            resource_id = "%s_%s" % (resource.hostname, resource.hostname)
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
            metric=meter,
            start=start_time,
            stop=stop_time,
            resource_id=resource_id,
            granularity=granularity,
            aggregation=aggregate,
        )

        kwargs = {k: v for k, v in raw_kwargs.items() if k and v}

        statistics = self.query_retry(
            f=self.gnocchi.metric.get_measures, **kwargs)

        return_value = None
        if statistics:
            # return value of latest measure
            # measure has structure [time, granularity, value]
            return_value = statistics[-1][2]

            if meter_name is 'host_airflow':
                # Airflow from hardware.ipmi.node.airflow is reported as
                # 1/10 th of actual CFM
                return_value *= 10

        return return_value

    def get_host_cpu_usage(self, resource, period, aggregate,
                           granularity=300):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_cpu_usage', period,
            aggregate, granularity)

    def get_host_ram_usage(self, resource, period, aggregate,
                           granularity=300):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_ram_usage', period,
            aggregate, granularity)

    def get_host_outlet_temp(self, resource, period, aggregate,
                             granularity=300):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_outlet_temp', period,
            aggregate, granularity)

    def get_host_inlet_temp(self, resource, period, aggregate,
                            granularity=300):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_inlet_temp', period,
            aggregate, granularity)

    def get_host_airflow(self, resource, period, aggregate,
                         granularity=300):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_airflow', period,
            aggregate, granularity)

    def get_host_power(self, resource, period, aggregate,
                       granularity=300):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_power', period,
            aggregate, granularity)

    def get_instance_cpu_usage(self, resource, period, aggregate,
                               granularity=300):

        return self.statistic_aggregation(
            resource, 'instance', 'instance_cpu_usage', period,
            aggregate, granularity)

    def get_instance_ram_usage(self, resource, period, aggregate,
                               granularity=300):

        return self.statistic_aggregation(
            resource, 'instance', 'instance_ram_usage', period,
            aggregate, granularity)

    def get_instance_ram_allocated(self, resource, period, aggregate,
                                   granularity=300):

        return self.statistic_aggregation(
            resource, 'instance', 'instance_ram_allocated', period,
            aggregate, granularity)

    def get_instance_l3_cache_usage(self, resource, period, aggregate,
                                    granularity=300):

        return self.statistic_aggregation(
            resource, 'instance', 'instance_l3_cache_usage', period,
            aggregate, granularity)

    def get_instance_root_disk_size(self, resource, period, aggregate,
                                    granularity=300):

        return self.statistic_aggregation(
            resource, 'instance', 'instance_root_disk_size', period,
            aggregate, granularity)
