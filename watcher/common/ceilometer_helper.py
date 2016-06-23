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

from ceilometerclient import exc

from watcher.common import clients


class CeilometerHelper(object):
    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.ceilometer = self.osc.ceilometer()

    def build_query(self, user_id=None, tenant_id=None, resource_id=None,
                    user_ids=None, tenant_ids=None, resource_ids=None):
        """Returns query built from given parameters.

        This query can be then used for querying resources, meters and
        statistics.
        :Parameters:
        - `user_id`: user_id, has a priority over list of ids
        - `tenant_id`: tenant_id, has a priority over list of ids
        - `resource_id`: resource_id, has a priority over list of ids
        - `user_ids`: list of user_ids
        - `tenant_ids`: list of tenant_ids
        - `resource_ids`: list of resource_ids
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

        :param resource_id: id
        :param meter_name: meter names of which we want the statistics
        :param period: `period`: In seconds. If no period is given, only one
                       aggregate statistic is returned. If given, a faceted
                       result will be returned, divided into given periods.
                       Periods with no data are ignored.
        :param aggregate:
        :return:
        """

        query = self.build_query(resource_id=resource_id)
        statistic = self.query_retry(f=self.ceilometer.statistics.list,
                                     meter_name=meter_name,
                                     q=query,
                                     period=period,
                                     aggregates=[
                                         {'func': aggregate}],
                                     groupby=['resource_id'])

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
                {'sample_%s' % index: {'timestamp': sample._info['timestamp'],
                                       'value': sample._info[
                                           'counter_volume']}})
        return values

    def get_last_sample_value(self, resource_id, meter_name):
        samples = self.query_sample(meter_name=meter_name,
                                    query=self.build_query(resource_id))
        if samples:
            return samples[-1]._info['counter_volume']
        else:
            return False
