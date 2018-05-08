# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <Vincent.FRANCOISE@b-com.com>
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
from watcher.common import exception
from watcher.common import nova_helper
from watcher.decision_engine.model import element
from watcher.decision_engine.model.notification import base
from watcher.decision_engine.model.notification import filtering

LOG = log.getLogger(__name__)


class NovaNotification(base.NotificationEndpoint):

    def __init__(self, collector):
        super(NovaNotification, self).__init__(collector)
        self._nova = None

    @property
    def nova(self):
        if self._nova is None:
            self._nova = nova_helper.NovaHelper()
        return self._nova

    def get_or_create_instance(self, instance_uuid, node_uuid=None):
        try:
            if node_uuid:
                self.get_or_create_node(node_uuid)
        except exception.ComputeNodeNotFound:
            LOG.warning("Could not find compute node %(node)s for "
                        "instance %(instance)s",
                        dict(node=node_uuid, instance=instance_uuid))
        try:
            instance = self.cluster_data_model.get_instance_by_uuid(
                instance_uuid)
        except exception.InstanceNotFound:
            # The instance didn't exist yet so we create a new instance object
            LOG.debug("New instance created: %s", instance_uuid)
            instance = element.Instance(uuid=instance_uuid)

            self.cluster_data_model.add_instance(instance)

        return instance

    def update_instance(self, instance, data):
        instance_data = data['nova_object.data']
        instance_flavor_data = instance_data['flavor']['nova_object.data']

        memory_mb = instance_flavor_data['memory_mb']
        num_cores = instance_flavor_data['vcpus']
        disk_gb = instance_flavor_data['root_gb']
        instance_metadata = data['nova_object.data']['metadata']

        instance.update({
            'state': instance_data['state'],
            'hostname': instance_data['host_name'],
            'human_id': instance_data['display_name'],
            'memory': memory_mb,
            'vcpus': num_cores,
            'disk': disk_gb,
            'disk_capacity': disk_gb,
            'metadata': instance_metadata,
            'tenant_id': instance_data['tenant_id']
        })

        try:
            node = self.get_or_create_node(instance_data['host'])
        except exception.ComputeNodeNotFound as exc:
            LOG.exception(exc)
            # If we can't create the node, we consider the instance as unmapped
            node = None

        self.update_instance_mapping(instance, node)

    def legacy_update_instance(self, instance, data):
        memory_mb = data['memory_mb']
        num_cores = data['vcpus']
        disk_gb = data['root_gb']
        instance_metadata = data['metadata']

        instance.update({
            'state': data['state'],
            'hostname': data['hostname'],
            'human_id': data['display_name'],
            'memory': memory_mb,
            'vcpus': num_cores,
            'disk': disk_gb,
            'disk_capacity': disk_gb,
            'metadata': instance_metadata,
        })

        try:
            node = self.get_or_create_node(data['host'])
        except exception.ComputeNodeNotFound as exc:
            LOG.exception(exc)
            # If we can't create the node, we consider the instance as unmapped
            node = None

        self.update_instance_mapping(instance, node)

    def update_compute_node(self, node, data):
        """Update the compute node using the notification data."""
        node_data = data['nova_object.data']
        node_state = (
            element.ServiceState.OFFLINE.value
            if node_data['forced_down'] else element.ServiceState.ONLINE.value)
        node_status = (
            element.ServiceState.DISABLED.value
            if node_data['disabled'] else element.ServiceState.ENABLED.value)
        disabled_reason = (
            node_data['disabled_reason']
            if node_data['disabled'] else None)

        node.update({
            'hostname': node_data['host'],
            'state': node_state,
            'status': node_status,
            'disabled_reason': disabled_reason,
        })

    def create_compute_node(self, node_hostname):
        """Update the compute node by querying the Nova API."""
        try:
            _node = self.nova.get_compute_node_by_hostname(node_hostname)
            node = element.ComputeNode(
                id=_node.id,
                uuid=node_hostname,
                hostname=_node.hypervisor_hostname,
                state=_node.state,
                status=_node.status,
                memory=_node.memory_mb,
                vcpus=_node.vcpus,
                disk=_node.free_disk_gb,
                disk_capacity=_node.local_gb,
            )
            return node
        except Exception as exc:
            LOG.exception(exc)
            LOG.debug("Could not refresh the node %s.", node_hostname)
            raise exception.ComputeNodeNotFound(name=node_hostname)

        return False

    def get_or_create_node(self, uuid):
        if uuid is None:
            LOG.debug("Compute node UUID not provided: skipping")
            return
        try:
            return self.cluster_data_model.get_node_by_uuid(uuid)
        except exception.ComputeNodeNotFound:
            # The node didn't exist yet so we create a new node object
            node = self.create_compute_node(uuid)
            LOG.debug("New compute node created: %s", uuid)
            self.cluster_data_model.add_node(node)
            LOG.debug("New compute node mapped: %s", uuid)
            return node

    def update_instance_mapping(self, instance, node):
        if node is None:
            self.cluster_data_model.add_instance(instance)
            LOG.debug("Instance %s not yet attached to any node: skipping",
                      instance.uuid)
            return
        try:
            try:
                current_node = (
                    self.cluster_data_model.get_node_by_instance_uuid(
                        instance.uuid) or self.get_or_create_node(node.uuid))
            except exception.ComputeNodeNotFound as exc:
                LOG.exception(exc)
                # If we can't create the node,
                # we consider the instance as unmapped
                current_node = None

            LOG.debug("Mapped node %s found", node.uuid)
            if current_node and node != current_node:
                LOG.debug("Unmapping instance %s from %s",
                          instance.uuid, node.uuid)
                self.cluster_data_model.unmap_instance(instance, current_node)
        except exception.InstanceNotFound:
            # The instance didn't exist yet so we map it for the first time
            LOG.debug("New instance: mapping it to %s", node.uuid)
        finally:
            if node:
                self.cluster_data_model.map_instance(instance, node)
                LOG.debug("Mapped instance %s to %s", instance.uuid, node.uuid)

    def delete_instance(self, instance, node):
        try:
            self.cluster_data_model.delete_instance(instance, node)
        except Exception:
            LOG.info("Instance %s already deleted", instance.uuid)


