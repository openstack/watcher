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

import collections

from lxml import etree
import six

from watcher._i18n import _
from watcher.common import exception
from watcher.common import utils
from watcher.decision_engine.model import base
from watcher.decision_engine.model import element
from watcher.decision_engine.model import mapping


class ModelRoot(base.Model):

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
            instance = self.get_instance_by_uuid(instance)
        if isinstance(node, six.string_types):
            node = self.get_node_by_uuid(node)

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
            instance = self.get_instance_by_uuid(instance)
        if isinstance(node, six.string_types):
            node = self.get_node_by_uuid(node)

        self.add_instance(instance)
        self.mapping.unmap(node, instance)

    def delete_instance(self, instance, node=None):
        if node is not None:
            self.mapping.unmap(node, instance)

        self.remove_instance(instance)

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

    def get_node_by_uuid(self, node_uuid):
        if str(node_uuid) not in self._nodes:
            raise exception.ComputeNodeNotFound(name=node_uuid)
        return self._nodes[str(node_uuid)]

    def get_instance_by_uuid(self, uuid):
        if str(uuid) not in self._instances:
            raise exception.InstanceNotFound(name=uuid)
        return self._instances[str(uuid)]

    def get_node_by_instance_uuid(self, instance_uuid):
        """Getting host information from the guest instance

        :param instance_uuid: the uuid of the instance
        :return: node
        """
        if str(instance_uuid) not in self.mapping.instance_mapping:
            raise exception.InstanceNotFound(name=instance_uuid)
        return self.get_node_by_uuid(
            self.mapping.instance_mapping[str(instance_uuid)])

    def get_all_instances(self):
        return self._instances

    def get_mapping(self):
        return self.mapping

    def create_resource(self, r):
        self.resource[str(r.name)] = r

    def get_resource_by_uuid(self, resource_id):
        return self.resource[str(resource_id)]

    def get_node_instances(self, node):
        return self.mapping.get_node_instances(node)

    def _build_compute_node_element(self, compute_node):
        attrib = collections.OrderedDict(
            id=six.text_type(compute_node.id), uuid=compute_node.uuid,
            human_id=compute_node.human_id, hostname=compute_node.hostname,
            state=compute_node.state, status=compute_node.status)

        for resource_name, resource in sorted(
                self.resource.items(), key=lambda x: x[0]):
            res_value = resource.get_capacity(compute_node)
            if res_value is not None:
                attrib[resource_name] = six.text_type(res_value)

        compute_node_el = etree.Element("ComputeNode", attrib=attrib)

        return compute_node_el

    def _build_instance_element(self, instance):
        attrib = collections.OrderedDict(
            uuid=instance.uuid, human_id=instance.human_id,
            hostname=instance.hostname, state=instance.state)

        for resource_name, resource in sorted(
                self.resource.items(), key=lambda x: x[0]):
            res_value = resource.get_capacity(instance)
            if res_value is not None:
                attrib[resource_name] = six.text_type(res_value)

        instance_el = etree.Element("Instance", attrib=attrib)

        return instance_el

    def to_string(self):
        root = etree.Element("ModelRoot")
        # Build compute node tree
        for cn in sorted(self.get_all_compute_nodes().values(),
                         key=lambda cn: cn.uuid):
            compute_node_el = self._build_compute_node_element(cn)

            # Build mapped instance tree
            node_instance_uuids = self.get_node_instances(cn)
            for instance_uuid in sorted(node_instance_uuids):
                instance = self.get_instance_by_uuid(instance_uuid)
                instance_el = self._build_instance_element(instance)
                compute_node_el.append(instance_el)

            root.append(compute_node_el)

        # Build unmapped instance tree (i.e. not assigned to any compute node)
        for instance in sorted(self.get_all_instances().values(),
                               key=lambda inst: inst.uuid):
            try:
                self.get_node_by_instance_uuid(instance.uuid)
            except exception.InstanceNotFound:
                root.append(self._build_instance_element(instance))

        return etree.tostring(root, pretty_print=True).decode('utf-8')

    @classmethod
    def from_xml(cls, data):
        model = cls()
        root = etree.fromstring(data)

        mem = element.Resource(element.ResourceType.memory)
        num_cores = element.Resource(element.ResourceType.cpu_cores)
        disk = element.Resource(element.ResourceType.disk)
        disk_capacity = element.Resource(element.ResourceType.disk_capacity)
        model.create_resource(mem)
        model.create_resource(num_cores)
        model.create_resource(disk)
        model.create_resource(disk_capacity)

        for cn in root.findall('.//ComputeNode'):
            node = element.ComputeNode(cn.get('id'))
            node.uuid = cn.get('uuid')
            node.hostname = cn.get('hostname')
            # set capacity
            mem.set_capacity(node, int(cn.get(str(mem.name))))
            disk.set_capacity(node, int(cn.get(str(disk.name))))
            disk_capacity.set_capacity(
                node, int(cn.get(str(disk_capacity.name))))
            num_cores.set_capacity(node, int(cn.get(str(num_cores.name))))
            node.state = cn.get('state')
            node.status = cn.get('status')

            model.add_node(node)

        for inst in root.findall('.//Instance'):
            instance = element.Instance()
            instance.uuid = inst.get('uuid')
            instance.state = inst.get('state')

            mem.set_capacity(instance, int(inst.get(str(mem.name))))
            disk.set_capacity(instance, int(inst.get(str(disk.name))))
            disk_capacity.set_capacity(
                instance, int(inst.get(str(disk_capacity.name))))
            num_cores.set_capacity(
                instance, int(inst.get(str(num_cores.name))))

            parent = inst.getparent()
            if parent.tag == 'ComputeNode':
                node = model.get_node_by_uuid(parent.get('uuid'))
                model.map_instance(instance, node)
            else:
                model.add_instance(instance)

        return model
