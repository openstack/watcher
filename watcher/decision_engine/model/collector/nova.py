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

from oslo_log import log

from watcher.common import nova_helper
from watcher.decision_engine.model.collector import base
from watcher.decision_engine.model import element
from watcher.decision_engine.model import model_root
from watcher.decision_engine.model.notification import nova

LOG = log.getLogger(__name__)


class NovaClusterDataModelCollector(base.BaseClusterDataModelCollector):
    """Nova cluster data model collector

       The Nova cluster data model collector creates an in-memory
       representation of the resources exposed by the compute service.
    """

    def __init__(self, config, osc=None):
        super(NovaClusterDataModelCollector, self).__init__(config, osc)
        self.wrapper = nova_helper.NovaHelper(osc=self.osc)

    @property
    def notification_endpoints(self):
        """Associated notification endpoints

        :return: Associated notification endpoints
        :rtype: List of :py:class:`~.EventsNotificationEndpoint` instances
        """
        return [
            nova.ServiceUpdated(self),

            nova.InstanceCreated(self),
            nova.InstanceUpdated(self),
            nova.InstanceDeletedEnd(self),

            nova.LegacyInstanceCreatedEnd(self),
            nova.LegacyInstanceUpdated(self),
            nova.LegacyInstanceDeletedEnd(self),
            nova.LegacyLiveMigratedEnd(self),
        ]

    def execute(self):
        """Build the compute cluster data model"""
        LOG.debug("Building latest Nova cluster data model")

        model = model_root.ModelRoot()
        mem = element.Resource(element.ResourceType.memory)
        num_cores = element.Resource(element.ResourceType.cpu_cores)
        disk = element.Resource(element.ResourceType.disk)
        disk_capacity = element.Resource(element.ResourceType.disk_capacity)
        model.create_resource(mem)
        model.create_resource(num_cores)
        model.create_resource(disk)
        model.create_resource(disk_capacity)

        flavor_cache = {}
        nodes = self.wrapper.get_compute_node_list()
        for n in nodes:
            service = self.wrapper.nova.services.find(id=n.service['id'])
            # create node in cluster_model_collector
            node = element.ComputeNode(n.id)
            node.uuid = service.host
            node.hostname = n.hypervisor_hostname
            # set capacity
            mem.set_capacity(node, n.memory_mb)
            disk.set_capacity(node, n.free_disk_gb)
            disk_capacity.set_capacity(node, n.local_gb)
            num_cores.set_capacity(node, n.vcpus)
            node.state = n.state
            node.status = n.status
            model.add_node(node)
            instances = self.wrapper.get_instances_by_node(str(service.host))
            for v in instances:
                # create VM in cluster_model_collector
                instance = element.Instance()
                instance.uuid = v.id
                # nova/nova/compute/instance_states.py
                instance.state = getattr(v, 'OS-EXT-STS:vm_state')

                # set capacity
                self.wrapper.get_flavor_instance(v, flavor_cache)
                mem.set_capacity(instance, v.flavor['ram'])
                # FIXME: update all strategies to use disk_capacity
                # for instances instead of disk
                disk.set_capacity(instance, v.flavor['disk'])
                disk_capacity.set_capacity(instance, v.flavor['disk'])
                num_cores.set_capacity(instance, v.flavor['vcpus'])

                model.map_instance(instance, node)

        return model
