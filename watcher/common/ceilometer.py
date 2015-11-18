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
from urlparse import urlparse

from ceilometerclient import client
from ceilometerclient.exc import HTTPUnauthorized
from watcher.common import keystone


class Client(object):
    # todo olso conf: this must be sync with ceilometer
    CEILOMETER_API_VERSION = '2'

    def __init__(self):
        ksclient = keystone.Client()
        self.creds = ksclient.get_credentials()
        self.creds['os_auth_token'] = ksclient.get_token()
        self.creds['token'] = ksclient.get_token()
        self.creds['ceilometer_url'] = "http://" + urlparse(
            ksclient.get_endpoint(
                service_type='metering',
                endpoint_type='publicURL')).netloc
        self.connect()

    def connect(self):
        """Initialization of Ceilometer client."""
        self.cmclient = client.get_client(self.CEILOMETER_API_VERSION,
                                          **self.creds)

    def build_query(user_id=None, tenant_id=None, resource_id=None,
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

    def query_sample(self, meter_name, query, limit=1):
        try:
            samples = self.ceilometerclient().samples.list(
                meter_name=meter_name,
                limit=limit,
                q=query)
        except HTTPUnauthorized:
            self.connect()
            samples = self.ceilometerclient().samples.list(
                meter_name=meter_name,
                limit=limit,
                q=query)
        except Exception:
            raise
        return samples

    def get_endpoint(self, service_type, endpoint_type=None):
        ksclient = keystone.Client()
        endpoint = ksclient.get_endpoint(service_type=service_type,
                                         endpoint_type=endpoint_type)
        return endpoint

    def statistic_list(self, meter_name, query=None, period=None):
        """List of statistics."""
        statistics = self.ceilometerclient().statistics.list(
            meter_name=meter_name, q=query, period=period)
        return statistics

    def meter_list(self, query=None):
        """List the user's meters."""
        meters = self.ceilometerclient().meters.list(query)
        return meters

    def statistic_aggregation(self,
                              resource_id,
                              meter_name,
                              period,
                              aggregate='avg'):
        """
        :param resource_id: id
        :param meter_name: meter names of which we want the statistics
        :param period: `period`: In seconds. If no period is given, only one
                       aggregate statistic is returned. If given, a faceted
                       result will be returned, divided into given periods.
                       Periods with no data are ignored.
        :param aggregate:
        :return:
        """
        """Representing a statistic aggregate by operators"""

        query = self.build_query(resource_id=resource_id)
        try:
            statistic = self.cmclient.statistics.list(
                meter_name=meter_name,
                q=query,
                period=period,
                aggregates=[
                    {'func': aggregate}],
                groupby=['resource_id'])
        except HTTPUnauthorized:
            self.connect()
            statistic = self.cmclient.statistics.list(
                meter_name=meter_name,
                q=query,
                period=period,
                aggregates=[
                    {'func': aggregate}],
                groupby=['resource_id'])
        except Exception:
            raise
        item_value = None
        if statistic:
            item_value = statistic[-1]._info.get('aggregate').get('avg')
        return item_value

    def get_last_sample_values(self, resource_id, meter_name, limit=1):
        samples = self.query_sample(meter_name=meter_name,
                                    query=self.build_query(resource_id))
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
