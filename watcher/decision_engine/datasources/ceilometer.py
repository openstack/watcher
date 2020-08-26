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

from oslo_log import log
from oslo_utils import timeutils

from watcher._i18n import _
from watcher.common import clients
from watcher.common import exception
from watcher.decision_engine.datasources import base


LOG = log.getLogger(__name__)


try:
    from ceilometerclient import exc
    HAS_CEILCLIENT = True
except ImportError:
    HAS_CEILCLIENT = False


class CeilometerHelper(base.DataSourceBase):

    NAME = 'ceilometer'
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
        self.ceilometer = self.osc.ceilometer()
        LOG.warning("Ceilometer API is deprecated and Ceilometer Datasource "
                    "module is no longer maintained. We recommend to use "
                    "Gnocchi instead.")

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

    def query_retry_reset(self, exception_instance):
        if isinstance(exception_instance, exc.HTTPUnauthorized):
            self.osc.reset_clients()
            self.ceilometer = self.osc.ceilometer()

    def list_metrics(self):
        """List the user's meters."""
        meters = self.query_retry(f=self.ceilometer.meters.list)
        if not meters:
            return set()
        else:
            return meters

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

    def statistic_aggregation(self, resource=None, resource_type=None,
                              meter_name=None, period=300, granularity=300,
                              aggregate='mean'):
        end_time = datetime.datetime.utcnow()
        start_time = end_time - datetime.timedelta(seconds=int(period))

        meter = self._get_meter(meter_name)

        if aggregate == 'mean':
            aggregate = 'avg'
        elif aggregate == 'count':
            aggregate = 'avg'
            LOG.warning('aggregate type count not supported by ceilometer,'
                        ' replaced with mean.')

        resource_id = resource.uuid
        if resource_type == 'compute_node':
            resource_id = "%s_%s" % (resource.hostname, resource.hostname)

        query = self.build_query(
            resource_id=resource_id, start_time=start_time, end_time=end_time)
        statistic = self.query_retry(f=self.ceilometer.statistics.list,
                                     meter_name=meter,
                                     q=query,
                                     period=period,
                                     aggregates=[
                                         {'func': aggregate}])

        item_value = None
        if statistic:
            item_value = statistic[-1]._info.get('aggregate').get(aggregate)
            if meter_name == 'host_airflow':
                # Airflow from hardware.ipmi.node.airflow is reported as
                # 1/10 th of actual CFM
                item_value *= 10
        return item_value

    def statistic_series(self, resource=None, resource_type=None,
                         meter_name=None, start_time=None, end_time=None,
                         granularity=300):
        raise NotImplementedError(
            _('Ceilometer helper does not support statistic series method'))

    def get_host_cpu_usage(self, resource, period,
                           aggregate, granularity=None):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_cpu_usage', period,
            aggregate, granularity)

    def get_host_ram_usage(self, resource, period,
                           aggregate, granularity=None):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_ram_usage', period,
            aggregate, granularity)

    def get_host_outlet_temp(self, resource, period,
                             aggregate, granularity=None):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_outlet_temp', period,
            aggregate, granularity)

    def get_host_inlet_temp(self, resource, period,
                            aggregate, granularity=None):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_inlet_temp', period,
            aggregate, granularity)

    def get_host_airflow(self, resource, period,
                         aggregate, granularity=None):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_airflow', period,
            aggregate, granularity)

    def get_host_power(self, resource, period,
                       aggregate, granularity=None):

        return self.statistic_aggregation(
            resource, 'compute_node', 'host_power', period,
            aggregate, granularity)

    def get_instance_cpu_usage(self, resource, period,
                               aggregate, granularity=None):

        return self.statistic_aggregation(
            resource, 'instance', 'instance_cpu_usage', period,
            aggregate, granularity)

    def get_instance_ram_usage(self, resource, period,
                               aggregate, granularity=None):

        return self.statistic_aggregation(
            resource, 'instance', 'instance_ram_usage', period,
            aggregate, granularity)

    def get_instance_ram_allocated(self, resource, period,
                                   aggregate, granularity=None):

        return self.statistic_aggregation(
            resource, 'instance', 'instance_ram_allocated', period,
            aggregate, granularity)

    def get_instance_l3_cache_usage(self, resource, period,
                                    aggregate, granularity=None):

        return self.statistic_aggregation(
            resource, 'instance', 'instance_l3_cache_usage', period,
            aggregate, granularity)

    def get_instance_root_disk_size(self, resource, period,
                                    aggregate, granularity=None):

        return self.statistic_aggregation(
            resource, 'instance', 'instance_root_disk_size', period,
            aggregate, granularity)
