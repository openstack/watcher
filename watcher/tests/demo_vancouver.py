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
from concurrent.futures import ThreadPoolExecutor

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
import ceilometerclient.v2 as c_client

cfg.CONF.debug = True
log.setup('metering-controller')

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
cfg.CONF.keystone_authtoken.admin_user = "watcher"
cfg.CONF.keystone_authtoken.admin_password = "watcher"
cfg.CONF.keystone_authtoken.admin_tenant_name = "services"


def make_query(user_id=None, tenant_id=None, resource_id=None,
               user_ids=None, tenant_ids=None, resource_ids=None):
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


# nova-manage service enable
--host='ldev-indeedsrv005' --service='nova-compute'


def create(wrapper, id, hypervisorid):
    print("create instance VM_{0} on {1}".format(str(id), str(hypervisorid)))
    try:

        for image in glance.images.list(name='Cirros'):
            id_image = image.id

        vm = wrapper.create_instance(hypervisor_id=hypervisorid,
                                     inst_name="VM_" + str(id),
                                     keypair_name='admin',
                                     image_id=id_image,
                                     create_new_floating_ip=True,
                                     flavor_name='m1.medium')
        print(vm)
    except Exception as e:
        print(unicode(e))


def purge(nova, wrapper):
    print("Purging the cluster")
    instances = nova.servers.list()
    for instance in instances:
        wrapper.delete_instance(instance.id)


try:
    executor = ThreadPoolExecutor(max_workers=3)
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

    wrapper = NovaWrapper(creds, session=sess)

    wrapper.live_migrate_instance(
        instance_id="b2aca823-a621-4235-9d56-9f0f75955dc1",
        dest_hostname="ldev-indeedsrv006", block_migration=True)

    nova-manage service enable --host='ldev-indeedsrv005' \
        --service='nova-compute'
    nova-manage service enable --host='ldev-indeedsrv006' \
        --service='nova-compute'


except Exception as e:
    print("rollback " + str(e))

"""
