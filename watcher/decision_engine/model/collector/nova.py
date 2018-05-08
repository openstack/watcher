# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Intel Innovation and Research Ireland Ltd.
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

from oslo_log import log

from watcher.common import exception
from watcher.common import nova_helper
from watcher.decision_engine.model.collector import base
from watcher.decision_engine.model import element
from watcher.decision_engine.model import model_root
from watcher.decision_engine.model.notification import nova
from watcher.decision_engine.scope import compute as compute_scope

LOG = log.getLogger(__name__)


class NovaClusterDataModelCollector(base.BaseClusterDataModelCollector):
    """Nova cluster data model collector

    The Nova cluster data model collector creates an in-memory
    representation of the resources exposed by the compute service.
    """

    HOST_AGGREGATES = "#/items/properties/compute/host_aggregates/"
    SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "host_aggregates": {
                    "type": "array",
                    "items": {
                        "anyOf": [
                            {"$ref": HOST_AGGREGATES + "id"},
                            {"$ref": HOST_AGGREGATES + "name"},
                        ]
                    }
                },
                "availability_zones": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "name": {
                                "type": "string"
                            }
                        },
                        "additionalProperties": False
                    }
                },
                "exclude": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "instances": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "uuid": {
                                            "type": "string"
                                        }
                                    },
                                    "additionalProperties": False
                                }
                            },
                            "compute_nodes": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "name": {
                                            "type": "string"
                                        }
                                    },
                                    "additionalProperties": False
                                }
                            },
                            "host_aggregates": {
                                "type": "array",
                                "items": {
                                    "anyOf": [
                                        {"$ref": HOST_AGGREGATES + "id"},
                                        {"$ref": HOST_AGGREGATES + "name"},
                                    ]
                                }
                            },
                            "instance_metadata": {
                                "type": "array",
                                "items": {
                                    "type": "object"
                                }
                            },
                            "projects": {
                                "type": "array",
                                "items": {
                                    "type": "object",
                                    "properties": {
                                        "uuid": {
                                            "type": "string"
                                        }
                                    },
                                    "additionalProperties": False
                                }
                            }
                        },
                        "additionalProperties": False
                    }
                }
            },
            "additionalProperties": False
        },
        "host_aggregates": {
            "id": {
                "properties": {
                    "id": {
                        "oneOf": [
                            {"type": "integer"},
                            {"enum": ["*"]}
                        ]
                    }
                },
                "additionalProperties": False
            },
            "name": {
                "properties": {
                    "name": {
                        "type": "string"
                    }
                },
                "additionalProperties": False
            }
        },
        "additionalProperties": False
    }

    def __init__(self, config, osc=None):
        super(NovaClusterDataModelCollector, self).__init__(config, osc)

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
            nova.LegacyInstanceResizeConfirmEnd(self),
            nova.LegacyInstanceRebuildEnd(self),
        ]

    def get_audit_scope_handler(self, audit_scope):
        self._audit_scope_handler = compute_scope.ComputeScope(
            audit_scope, self.config)
        return self._audit_scope_handler

    def execute(self):
        """Build the compute cluster data model"""
        LOG.debug("Building latest Nova cluster data model")

        builder = ModelBuilder(self.osc)
        return builder.execute()


