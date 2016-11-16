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

from oslo_concurrency import lockutils
from oslo_log import log

from watcher._i18n import _LW

LOG = log.getLogger(__name__)


class Mapping(object):
    def __init__(self, model):
        self.model = model
        self.compute_node_mapping = {}
        self.instance_mapping = {}

    def map(self, node, instance):
        """Select the node where the instance is launched

        :param node: the node
        :param instance: the virtual machine or instance
        """
        with lockutils.lock(__name__):
            # init first
            if node.uuid not in self.compute_node_mapping.keys():
                self.compute_node_mapping[node.uuid] = set()

            # map node => instances
            self.compute_node_mapping[node.uuid].add(instance.uuid)

            # map instance => node
            self.instance_mapping[instance.uuid] = node.uuid

    def unmap(self, node, instance):
        """Remove the instance from the node

        :param node: the node
        :param instance: the virtual machine or instance
        """
        self.unmap_by_uuid(node.uuid, instance.uuid)

    def unmap_by_uuid(self, node_uuid, instance_uuid):
        """Remove the instance (by id) from the node (by id)

        :rtype : object
        """
        with lockutils.lock(__name__):
            if str(node_uuid) in self.compute_node_mapping:
                self.compute_node_mapping[str(node_uuid)].remove(
                    str(instance_uuid))
                # remove instance
                self.instance_mapping.pop(instance_uuid)
            else:
                LOG.warning(
                    _LW("Trying to delete the instance %(instance)s but it "
                        "was not found on node %(node)s") %
                    {'instance': instance_uuid, 'node': node_uuid})

    def get_mapping(self):
        return self.compute_node_mapping

    def get_node_from_instance(self, instance):
        return self.get_node_by_instance_uuid(instance.uuid)

    def get_node_by_instance_uuid(self, instance_uuid):
        """Getting host information from the guest instance

        :param instance: the uuid of the instance
        :return: node
        """
        return self.model.get_node_by_uuid(
            self.instance_mapping[str(instance_uuid)])

    def get_node_instances(self, node):
        """Get the list of instances running on the node

        :param node:
        :return:
        """
        return self.get_node_instances_by_uuid(node.uuid)

    def get_node_instances_by_uuid(self, node_uuid):
        if str(node_uuid) in self.compute_node_mapping.keys():
            return self.compute_node_mapping[str(node_uuid)]
        else:
            # empty
            return set()
