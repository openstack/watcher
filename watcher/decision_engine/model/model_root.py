# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Intel Innovation and Research Ireland Ltd.
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
"""
Openstack implementation of the cluster graph.
"""

from lxml import etree
import networkx as nx
from oslo_concurrency import lockutils
from oslo_log import log
import six

from watcher._i18n import _
from watcher.common import exception
from watcher.decision_engine.model import base
from watcher.decision_engine.model import element

LOG = log.getLogger(__name__)


class ModelRoot(nx.DiGraph, base.Model):
    """Cluster graph for an Openstack cluster."""

    def __init__(self, stale=False):
        super(ModelRoot, self).__init__()
        self.stale = stale

    def __nonzero__(self):
        return not self.stale

    __bool__ = __nonzero__

    @staticmethod
    def assert_node(obj):
        if not isinstance(obj, element.ComputeNode):
            raise exception.IllegalArgumentException(
                message=_("'obj' argument type is not valid: %s") % type(obj))

    @staticmethod
    def assert_instance(obj):
        if not isinstance(obj, element.Instance):
            raise exception.IllegalArgumentException(
                message=_("'obj' argument type is not valid"))

    @lockutils.synchronized("model_root")
    def add_node(self, node):
        self.assert_node(node)
        super(ModelRoot, self).add_node(node.uuid, node)

    @lockutils.synchronized("model_root")
    def remove_node(self, node):
        self.assert_node(node)
        try:
            super(ModelRoot, self).remove_node(node.uuid)
        except nx.NetworkXError as exc:
            LOG.exception(exc)
            raise exception.ComputeNodeNotFound(name=node.uuid)

    @lockutils.synchronized("model_root")
    def add_instance(self, instance):
        self.assert_instance(instance)
        try:
            super(ModelRoot, self).add_node(instance.uuid, instance)
        except nx.NetworkXError as exc:
            LOG.exception(exc)
            raise exception.InstanceNotFound(name=instance.uuid)

    @lockutils.synchronized("model_root")
    def remove_instance(self, instance):
        self.assert_instance(instance)
        super(ModelRoot, self).remove_node(instance.uuid)

    @lockutils.synchronized("model_root")
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
        self.assert_node(node)
        self.assert_instance(instance)

        self.add_edge(instance.uuid, node.uuid)

    @lockutils.synchronized("model_root")
    def unmap_instance(self, instance, node):
        if isinstance(instance, six.string_types):
            instance = self.get_instance_by_uuid(instance)
        if isinstance(node, six.string_types):
            node = self.get_node_by_uuid(node)

        self.remove_edge(instance.uuid, node.uuid)

    def delete_instance(self, instance, node=None):
        self.assert_instance(instance)
        self.remove_instance(instance)

    @lockutils.synchronized("model_root")
    def migrate_instance(self, instance, source_node, destination_node):
        """Migrate single instance from source_node to destination_node

        :param instance:
        :param source_node:
        :param destination_node:
        :return:
        """
        self.assert_instance(instance)
        self.assert_node(source_node)
        self.assert_node(destination_node)

        if source_node == destination_node:
            return False

        # unmap
        self.remove_edge(instance.uuid, source_node.uuid)
        # map
        self.add_edge(instance.uuid, destination_node.uuid)
        return True

    @lockutils.synchronized("model_root")
    def get_all_compute_nodes(self):
        return {uuid: cn for uuid, cn in self.nodes(data=True)
                if isinstance(cn, element.ComputeNode)}

    @lockutils.synchronized("model_root")
    def get_node_by_uuid(self, uuid):
        try:
            return self._get_by_uuid(uuid)
        except exception.ComputeResourceNotFound:
            raise exception.ComputeNodeNotFound(name=uuid)

    @lockutils.synchronized("model_root")
    def get_instance_by_uuid(self, uuid):
        try:
            return self._get_by_uuid(uuid)
        except exception.ComputeResourceNotFound:
            raise exception.InstanceNotFound(name=uuid)

    def _get_by_uuid(self, uuid):
        try:
            return self.node[uuid]
        except Exception as exc:
            LOG.exception(exc)
            raise exception.ComputeResourceNotFound(name=uuid)

    @lockutils.synchronized("model_root")
    def get_node_by_instance_uuid(self, instance_uuid):
        instance = self._get_by_uuid(instance_uuid)
        for node_uuid in self.neighbors(instance.uuid):
            node = self._get_by_uuid(node_uuid)
            if isinstance(node, element.ComputeNode):
                return node
        raise exception.ComputeNodeNotFound(name=instance_uuid)

    @lockutils.synchronized("model_root")
    def get_all_instances(self):
        return {uuid: inst for uuid, inst in self.nodes(data=True)
                if isinstance(inst, element.Instance)}

    @lockutils.synchronized("model_root")
    def get_node_instances(self, node):
        self.assert_node(node)
        node_instances = []
        for instance_uuid in self.predecessors(node.uuid):
            instance = self._get_by_uuid(instance_uuid)
            if isinstance(instance, element.Instance):
                node_instances.append(instance)

        return node_instances

    def to_string(self):
        return self.to_xml()

    def to_xml(self):
        root = etree.Element("ModelRoot")
        # Build compute node tree
        for cn in sorted(self.get_all_compute_nodes().values(),
                         key=lambda cn: cn.uuid):
            compute_node_el = cn.as_xml_element()

            # Build mapped instance tree
            node_instances = self.get_node_instances(cn)
            for instance in sorted(node_instances, key=lambda x: x.uuid):
                instance_el = instance.as_xml_element()
                compute_node_el.append(instance_el)

            root.append(compute_node_el)

        # Build unmapped instance tree (i.e. not assigned to any compute node)
        for instance in sorted(self.get_all_instances().values(),
                               key=lambda inst: inst.uuid):
            try:
                self.get_node_by_instance_uuid(instance.uuid)
            except (exception.InstanceNotFound, exception.ComputeNodeNotFound):
                root.append(instance.as_xml_element())

        return etree.tostring(root, pretty_print=True).decode('utf-8')

    @classmethod
    def from_xml(cls, data):
        model = cls()

        root = etree.fromstring(data)
        for cn in root.findall('.//ComputeNode'):
            node = element.ComputeNode(**cn.attrib)
            model.add_node(node)

        for inst in root.findall('.//Instance'):
            instance = element.Instance(**inst.attrib)
            model.add_instance(instance)

            parent = inst.getparent()
            if parent.tag == 'ComputeNode':
                node = model.get_node_by_uuid(parent.get('uuid'))
                model.map_instance(instance, node)
            else:
                model.add_instance(instance)

        return model