class ModelBuilder(object):
    """Build the graph-based model

    This model builder adds the following data"

    - Compute-related knowledge (Nova)
    - TODO(v-francoise): Storage-related knowledge (Cinder)
    - TODO(v-francoise): Network-related knowledge (Neutron)

    NOTE(v-francoise): This model builder is meant to be extended in the future
    to also include both storage and network information respectively coming
    from Cinder and Neutron. Some prelimary work has been done in this
    direction in https://review.openstack.org/#/c/362730 but since we cannot
    guarantee a sufficient level of consistency for neither the storage nor the
    network part before the end of the Ocata cycle, this work has been
    re-scheduled for Pike. In the meantime, all the associated code has been
    commented out.
    """
    def __init__(self, osc):
        self.osc = osc
        self.model = model_root.ModelRoot()
        self.nova = osc.nova()
        self.nova_helper = nova_helper.NovaHelper(osc=self.osc)
        # self.neutron = osc.neutron()
        # self.cinder = osc.cinder()

    def _add_physical_layer(self):
        """Add the physical layer of the graph.

        This includes components which represent actual infrastructure
        hardware.
        """
        for cnode in self.nova_helper.get_compute_node_list():
            self.add_compute_node(cnode)

    def add_compute_node(self, node):
        # Build and add base node.
        compute_node = self.build_compute_node(node)
        self.model.add_node(compute_node)

        # NOTE(v-francoise): we can encapsulate capabilities of the node
        # (special instruction sets of CPUs) in the attributes; as well as
        # sub-nodes can be added re-presenting e.g. GPUs/Accelerators etc.

        # # Build & add disk, memory, network and cpu nodes.
        # disk_id, disk_node = self.build_disk_compute_node(base_id, node)
        # self.add_node(disk_id, disk_node)
        # mem_id, mem_node = self.build_memory_compute_node(base_id, node)
        # self.add_node(mem_id, mem_node)
        # net_id, net_node = self._build_network_compute_node(base_id)
        # self.add_node(net_id, net_node)
        # cpu_id, cpu_node = self.build_cpu_compute_node(base_id, node)
        # self.add_node(cpu_id, cpu_node)

        # # Connect the base compute node to the dependent nodes.
        # self.add_edges_from([(base_id, disk_id), (base_id, mem_id),
        #                      (base_id, cpu_id), (base_id, net_id)],
        #                     label="contains")

    def build_compute_node(self, node):
        """Build a compute node from a Nova compute node

        :param node: A node hypervisor instance
        :type node: :py:class:`~novaclient.v2.hypervisors.Hypervisor`
        """
        # build up the compute node.
        compute_service = self.nova_helper.get_service(node.service["id"])
        node_attributes = {
            "id": node.id,
            "uuid": compute_service.host,
            "hostname": node.hypervisor_hostname,
            "memory": node.memory_mb,
            "disk": node.free_disk_gb,
            "disk_capacity": node.local_gb,
            "vcpus": node.vcpus,
            "state": node.state,
            "status": node.status,
            "disabled_reason": compute_service.disabled_reason}

        compute_node = element.ComputeNode(**node_attributes)
        # compute_node = self._build_node("physical", "compute", "hypervisor",
        #                                 node_attributes)
        return compute_node

    # def _build_network_compute_node(self, base_node):
    #     attributes = {}
    #     net_node = self._build_node("physical", "network", "NIC", attributes)
    #     net_id = "{}_network".format(base_node)
    #     return net_id, net_node

    # def build_disk_compute_node(self, base_node, compute):
    #     # Build disk node attributes.
    #     disk_attributes = {
    #         "size_gb": compute.local_gb,
    #         "used_gb": compute.local_gb_used,
    #         "available_gb": compute.free_disk_gb}
    #     disk_node = self._build_node("physical", "storage", "disk",
    #                                  disk_attributes)
    #     disk_id = "{}_disk".format(base_node)
    #     return disk_id, disk_node

    # def build_memory_compute_node(self, base_node, compute):
    #     # Build memory node attributes.
    #     memory_attrs = {"size_mb": compute.memory_mb,
    #                     "used_mb": compute.memory_mb_used,
    #                     "available_mb": compute.free_ram_mb}
    #     memory_node = self._build_node("physical", "memory", "memory",
    #                                    memory_attrs)
    #     memory_id = "{}_memory".format(base_node)
    #     return memory_id, memory_node

    # def build_cpu_compute_node(self, base_node, compute):
    #     # Build memory node attributes.
    #     cpu_attributes = {"vcpus": compute.vcpus,
    #                       "vcpus_used": compute.vcpus_used,
    #                       "info": jsonutils.loads(compute.cpu_info)}
    #     cpu_node = self._build_node("physical", "cpu", "cpu", cpu_attributes)
    #     cpu_id = "{}_cpu".format(base_node)
    #     return cpu_id, cpu_node

    # @staticmethod
    # def _build_node(layer, category, node_type, attributes):
    #     return {"layer": layer, "category": category, "type": node_type,
    #             "attributes": attributes}

    def _add_virtual_layer(self):
        """Add the virtual layer to the graph.

        This layer is the virtual components of the infrastructure,
        such as vms.
        """
        self._add_virtual_servers()
        # self._add_virtual_network()
        # self._add_virtual_storage()

    def _add_virtual_servers(self):
        all_instances = self.nova_helper.get_instance_list()
        for inst in all_instances:
            # Add Node
            instance = self._build_instance_node(inst)
            self.model.add_instance(instance)
            # Get the cnode_name uuid.
            cnode_uuid = getattr(inst, "OS-EXT-SRV-ATTR:host")
            if cnode_uuid is None:
                # The instance is not attached to any Compute node
                continue
            try:
                # Nova compute node
                # cnode = self.nova_helper.get_compute_node_by_hostname(
                #     cnode_uuid)
                compute_node = self.model.get_node_by_uuid(
                    cnode_uuid)
                # Connect the instance to its compute node
                self.model.map_instance(instance, compute_node)
            except exception.ComputeNodeNotFound:
                continue

    def _build_instance_node(self, instance):
        """Build an instance node

        Create an instance node for the graph using nova and the
        `server` nova object.
        :param instance: Nova VM object.
        :return: An instance node for the graph.
        """
        flavor = instance.flavor
        instance_attributes = {
            "uuid": instance.id,
            "human_id": instance.human_id,
            "memory": flavor["ram"],
            "disk": flavor["disk"],
            "disk_capacity": flavor["disk"],
            "vcpus": flavor["vcpus"],
            "state": getattr(instance, "OS-EXT-STS:vm_state"),
            "metadata": instance.metadata,
            "project_id": instance.tenant_id}

        # node_attributes = dict()
        # node_attributes["layer"] = "virtual"
        # node_attributes["category"] = "compute"
        # node_attributes["type"] = "compute"
        # node_attributes["attributes"] = instance_attributes
        return element.Instance(**instance_attributes)

    # def _add_virtual_storage(self):
    #     try:
    #         volumes = self.cinder.volumes.list()
    #     except Exception:
    #         return
    #     for volume in volumes:
    #         volume_id, volume_node = self._build_storage_node(volume)
    #         self.add_node(volume_id, volume_node)
    #         host = self._get_volume_host_id(volume_node)
    #         self.add_edge(volume_id, host)
    #         # Add connections to an instance.
    #         if volume_node['attributes']['attachments']:
    #             for attachment in volume_node['attributes']['attachments']:
    #                 self.add_edge(volume_id, attachment['server_id'],
    #                               label='ATTACHED_TO')
    #             volume_node['attributes'].pop('attachments')

    # def _add_virtual_network(self):
    #     try:
    #         routers = self.neutron.list_routers()
    #     except Exception:
    #         return

    #     for network in self.neutron.list_networks()['networks']:
    #         self.add_node(*self._build_network(network))

    #     for router in routers['routers']:
    #         self.add_node(*self._build_router(router))

    #     router_interfaces, _, compute_ports = self._group_ports()
    #     for router_interface in router_interfaces:
    #         interface = self._build_router_interface(router_interface)
    #         router_interface_id = interface[0]
    #         router_interface_node = interface[1]
    #         router_id = interface[2]
    #         self.add_node(router_interface_id, router_interface_node)
    #         self.add_edge(router_id, router_interface_id)
    #         network_id = router_interface_node['attributes']['network_id']
    #         self.add_edge(router_interface_id, network_id)

    #     for compute_port in compute_ports:
    #         cp_id, cp_node, instance_id = self._build_compute_port_node(
    #             compute_port)
    #         self.add_node(cp_id, cp_node)
    #         self.add_edge(cp_id, vm_id)
    #         net_id = cp_node['attributes']['network_id']
    #         self.add_edge(net_id, cp_id)
    #         # Connect port to physical node
    #         phys_net_node = "{}_network".format(cp_node['attributes']
    #                                             ['binding:host_id'])
    #         self.add_edge(cp_id, phys_net_node)

    # def _get_volume_host_id(self, volume_node):
    #     host = volume_node['attributes']['os-vol-host-attr:host']
    #     if host.find('@') != -1:
    #         host = host.split('@')[0]
    #     elif host.find('#') != -1:
    #         host = host.split('#')[0]
    #     return "{}_disk".format(host)

    # def _build_storage_node(self, volume_obj):
    #     volume = volume_obj.__dict__
    #     volume["name"] = volume["id"]
    #     volume.pop("id")
    #     volume.pop("manager")
    #     node = self._build_node("virtual", "storage", 'volume', volume)
    #     return volume["name"], node

    # def _build_compute_port_node(self, compute_port):
    #     compute_port["name"] = compute_port["id"]
    #     compute_port.pop("id")
    #     nde_type = "{}_port".format(
    #         compute_port["device_owner"].split(":")[0])
    #     compute_port.pop("device_owner")
    #     device_id = compute_port["device_id"]
    #     compute_port.pop("device_id")
    #     node = self._build_node("virtual", "network", nde_type, compute_port)
    #     return compute_port["name"], node, device_id

    # def _group_ports(self):
    #     router_interfaces = []
    #     floating_ips = []
    #     compute_ports = []
    #     interface_types = ["network:router_interface",
    #                        'network:router_gateway']

    #     for port in self.neutron.list_ports()['ports']:
    #         if port['device_owner'] in interface_types:
    #             router_interfaces.append(port)
    #         elif port['device_owner'].startswith('compute:'):
    #             compute_ports.append(port)
    #         elif port['device_owner'] == 'network:floatingip':
    #             floating_ips.append(port)

    #     return router_interfaces, floating_ips, compute_ports

    # def _build_router_interface(self, interface):
    #     interface["name"] = interface["id"]
    #     interface.pop("id")
    #     node_type = interface["device_owner"].split(":")[1]
    #     node = self._build_node("virtual", "network", node_type, interface)
    #     return interface["name"], node, interface["device_id"]

    # def _build_router(self, router):
    #     router_attrs = {"uuid": router['id'],
    #                     "name": router['name'],
    #                     "state": router['status']}
    #     node = self._build_node('virtual', 'network', 'router', router_attrs)
    #     return str(router['id']), node

    # def _build_network(self, network):
    #     node = self._build_node('virtual', 'network', 'network', network)
    #     return network['id'], node

    def execute(self):
        """Instantiates the graph with the openstack cluster data.

        The graph is populated along 2 layers: virtual and physical. As each
        new layer is built connections are made back to previous layers.
        """
        self._add_physical_layer()
        self._add_virtual_layer()
        return self.model
