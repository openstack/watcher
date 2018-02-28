# -*- encoding: utf-8 -*-
# Copyright 2017 NEC Corporation
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

from oslo_log import log
from watcher.common import cinder_helper
from watcher.common import exception
from watcher.decision_engine.model import element
from watcher.decision_engine.model.notification import base
from watcher.decision_engine.model.notification import filtering

LOG = log.getLogger(__name__)


class CinderNotification(base.NotificationEndpoint):

    def __init__(self, collector):
        super(CinderNotification, self).__init__(collector)
        self._cinder = None

    @property
    def cinder(self):
        if self._cinder is None:
            self._cinder = cinder_helper.CinderHelper()
        return self._cinder

    def update_pool(self, pool, data):
        """Update the storage pool using the notification data."""
        pool.update({
            "total_capacity_gb": data['total'],
            "free_capacity_gb": data['free'],
            "provisioned_capacity_gb": data['provisioned'],
            "allocated_capacity_gb": data['allocated'],
            "virtual_free": data['virtual_free']
        })

        node_name = pool.name.split("#")[0]
        node = self.get_or_create_node(node_name)
        self.cluster_data_model.map_pool(pool, node)
        LOG.debug("Mapped pool %s to %s", pool.name, node.host)

    def update_pool_by_api(self, pool):
        """Update the storage pool using the API data."""
        if not pool:
            return
        _pool = self.cinder.get_storage_pool_by_name(pool.name)
        pool.update({
            "total_volumes": _pool.total_volumes,
            "total_capacity_gb": _pool.total_capacity_gb,
            "free_capacity_gb": _pool.free_capacity_gb,
            "provisioned_capacity_gb": _pool.provisioned_capacity_gb,
            "allocated_capacity_gb": _pool.allocated_capacity_gb
        })
        node_name = pool.name.split("#")[0]
        node = self.get_or_create_node(node_name)
        self.cluster_data_model.map_pool(pool, node)
        LOG.debug("Mapped pool %s to %s", pool.name, node.host)

    def create_storage_node(self, name):
        """Create the storage node by querying the Cinder API."""
        try:
            _node = self.cinder.get_storage_node_by_name(name)
            _volume_type = self.cinder.get_volume_type_by_backendname(
                # name is formatted as host@backendname
                name.split('@')[1])
            storage_node = element.StorageNode(
                host=_node.host,
                zone=_node.zone,
                state=_node.state,
                status=_node.status,
                volume_type=_volume_type)
            return storage_node
        except Exception as exc:
            LOG.exception(exc)
            LOG.debug("Could not create storage node %s.", name)
            raise exception.StorageNodeNotFound(name=name)

    def get_or_create_node(self, name):
        """Get storage node by name, otherwise create storage node"""
        if name is None:
            LOG.debug("Storage node name not provided: skipping")
            return
        try:
            return self.cluster_data_model.get_node_by_name(name)
        except exception.StorageNodeNotFound:
            # The node didn't exist yet so we create a new node object
            node = self.create_storage_node(name)
            LOG.debug("New storage node created: %s", name)
            self.cluster_data_model.add_node(node)
            LOG.debug("New storage node added: %s", name)
            return node

    def create_pool(self, pool_name):
        """Create the storage pool by querying the Cinder API."""
        try:
            _pool = self.cinder.get_storage_pool_by_name(pool_name)
            pool = element.Pool(
                name=_pool.name,
                total_volumes=_pool.total_volumes,
                total_capacity_gb=_pool.total_capacity_gb,
                free_capacity_gb=_pool.free_capacity_gb,
                provisioned_capacity_gb=_pool.provisioned_capacity_gb,
                allocated_capacity_gb=_pool.allocated_capacity_gb)
            return pool
        except Exception as exc:
            LOG.exception(exc)
            LOG.debug("Could not refresh the pool %s.", pool_name)
            raise exception.PoolNotFound(name=pool_name)

    def get_or_create_pool(self, name):
        if not name:
            LOG.debug("Pool name not provided: skipping")
            return
        try:
            return self.cluster_data_model.get_pool_by_pool_name(name)
        except exception.PoolNotFound:
            # The pool didn't exist yet so we create a new pool object
            pool = self.create_pool(name)
            LOG.debug("New storage pool created: %s", name)
            self.cluster_data_model.add_pool(pool)
            LOG.debug("New storage pool added: %s", name)
            return pool

    def get_or_create_volume(self, volume_id, pool_name=None):
        try:
            if pool_name:
                self.get_or_create_pool(pool_name)
        except exception.PoolNotFound:
            LOG.warning("Could not find storage pool %(pool)s for "
                        "volume %(volume)s",
                        dict(pool=pool_name, volume=volume_id))
        try:
            return self.cluster_data_model.get_volume_by_uuid(volume_id)
        except exception.VolumeNotFound:
            # The volume didn't exist yet so we create a new volume object
            volume = element.Volume(uuid=volume_id)
            self.cluster_data_model.add_volume(volume)
        return volume

    def update_volume(self, volume, data):
        """Update the volume using the notification data."""

        def _keyReplace(key):
            if key == 'instance_uuid':
                return 'server_id'
            if key == 'id':
                return 'attachment_id'

        attachments = [
            {_keyReplace(k): v for k, v in six.iteritems(d)
                if k in ('instance_uuid', 'id')}
            for d in data['volume_attachment']
        ]

        # glance_metadata is provided if volume is bootable
        bootable = False
        if 'glance_metadata' in data:
            bootable = True

        volume.update({
            "name": data['display_name'] or "",
            "size": data['size'],
            "status": data['status'],
            "attachments": attachments,
            "snapshot_id": data['snapshot_id'] or "",
            "project_id": data['tenant_id'],
            "metadata": data['metadata'],
            "bootable": bootable
            })

        try:
            # if volume is under pool, let's update pool element.
            # get existing pool or create pool by cinder api
            pool = self.get_or_create_pool(data['host'])
            self.update_pool_by_api(pool)

        except exception.PoolNotFound as exc:
            LOG.exception(exc)
            pool = None

        self.update_volume_mapping(volume, pool)

    def update_volume_mapping(self, volume, pool):
        if pool is None:
            self.cluster_data_model.add_volume(volume)
            LOG.debug("Volume %s not yet attached to any pool: skipping",
                      volume.uuid)
            return
        try:
            try:
                current_pool = (
                    self.cluster_data_model.get_pool_by_volume(
                        volume) or self.get_or_create_pool(pool.name))
            except exception.PoolNotFound as exc:
                LOG.exception(exc)
                # If we can't create the pool,
                # we consider the volume as unmapped
                current_pool = None

            LOG.debug("Mapped pool %s found", pool.name)
            if current_pool and pool != current_pool:
                LOG.debug("Unmapping volume %s from %s",
                          volume.uuid, pool.name)
                self.cluster_data_model.unmap_volume(volume, current_pool)
        except exception.VolumeNotFound:
            # The instance didn't exist yet so we map it for the first time
            LOG.debug("New volume: mapping it to %s", pool.name)
        finally:
            if pool:
                self.cluster_data_model.map_volume(volume, pool)
                LOG.debug("Mapped volume %s to %s", volume.uuid, pool.name)

    def delete_volume(self, volume, pool):
        try:
            self.cluster_data_model.delete_volume(volume)
        except Exception:
            LOG.info("Volume %s already deleted", volume.uuid)

        try:
            if pool:
                # if volume is under pool, let's update pool element.
                # get existing pool or create pool by cinder api
                pool = self.get_or_create_pool(pool.name)
                self.update_pool_by_api(pool)
        except exception.PoolNotFound as exc:
            LOG.exception(exc)
            pool = None


