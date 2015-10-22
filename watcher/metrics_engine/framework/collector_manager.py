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
from keystoneclient.auth.identity import v3
from keystoneclient import session

from oslo_config import cfg
from stevedore import driver
from watcher.applier.framework.command.wrapper.nova_wrapper import NovaWrapper

from watcher.metrics_engine.framework.statedb_collector import NovaCollector
from watcher.openstack.common import log

LOG = log.getLogger(__name__)
CONF = cfg.CONF

WATCHER_METRICS_COLLECTOR_OPTS = [
    cfg.StrOpt('metrics_resource',
               default="influxdb",
               help='The driver that collect measurements'
                    'of the utilization'
                    'of the physical and virtual resources')
]
metrics_collector_opt_group = cfg.OptGroup(
    name='watcher_collector',
    title='Defines Metrics collector available')
CONF.register_group(metrics_collector_opt_group)
CONF.register_opts(WATCHER_METRICS_COLLECTOR_OPTS, metrics_collector_opt_group)

CONF.import_opt('admin_user', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('admin_tenant_name', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('admin_password', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('auth_uri', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')


class CollectorManager(object):
    def get_metric_collector(self):
        manager = driver.DriverManager(
            namespace='watcher_metrics_collector',
            name=CONF.watcher_collector.metrics_resource,
            invoke_on_load=True,
        )
        return manager.driver

    def get_statedb_collector(self):
        creds = \
            {'auth_url': CONF.keystone_authtoken.auth_uri,
             'username': CONF.keystone_authtoken.admin_user,
             'password': CONF.keystone_authtoken.admin_password,
             'project_name': CONF.keystone_authtoken.admin_tenant_name,
             'user_domain_name': "default",
             'project_domain_name': "default"}

        auth = v3.Password(auth_url=creds['auth_url'],
                           username=creds['username'],
                           password=creds['password'],
                           project_name=creds['project_name'],
                           user_domain_name=creds[
                               'user_domain_name'],
                           project_domain_name=creds[
                               'project_domain_name'])
        sess = session.Session(auth=auth)
        wrapper = NovaWrapper(creds, session=sess)
        return NovaCollector(wrapper=wrapper)
