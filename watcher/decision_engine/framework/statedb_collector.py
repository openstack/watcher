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


from keystoneclient.auth.identity import v3
from keystoneclient import session

from watcher.applier.framework.command.wrapper.nova_wrapper import NovaWrapper
from watcher.decision_engine.api.collector.cluster_state_collector import \
    ClusterStateCollector
from watcher.decision_engine.framework.model.hypervisor import Hypervisor
from watcher.decision_engine.framework.model.model_root import ModelRoot
from watcher.decision_engine.framework.model.resource import Resource
from watcher.decision_engine.framework.model.resource import ResourceType
from watcher.decision_engine.framework.model.vm import VM
from watcher.openstack.common import log

from oslo_config import cfg
CONF = cfg.CONF
LOG = log.getLogger(__name__)

CONF.import_opt('admin_user', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('admin_tenant_name', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('admin_password', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('auth_uri', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')


class NovaCollector(ClusterStateCollector):
    def get_latest_state_cluster(self):
        try:
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

            cluster = ModelRoot()
            mem = Resource(ResourceType.memory)
            num_cores = Resource(ResourceType.cpu_cores)
            disk = Resource(ResourceType.disk)
            cluster.create_resource(mem)
            cluster.create_resource(num_cores)
            cluster.create_resource(disk)

            flavor_cache = {}
            hypervisors = wrapper.get_hypervisors_list()
            for h in hypervisors:
                i = h.hypervisor_hostname.index('.')
                name = h.hypervisor_hostname[0:i]
                # create hypervisor in stateDB
                hypervisor = Hypervisor()
                hypervisor.set_uuid(name)
                # set capacity
                mem.set_capacity(hypervisor, h.memory_mb)
                disk.set_capacity(hypervisor, h.disk_available_least)
                num_cores.set_capacity(hypervisor, h.vcpus)
                cluster.add_hypervisor(hypervisor)
                vms = wrapper.get_vms_by_hypervisor(str(name))
                for v in vms:
                    # create VM in stateDB
                    vm = VM()
                    vm.set_uuid(v.id)
                    # set capacity
                    wrapper.get_flavor_instance(v, flavor_cache)
                    mem.set_capacity(vm, v.flavor['ram'])
                    disk.set_capacity(vm, v.flavor['disk'])
                    num_cores.set_capacity(vm, v.flavor['vcpus'])
                    # print(dir(v))
                    cluster.get_mapping().map(hypervisor, vm)
                    cluster.add_vm(vm)
            return cluster
        except Exception as e:
            LOG.error("nova collector " + unicode(e))
            return None
