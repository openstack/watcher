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

import six

from watcher._i18n import _
from watcher.common import exception
from watcher.common import utils
from watcher.decision_engine.model import element
from watcher.decision_engine.model import mapping


class ModelRoot(object):
    def __init__(self, stale=False):
        self._nodes = utils.Struct()
        self._instances = utils.Struct()
        self.mapping = mapping.Mapping(self)
        self.resource = utils.Struct()
        self.stale = stale

    def __nonzero__(self):
        return not self.stale

    __bool__ = __nonzero__

    def assert_node(self, obj):
        if not isinstance(obj, element.ComputeNode):
            raise exception.IllegalArgumentException(
                message=_("'obj' argument type is not valid"))

    def assert_instance(self, obj):
        if not isinstance(obj, element.Instance):
            raise exception.IllegalArgumentException(
                message=_("'obj' argument type is not valid"))

    def add_node(self, node):
        self.assert_node(node)
        self._nodes[node.uuid] = node

    def remove_node(self, node):
        self.assert_node(node)
        if str(node.uuid) not in self._nodes:
            raise exception.ComputeNodeNotFound(name=node.uuid)
        else:
            del self._nodes[node.uuid]

    def add_instance(self, instance):
        self.assert_instance(instance)
        self._instances[instance.uuid] = instance

    def remove_instance(self, instance):
        self.assert_instance(instance)
        del self._instances[instance.uuid]

    def map_instance(self, instance, node):
        """Map a newly created instance to a node

        :param instance: :py:class:`~.Instance` object or instance UUID
        :type instance: str or :py:class:`~.Instance`
        :param node: :py:class:`~.ComputeNode` object or node UUID
        :type node: str or :py:class:`~.Instance`
        """
        if isinstance(instance, six.string_types):
            instance = self.get_instance_from_id(instance)
        if isinstance(node, six.string_types):
            node = self.get_node_from_id(node)

        self.add_instance(instance)
        self.mapping.map(node, instance)

    def unmap_instance(self, instance, node):
        """Unmap an instance from a node

        :param instance: :py:class:`~.Instance` object or instance UUID
        :type instance: str or :py:class:`~.Instance`
        :param node: :py:class:`~.ComputeNode` object or node UUID
        :type node: str or :py:class:`~.Instance`
        """
        if isinstance(instance, six.string_types):
            instance = self.get_instance_from_id(instance)
        if isinstance(node, six.string_types):
            node = self.get_node_from_id(node)

        self.add_instance(instance)
        self.mapping.unmap(node, instance)

    def delete_instance(self, instance, node):
        self.remove_instance(instance)

        self.mapping.unmap(node, instance)

        for resource in self.resource.values():
            try:
                resource.unset_capacity(instance)
            except KeyError:
                pass

    def migrate_instance(self, instance, source_node, destination_node):
        """Migrate single instance from source_node to destination_node

        :param instance:
        :param source_node:
        :param destination_node:
        :return:
        """
        if source_node == destination_node:
            return False
        # unmap
        self.mapping.unmap(source_node, instance)
        # map
        self.mapping.map(destination_node, instance)
        return True

    def get_all_compute_nodes(self):
        return self._nodes

    def get_node_from_id(self, node_uuid):
        if str(node_uuid) not in self._nodes:
            raise exception.ComputeNodeNotFound(name=node_uuid)
        return self._nodes[str(node_uuid)]

    def get_instance_from_id(self, uuid):
        if str(uuid) not in self._instances:
            raise exception.InstanceNotFound(name=uuid)
        return self._instances[str(uuid)]

    def get_node_from_instance_id(self, instance_uuid):
        """Getting host information from the guest instance

        :param instance_uuid: the uuid of the instance
        :return: node
        """
        if str(instance_uuid) not in self.mapping.instance_mapping:
            raise exception.InstanceNotFound(name=instance_uuid)
        return self.get_node_from_id(
            self.mapping.instance_mapping[str(instance_uuid)])

    def get_all_instances(self):
        return self._instances

    def get_mapping(self):
        return self.mapping

    def create_resource(self, r):
        self.resource[str(r.name)] = r

    def get_resource_from_id(self, resource_id):
        return self.resource[str(resource_id)]
