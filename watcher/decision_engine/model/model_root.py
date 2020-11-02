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

import ast
from lxml import etree
import networkx as nx
from oslo_concurrency import lockutils
from oslo_log import log

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
        super(ModelRoot, self).add_node(node.uuid, attr=node)

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
            super(ModelRoot, self).add_node(instance.uuid, attr=instance)
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

        :param instance: :py:class:`~.instance.Instance` object or instance
           UUID
        :type instance: str or :py:class:`~.instance.Instance`
        :param node: :py:class:`~.node.ComputeNode` object or node UUID
        :type node: str or :py:class:`~.instance.Instance`
        """
        if isinstance(instance, str):
            instance = self.get_instance_by_uuid(instance)
        if isinstance(node, str):
            node = self.get_node_by_uuid(node)
        self.assert_node(node)
        self.assert_instance(instance)

        self.add_edge(instance.uuid, node.uuid)

    @lockutils.synchronized("model_root")
    def unmap_instance(self, instance, node):
        if isinstance(instance, str):
            instance = self.get_instance_by_uuid(instance)
        if isinstance(node, str):
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
        return {uuid: cn['attr'] for uuid, cn in self.nodes(data=True)
                if isinstance(cn['attr'], element.ComputeNode)}

    @lockutils.synchronized("model_root")
    def get_node_by_uuid(self, uuid):
        try:
            return self._get_by_uuid(uuid)
        except exception.ComputeResourceNotFound:
            raise exception.ComputeNodeNotFound(name=uuid)

    @lockutils.synchronized("model_root")
    def get_node_by_name(self, name):
        try:
            node_list = [cn['attr'] for uuid, cn in self.nodes(data=True)
                         if (isinstance(cn['attr'], element.ComputeNode) and
                         cn['attr']['hostname'] == name)]
            if node_list:
                return node_list[0]
            else:
                raise exception.ComputeResourceNotFound
        except exception.ComputeResourceNotFound:
            raise exception.ComputeNodeNotFound(name=name)

    @lockutils.synchronized("model_root")
    def get_instance_by_uuid(self, uuid):
        try:
            return self._get_by_uuid(uuid)
        except exception.ComputeResourceNotFound:
            raise exception.InstanceNotFound(name=uuid)

    def _get_by_uuid(self, uuid):
        try:
            return self.nodes[uuid]['attr']
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
        raise exception.InstanceNotMapped(uuid=instance_uuid)

    @lockutils.synchronized("model_root")
    def get_all_instances(self):
        return {uuid: inst['attr'] for uuid, inst in self.nodes(data=True)
                if isinstance(inst['attr'], element.Instance)}

    @lockutils.synchronized("model_root")
    def get_node_instances(self, node):
        self.assert_node(node)
        node_instances = []
        for instance_uuid in self.predecessors(node.uuid):
            instance = self._get_by_uuid(instance_uuid)
            if isinstance(instance, element.Instance):
                node_instances.append(instance)

        return node_instances

    def get_node_used_resources(self, node):
        vcpu_used = 0
        memory_used = 0
        disk_used = 0
        for instance in self.get_node_instances(node):
            vcpu_used += instance.vcpus
            memory_used += instance.memory
            disk_used += instance.disk

        return dict(vcpu=vcpu_used, memory=memory_used, disk=disk_used)

    def get_node_free_resources(self, node):
        resources_used = self.get_node_used_resources(node)
        vcpu_free = node.vcpu_capacity-resources_used.get('vcpu')
        memory_free = node.memory_mb_capacity-resources_used.get('memory')
        disk_free = node.disk_gb_capacity-resources_used.get('disk')

        return dict(vcpu=vcpu_free, memory=memory_free, disk=disk_free)

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
            except exception.ComputeResourceNotFound:
                root.append(instance.as_xml_element())

        return etree.tostring(root, pretty_print=True).decode('utf-8')

    def to_list(self):
        ret_list = []
        for cn in sorted(self.get_all_compute_nodes().values(),
                         key=lambda cn: cn.uuid):
            in_dict = {}
            for field in cn.fields:
                new_name = "node_"+str(field)
                in_dict[new_name] = cn[field]
            node_instances = self.get_node_instances(cn)
            if not node_instances:
                deep_in_dict = in_dict.copy()
                ret_list.append(deep_in_dict)
                continue
            for instance in sorted(node_instances, key=lambda x: x.uuid):
                for field in instance.fields:
                    new_name = "server_"+str(field)
                    in_dict[new_name] = instance[field]
                if in_dict != {}:
                    deep_in_dict = in_dict.copy()
                    ret_list.append(deep_in_dict)
        return ret_list

    @classmethod
    def from_xml(cls, data):
        model = cls()

        root = etree.fromstring(data)
        for cn in root.findall('.//ComputeNode'):
            node = element.ComputeNode(**cn.attrib)
            model.add_node(node)

        for inst in root.findall('.//Instance'):
            instance = element.Instance(**inst.attrib)
            instance.watcher_exclude = ast.literal_eval(
                inst.attrib["watcher_exclude"])
            model.add_instance(instance)

            parent = inst.getparent()
            if parent.tag == 'ComputeNode':
                node = model.get_node_by_uuid(parent.get('uuid'))
                model.map_instance(instance, node)
            else:
                model.add_instance(instance)

        return model

    @classmethod
    def is_isomorphic(cls, G1, G2):
        def node_match(node1, node2):
            return node1['attr'].as_dict() == node2['attr'].as_dict()
        return nx.algorithms.isomorphism.isomorph.is_isomorphic(
            G1, G2, node_match=node_match)


class StorageModelRoot(nx.DiGraph, base.Model):
    """Cluster graph for an Openstack cluster."""

    def __init__(self, stale=False):
        super(StorageModelRoot, self).__init__()
        self.stale = stale

    def __nonzero__(self):
        return not self.stale

    __bool__ = __nonzero__

    @staticmethod
    def assert_node(obj):
        if not isinstance(obj, element.StorageNode):
            raise exception.IllegalArgumentException(
                message=_("'obj' argument type is not valid: %s") % type(obj))

    @staticmethod
    def assert_pool(obj):
        if not isinstance(obj, element.Pool):
            raise exception.IllegalArgumentException(
                message=_("'obj' argument type is not valid: %s") % type(obj))

    @staticmethod
    def assert_volume(obj):
        if not isinstance(obj, element.Volume):
            raise exception.IllegalArgumentException(
                message=_("'obj' argument type is not valid: %s") % type(obj))

    @lockutils.synchronized("storage_model")
    def add_node(self, node):
        self.assert_node(node)
        super(StorageModelRoot, self).add_node(node.host, attr=node)

    @lockutils.synchronized("storage_model")
    def add_pool(self, pool):
        self.assert_pool(pool)
        super(StorageModelRoot, self).add_node(pool.name, attr=pool)

    @lockutils.synchronized("storage_model")
    def remove_node(self, node):
        self.assert_node(node)
        try:
            super(StorageModelRoot, self).remove_node(node.host)
        except nx.NetworkXError as exc:
            LOG.exception(exc)
            raise exception.StorageNodeNotFound(name=node.host)

    @lockutils.synchronized("storage_model")
    def remove_pool(self, pool):
        self.assert_pool(pool)
        try:
            super(StorageModelRoot, self).remove_node(pool.name)
        except nx.NetworkXError as exc:
            LOG.exception(exc)
            raise exception.PoolNotFound(name=pool.name)

    @lockutils.synchronized("storage_model")
    def map_pool(self, pool, node):
        """Map a newly created pool to a node

        :param pool: :py:class:`~.node.Pool` object or pool name
        :param node: :py:class:`~.node.StorageNode` object or node host
        """
        if isinstance(pool, str):
            pool = self.get_pool_by_pool_name(pool)
        if isinstance(node, str):
            node = self.get_node_by_name(node)
        self.assert_node(node)
        self.assert_pool(pool)

        self.add_edge(pool.name, node.host)

    @lockutils.synchronized("storage_model")
    def unmap_pool(self, pool, node):
        """Unmap a pool from a node

        :param pool: :py:class:`~.node.Pool` object or pool name
        :param node: :py:class:`~.node.StorageNode` object or node name
        """
        if isinstance(pool, str):
            pool = self.get_pool_by_pool_name(pool)
        if isinstance(node, str):
            node = self.get_node_by_name(node)

        self.remove_edge(pool.name, node.host)

    @lockutils.synchronized("storage_model")
    def add_volume(self, volume):
        self.assert_volume(volume)
        super(StorageModelRoot, self).add_node(volume.uuid, attr=volume)

    @lockutils.synchronized("storage_model")
    def remove_volume(self, volume):
        self.assert_volume(volume)
        try:
            super(StorageModelRoot, self).remove_node(volume.uuid)
        except nx.NetworkXError as exc:
            LOG.exception(exc)
            raise exception.VolumeNotFound(name=volume.uuid)

    @lockutils.synchronized("storage_model")
    def map_volume(self, volume, pool):
        """Map a newly created volume to a pool

        :param volume: :py:class:`~.volume.Volume` object or volume UUID
        :param pool: :py:class:`~.node.Pool` object or pool name
        """
        if isinstance(volume, str):
            volume = self.get_volume_by_uuid(volume)
        if isinstance(pool, str):
            pool = self.get_pool_by_pool_name(pool)
        self.assert_pool(pool)
        self.assert_volume(volume)

        self.add_edge(volume.uuid, pool.name)

    @lockutils.synchronized("storage_model")
    def unmap_volume(self, volume, pool):
        """Unmap a volume from a pool

        :param volume: :py:class:`~.volume.Volume` object or volume UUID
        :param pool: :py:class:`~.node.Pool` object or pool name
        """
        if isinstance(volume, str):
            volume = self.get_volume_by_uuid(volume)
        if isinstance(pool, str):
            pool = self.get_pool_by_pool_name(pool)

        self.remove_edge(volume.uuid, pool.name)

    def delete_volume(self, volume):
        self.assert_volume(volume)
        self.remove_volume(volume)

    @lockutils.synchronized("storage_model")
    def get_all_storage_nodes(self):
        return {host: cn['attr'] for host, cn in self.nodes(data=True)
                if isinstance(cn['attr'], element.StorageNode)}

    @lockutils.synchronized("storage_model")
    def get_node_by_name(self, name):
        try:
            return self._get_by_name(name.split("#")[0])
        except exception.StorageResourceNotFound:
            raise exception.StorageNodeNotFound(name=name)

    @lockutils.synchronized("storage_model")
    def get_pool_by_pool_name(self, name):
        try:
            return self._get_by_name(name)
        except exception.StorageResourceNotFound:
            raise exception.PoolNotFound(name=name)

    @lockutils.synchronized("storage_model")
    def get_volume_by_uuid(self, uuid):
        try:
            return self._get_by_uuid(uuid)
        except exception.StorageResourceNotFound:
            raise exception.VolumeNotFound(name=uuid)

    def _get_by_uuid(self, uuid):
        try:
            return self.nodes[uuid]['attr']
        except Exception as exc:
            LOG.exception(exc)
            raise exception.StorageResourceNotFound(name=uuid)

    def _get_by_name(self, name):
        try:
            return self.nodes[name]['attr']
        except Exception as exc:
            LOG.exception(exc)
            raise exception.StorageResourceNotFound(name=name)

    @lockutils.synchronized("storage_model")
    def get_node_by_pool_name(self, pool_name):
        pool = self._get_by_name(pool_name)
        for node_name in self.neighbors(pool.name):
            node = self._get_by_name(node_name)
            if isinstance(node, element.StorageNode):
                return node
        raise exception.StorageNodeNotFound(name=pool_name)

    @lockutils.synchronized("storage_model")
    def get_node_pools(self, node):
        self.assert_node(node)
        node_pools = []
        for pool_name in self.predecessors(node.host):
            pool = self._get_by_name(pool_name)
            if isinstance(pool, element.Pool):
                node_pools.append(pool)

        return node_pools

    @lockutils.synchronized("storage_model")
    def get_pool_by_volume(self, volume):
        self.assert_volume(volume)
        volume = self._get_by_uuid(volume.uuid)
        for p in self.neighbors(volume.uuid):
            pool = self._get_by_name(p)
            if isinstance(pool, element.Pool):
                return pool
        raise exception.PoolNotFound(name=volume.uuid)

    @lockutils.synchronized("storage_model")
    def get_all_volumes(self):
        return {name: vol['attr'] for name, vol in self.nodes(data=True)
                if isinstance(vol['attr'], element.Volume)}

    @lockutils.synchronized("storage_model")
    def get_pool_volumes(self, pool):
        self.assert_pool(pool)
        volumes = []
        for vol in self.predecessors(pool.name):
            volume = self._get_by_uuid(vol)
            if isinstance(volume, element.Volume):
                volumes.append(volume)

        return volumes

    def to_string(self):
        return self.to_xml()

    def to_xml(self):
        root = etree.Element("ModelRoot")
        # Build storage node tree
        for cn in sorted(self.get_all_storage_nodes().values(),
                         key=lambda cn: cn.host):
            storage_node_el = cn.as_xml_element()
            # Build mapped pool tree
            node_pools = self.get_node_pools(cn)
            for pool in sorted(node_pools, key=lambda x: x.name):
                pool_el = pool.as_xml_element()
                storage_node_el.append(pool_el)
                # Build mapped volume tree
                pool_volumes = self.get_pool_volumes(pool)
                for volume in sorted(pool_volumes, key=lambda x: x.uuid):
                    volume_el = volume.as_xml_element()
                    pool_el.append(volume_el)

            root.append(storage_node_el)

        # Build unmapped volume tree (i.e. not assigned to any pool)
        for volume in sorted(self.get_all_volumes().values(),
                             key=lambda vol: vol.uuid):
            try:
                self.get_pool_by_volume(volume)
            except (exception.VolumeNotFound, exception.PoolNotFound):
                root.append(volume.as_xml_element())

        return etree.tostring(root, pretty_print=True).decode('utf-8')

    @classmethod
    def from_xml(cls, data):
        model = cls()

        root = etree.fromstring(data)
        for cn in root.findall('.//StorageNode'):
            ndata = {}
            for attr, val in cn.items():
                ndata[attr] = val
            volume_type = ndata.get('volume_type')
            if volume_type:
                ndata['volume_type'] = [volume_type]
            node = element.StorageNode(**ndata)
            model.add_node(node)

        for p in root.findall('.//Pool'):
            pool = element.Pool(**p.attrib)
            model.add_pool(pool)

            parent = p.getparent()
            if parent.tag == 'StorageNode':
                node = model.get_node_by_name(parent.get('host'))
                model.map_pool(pool, node)
            else:
                model.add_pool(pool)

        for vol in root.findall('.//Volume'):
            volume = element.Volume(**vol.attrib)
            model.add_volume(volume)

            parent = vol.getparent()
            if parent.tag == 'Pool':
                pool = model.get_pool_by_pool_name(parent.get('name'))
                model.map_volume(volume, pool)
            else:
                model.add_volume(volume)

        return model

    @classmethod
    def is_isomorphic(cls, G1, G2):
        return nx.algorithms.isomorphism.isomorph.is_isomorphic(
            G1, G2)


class BaremetalModelRoot(nx.DiGraph, base.Model):

    """Cluster graph for an Openstack cluster: Baremetal Cluster."""

    def __init__(self, stale=False):
        super(BaremetalModelRoot, self).__init__()
        self.stale = stale

    def __nonzero__(self):
        return not self.stale

    __bool__ = __nonzero__

    @staticmethod
    def assert_node(obj):
        if not isinstance(obj, element.IronicNode):
            raise exception.IllegalArgumentException(
                message=_("'obj' argument type is not valid: %s") % type(obj))

    @lockutils.synchronized("baremetal_model")
    def add_node(self, node):
        self.assert_node(node)
        super(BaremetalModelRoot, self).add_node(node.uuid, attr=node)

    @lockutils.synchronized("baremetal_model")
    def remove_node(self, node):
        self.assert_node(node)
        try:
            super(BaremetalModelRoot, self).remove_node(node.uuid)
        except nx.NetworkXError as exc:
            LOG.exception(exc)
            raise exception.IronicNodeNotFound(uuid=node.uuid)

    @lockutils.synchronized("baremetal_model")
    def get_all_ironic_nodes(self):
        return {uuid: cn['attr'] for uuid, cn in self.nodes(data=True)
                if isinstance(cn['attr'], element.IronicNode)}

    @lockutils.synchronized("baremetal_model")
    def get_node_by_uuid(self, uuid):
        try:
            return self._get_by_uuid(uuid)
        except exception.BaremetalResourceNotFound:
            raise exception.IronicNodeNotFound(uuid=uuid)

    def _get_by_uuid(self, uuid):
        try:
            return self.nodes[uuid]['attr']
        except Exception as exc:
            LOG.exception(exc)
        raise exception.BaremetalResourceNotFound(name=uuid)

    def to_string(self):
        return self.to_xml()

    def to_xml(self):
        root = etree.Element("ModelRoot")
        # Build Ironic node tree
        for cn in sorted(self.get_all_ironic_nodes().values(),
                         key=lambda cn: cn.uuid):
            ironic_node_el = cn.as_xml_element()
            root.append(ironic_node_el)

        return etree.tostring(root, pretty_print=True).decode('utf-8')

    @classmethod
    def from_xml(cls, data):
        model = cls()

        root = etree.fromstring(data)
        for cn in root.findall('.//IronicNode'):
            node = element.IronicNode(**cn.attrib)
            model.add_node(node)

        return model

    @classmethod
    def is_isomorphic(cls, G1, G2):
        return nx.algorithms.isomorphism.isomorph.is_isomorphic(
            G1, G2)