class VersionedNotificationEndpoint(NovaNotification):
    publisher_id_regex = r'^nova-compute.*'


class UnversionedNotificationEndpoint(NovaNotification):
    publisher_id_regex = r'^compute.*'


class ServiceUpdated(VersionedNotificationEndpoint):

    @property
    def filter_rule(self):
        """Nova service.update notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='service.update',
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
        node_data = payload['nova_object.data']
        node_uuid = node_data['host']
        try:
            node = self.get_or_create_node(node_uuid)
            self.update_compute_node(node, payload)
        except exception.ComputeNodeNotFound as exc:
            LOG.exception(exc)


class InstanceCreated(VersionedNotificationEndpoint):

    @property
    def filter_rule(self):
        """Nova instance.update notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='instance.update',
            # To be "fully" created, an instance transitions
            # from the 'building' state to the 'active' one.
            # See https://docs.openstack.org/nova/latest/reference/
            # vm-states.html

            payload={
                'nova_object.data': {
                    'state': element.InstanceState.ACTIVE.value,
                    'state_update': {
                        'nova_object.data': {
                            'old_state': element.InstanceState.BUILDING.value,
                            'state': element.InstanceState.ACTIVE.value,
                        },
                        'nova_object.name': 'InstanceStateUpdatePayload',
                        'nova_object.namespace': 'nova',
                    },
                }
            }
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
        instance_data = payload['nova_object.data']
        instance_uuid = instance_data['uuid']
        node_uuid = instance_data.get('host')
        instance = self.get_or_create_instance(instance_uuid, node_uuid)

        self.update_instance(instance, payload)


