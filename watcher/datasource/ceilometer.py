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
from oslo_utils import timeutils

from watcher._i18n import _
from watcher.common import clients
from watcher.common import exception


class CeilometerHelper(object):
    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.ceilometer = self.osc.ceilometer()

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

        user_ids = user_ids or []
        tenant_ids = tenant_ids or []
        resource_ids = resource_ids or []

        query = []
        if user_id:
            user_ids = [user_id]
        for u_id in user_ids:
            query.append({"field": "user_id", "op": "eq", "value": u_id})

        if tenant_id:
            tenant_ids = [tenant_id]
        for t_id in tenant_ids:
            query.append({"field": "project_id", "op": "eq", "value": t_id})

        if resource_id:
            resource_ids = [resource_id]
        for r_id in resource_ids:
            query.append({"field": "resource_id", "op": "eq", "value": r_id})

        start_timestamp = None
        end_timestamp = None

        if start_time:
            start_timestamp = start_time
            if isinstance(start_time, datetime.datetime):
                start_timestamp = start_time.isoformat()

        if end_time:
            end_timestamp = end_time
            if isinstance(end_time, datetime.datetime):
                end_timestamp = end_time.isoformat()

        if (start_timestamp and end_timestamp and
                timeutils.parse_isotime(start_timestamp) >
                timeutils.parse_isotime(end_timestamp)):
            raise exception.Invalid(
                _("Invalid query: %(start_time)s > %(end_time)s") % dict(
                    start_time=start_timestamp, end_time=end_timestamp))

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
        except Exception:
            raise

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

    def meter_list(self, query=None):
        """List the user's meters."""
        meters = self.query_retry(f=self.ceilometer.meters.list,
                                  query=query)
        return meters

    def statistic_aggregation(self,
                              resource_id,
                              meter_name,
                              period,
                              aggregate='avg'):
        """Representing a statistic aggregate by operators

        :param resource_id: id of resource to list statistics for.
        :param meter_name: Name of meter to list statistics for.
        :param period: Period in seconds over which to group samples.
        :param aggregate: Available aggregates are: count, cardinality,
                           min, max, sum, stddev, avg. Defaults to avg.
        :return: Return the latest statistical data, None if no data.
        """

        end_time = datetime.datetime.utcnow()
        start_time = end_time - datetime.timedelta(seconds=int(period))
        query = self.build_query(
            resource_id=resource_id, start_time=start_time, end_time=end_time)
        statistic = self.query_retry(f=self.ceilometer.statistics.list,
                                     meter_name=meter_name,
                                     q=query,
                                     period=period,
                                     aggregates=[
                                         {'func': aggregate}])

        item_value = None
        if statistic:
            item_value = statistic[-1]._info.get('aggregate').get(aggregate)
        return item_value

    def get_last_sample_values(self, resource_id, meter_name, limit=1):
        samples = self.query_sample(meter_name=meter_name,
                                    query=self.build_query(resource_id),
                                    limit=limit)
        values = []
        for index, sample in enumerate(samples):
            values.append(
                {'sample_%s' % index: {
                    'timestamp': sample._info['timestamp'],
                    'value': sample._info['counter_volume']}})
        return values

    def get_last_sample_value(self, resource_id, meter_name):
        samples = self.query_sample(meter_name=meter_name,
                                    query=self.build_query(resource_id))
        if samples:
            return samples[-1]._info['counter_volume']
        else:
            return False
