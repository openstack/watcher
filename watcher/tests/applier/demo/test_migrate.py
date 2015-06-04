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
"""
from keystoneclient import session

from keystoneclient.auth.identity import v3

import cinderclient.v2.client as ciclient
import glanceclient.v2.client as glclient
import keystoneclient.v3.client as ksclient
import neutronclient.neutron.client as netclient
import novaclient.v2.client as nvclient

from watcher.common.utils import CONF
from oslo_config import cfg
from watcher.applier.framework.command.migrate_command import MigrateCommand
from watcher.applier.framework.command.wrapper.nova_wrapper import NovaWrapper
from watcher.decision_engine.framework.default_planner import Primitives
from watcher.openstack.common import log

cfg.CONF.import_opt('auth_uri', 'keystoneclient.middleware.auth_token',
                    group='keystone_authtoken')
cfg.CONF.import_opt('admin_user', 'keystoneclient.middleware.auth_token',
                    group='keystone_authtoken')
cfg.CONF.import_opt('admin_password', 'keystoneclient.middleware.auth_token',
                    group='keystone_authtoken')
cfg.CONF.import_opt('admin_tenant_name',
                    'keystoneclient.middleware.auth_token',
                    group='keystone_authtoken')

cfg.CONF.keystone_authtoken.auth_uri = "http://10.50.0.105:5000/v3/"
cfg.CONF.keystone_authtoken.admin_user = "admin"
cfg.CONF.keystone_authtoken.admin_password = "openstacktest"
cfg.CONF.keystone_authtoken.admin_tenant_name = "test"

try:
    cfg.CONF.debug = True
    log.setup('watcher-sercon-demo')
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
    nova = nvclient.Client("3", session=sess)
    neutron = netclient.Client('2.0', session=sess)
    neutron.format = 'json'
    keystone = ksclient.Client(**creds)

    glance_endpoint = keystone. \
        service_catalog.url_for(service_type='image',
                                endpoint_type='publicURL')
    glance = glclient.Client(glance_endpoint,
                             token=keystone.auth_token)

    cinder = ciclient.Client('2', session=sess)
    wrapper = NovaWrapper(user=creds['username'], nova=nova,
                          neutron=neutron, glance=glance,
                          cinder=cinder)
    instance = wrapper. \
        create_instance(hypervisor_id='ldev-indeedsrv006',
                        inst_name="demo_instance_1",
                        keypair_name='admin',
                        image_id=
                        "2b958331-379b-4618-b2ba-fbe8a608b2bb")

    cmd = MigrateCommand(instance.id, Primitives.COLD_MIGRATE,
                         'ldev-indeedsrv006',
                         'ldev-indeedsrv005')
    resu = cmd.execute(cmd)
    resu.result()
    # wrapper.delete_instance(instance.id)
except Exception as e:
    print("rollback " + unicode(e))
"""""
