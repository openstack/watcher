# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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
import ceilometerclient.v2 as c_client
import keystoneclient.v3.client as ksclient
from oslo_config import cfg
CONF = cfg.CONF

from watcher.decision_engine.api.collector.metrics_resource_collector import \
    MetricsResourceCollector

CONF.import_opt('admin_user', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('admin_tenant_name', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('admin_password', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('auth_uri', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')


class RessourceDB(MetricsResourceCollector):
    def __init__(self):
        creds = \
            {'auth_url': CONF.keystone_authtoken.auth_uri,
             'username': CONF.keystone_authtoken.admin_user,
             'password': CONF.keystone_authtoken.admin_password,
             'project_name': CONF.keystone_authtoken.admin_tenant_name,
             'user_domain_name': "default",
             'project_domain_name': "default"}
        self.keystone = ksclient.Client(**creds)

        self.ceilometer = c_client.Client(
            endpoint=self.get_ceilometer_uri(),
            token=self.keystone.auth_token)

    def make_query(user_id=None, tenant_id=None, resource_id=None,
                   user_ids=None, tenant_ids=None, resource_ids=None):

        """Returns query built form given parameters.
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

    def get_ceilometer_uri(self):
        a = self.keystone.services.list(**{'type': 'metering'})
        e = self.keystone.endpoints.list()
        for s in e:
            if s.service_id == a[0].id and s.interface == 'internal':
                return s.url
        raise Exception("Ceilometer Metering Service internal not defined")

    def get_average_usage_vm_cpu(self, instance_uuid):
        """The last VM CPU usage values to average

        :param uuid:00
        :return:
        """
        # query influxdb stream
        query = self.make_query(resource_id=instance_uuid)
        cpu_util_sample = self.ceilometer.samples.list('cpu_util',
                                                       q=query)
        cpu_usage = 0
        count = len(cpu_util_sample)
        for each in cpu_util_sample:
            # print each.timestamp, each.counter_name, each.counter_volume
            cpu_usage = cpu_usage + each.counter_volume
        if count == 0:
            return 0
        else:
            return cpu_usage / len(cpu_util_sample)

    def get_average_usage_vm_memory(self, uuid):
        # Obtaining Memory Usage is not implemented for LibvirtInspector
        # waiting for kilo memory.resident
        return 1

    def get_average_usage_vm_disk(self, uuid):
        # waiting for kilo disk.usage
        return 1