class CapacityNotificationEndpoint(CinderNotification):

    @property
    def filter_rule(self):
        """Cinder capacity notification filter"""
        return filtering.NotificationFilter(
            publisher_id=r'capacity.*',
            event_type='capacity.pool',
        )

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        ctxt.request_id = metadata['message_id']
        ctxt.project_domain = event_type
        LOG.info("Event '%(event)s' received from %(publisher)s "
                 "with metadata %(metadata)s",
                 dict(event=event_type,
                      publisher=publisher_id,
                      metadata=metadata))
        LOG.debug(payload)
        name = payload['name_to_id']
        try:
            pool = self.get_or_create_pool(name)
            self.update_pool(pool, payload)
        except exception.PoolNotFound as exc:
            LOG.exception(exc)


class VolumeNotificationEndpoint(CinderNotification):
    publisher_id_regex = r'^volume.*'


class VolumeCreateEnd(VolumeNotificationEndpoint):

    @property
    def filter_rule(self):
        """Cinder volume notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='volume.create.end',
        )

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        ctxt.request_id = metadata['message_id']
        ctxt.project_domain = event_type
        LOG.info("Event '%(event)s' received from %(publisher)s "
                 "with metadata %(metadata)s",
                 dict(event=event_type,
                      publisher=publisher_id,
                      metadata=metadata))
        LOG.debug(payload)
        volume_id = payload['volume_id']
        poolname = payload['host']
        volume = self.get_or_create_volume(volume_id, poolname)
        self.update_volume(volume, payload)


class VolumeUpdateEnd(VolumeNotificationEndpoint):

    @property
    def filter_rule(self):
        """Cinder volume notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='volume.update.end',
        )

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        ctxt.request_id = metadata['message_id']
        ctxt.project_domain = event_type
        LOG.info("Event '%(event)s' received from %(publisher)s "
                 "with metadata %(metadata)s",
                 dict(event=event_type,
                      publisher=publisher_id,
                      metadata=metadata))
        LOG.debug(payload)
        volume_id = payload['volume_id']
        poolname = payload['host']
        volume = self.get_or_create_volume(volume_id, poolname)
        self.update_volume(volume, payload)


class VolumeAttachEnd(VolumeUpdateEnd):

    @property
    def filter_rule(self):
        """Cinder volume notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='volume.attach.end',
        )


class VolumeDetachEnd(VolumeUpdateEnd):

    @property
    def filter_rule(self):
        """Cinder volume notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='volume.detach.end',
        )


class VolumeResizeEnd(VolumeUpdateEnd):

    @property
    def filter_rule(self):
        """Cinder volume notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='volume.resize.end',
        )


class VolumeDeleteEnd(VolumeNotificationEndpoint):

    @property
    def filter_rule(self):
        """Cinder volume notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='volume.delete.end',
        )

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        ctxt.request_id = metadata['message_id']
        ctxt.project_domain = event_type
        LOG.info("Event '%(event)s' received from %(publisher)s "
                 "with metadata %(metadata)s",
                 dict(event=event_type,
                      publisher=publisher_id,
                      metadata=metadata))
        LOG.debug(payload)
        volume_id = payload['volume_id']
        poolname = payload['host']
        volume = self.get_or_create_volume(volume_id, poolname)

        try:
            pool = self.get_or_create_pool(poolname)
        except exception.PoolNotFound as exc:
            LOG.exception(exc)
            pool = None

        self.delete_volume(volume, pool)