class InstanceUpdated(VersionedNotificationEndpoint):

    @staticmethod
    def _match_not_new_instance_state(data):
        is_new_instance = (
            data['old_state'] == element.InstanceState.BUILDING.value and
            data['state'] == element.InstanceState.ACTIVE.value)

        return not is_new_instance

    @property
    def filter_rule(self):
        """Nova instance.update notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='instance.update',
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
        instance_data = payload['nova_object.data']
        instance_uuid = instance_data['uuid']
        node_uuid = instance_data.get('host')
        instance = self.get_or_create_instance(instance_uuid, node_uuid)

        self.update_instance(instance, payload)


class InstanceDeletedEnd(VersionedNotificationEndpoint):

    @property
    def filter_rule(self):
        """Nova service.update notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='instance.delete.end',
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

        instance_data = payload['nova_object.data']
        instance_uuid = instance_data['uuid']
        node_uuid = instance_data.get('host')
        instance = self.get_or_create_instance(instance_uuid, node_uuid)

        try:
            node = self.get_or_create_node(instance_data['host'])
        except exception.ComputeNodeNotFound as exc:
            LOG.exception(exc)
            # If we can't create the node, we consider the instance as unmapped
            node = None

        self.delete_instance(instance, node)


class LegacyInstanceUpdated(UnversionedNotificationEndpoint):

    @property
    def filter_rule(self):
        """Nova compute.instance.update notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='compute.instance.update',
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

        instance_uuid = payload['instance_id']
        node_uuid = payload.get('node')
        instance = self.get_or_create_instance(instance_uuid, node_uuid)

        self.legacy_update_instance(instance, payload)


class LegacyInstanceCreatedEnd(UnversionedNotificationEndpoint):

    @property
    def filter_rule(self):
        """Nova compute.instance.create.end notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='compute.instance.create.end',
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

        instance_uuid = payload['instance_id']
        node_uuid = payload.get('node')
        instance = self.get_or_create_instance(instance_uuid, node_uuid)

        self.legacy_update_instance(instance, payload)


class LegacyInstanceDeletedEnd(UnversionedNotificationEndpoint):

    @property
    def filter_rule(self):
        """Nova compute.instance.delete.end notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='compute.instance.delete.end',
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
        instance_uuid = payload['instance_id']
        node_uuid = payload.get('node')
        instance = self.get_or_create_instance(instance_uuid, node_uuid)

        try:
            node = self.get_or_create_node(payload['host'])
        except exception.ComputeNodeNotFound as exc:
            LOG.exception(exc)
            # If we can't create the node, we consider the instance as unmapped
            node = None

        self.delete_instance(instance, node)


class LegacyLiveMigratedEnd(UnversionedNotificationEndpoint):

    @property
    def filter_rule(self):
        """Nova *.live_migration.post.dest.end notification filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='compute.instance.live_migration.post.dest.end',
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

        instance_uuid = payload['instance_id']
        node_uuid = payload.get('node')
        instance = self.get_or_create_instance(instance_uuid, node_uuid)

        self.legacy_update_instance(instance, payload)


class LegacyInstanceResizeConfirmEnd(UnversionedNotificationEndpoint):

    @property
    def filter_rule(self):
        """Nova compute.instance.resize.confirm.end filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='compute.instance.resize.confirm.end',
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

        instance_uuid = payload['instance_id']
        node_uuid = payload.get('node')
        instance = self.get_or_create_instance(instance_uuid, node_uuid)

        self.legacy_update_instance(instance, payload)


class LegacyInstanceRebuildEnd(UnversionedNotificationEndpoint):

    @property
    def filter_rule(self):
        """Nova compute.instance.rebuild.end filter"""
        return filtering.NotificationFilter(
            publisher_id=self.publisher_id_regex,
            event_type='compute.instance.rebuild.end',
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

        instance_uuid = payload['instance_id']
        node_uuid = payload.get('node')
        instance = self.get_or_create_instance(instance_uuid, node_uuid)

        self.legacy_update_instance(instance, payload)
