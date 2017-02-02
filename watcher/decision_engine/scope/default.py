# -*- encoding: utf-8 -*-
# Copyright (c) 2016 Servionica
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

from watcher._i18n import _LW
from watcher.common import exception
from watcher.common import nova_helper
from watcher.decision_engine.scope import base


LOG = log.getLogger(__name__)


class DefaultScope(base.BaseScope):
    """Default Audit Scope Handler"""

    DEFAULT_SCHEMA = {
        "$schema": "http://json-schema.org/draft-04/schema#",
        "type": "array",
        "items": {
            "type": "object",
            "properties": {
                "host_aggregates": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {
                            "anyOf": [
                                {"type": ["string", "number"]}
                            ]
                        },
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
                                    }
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
                                    }
                                }
                            }
                        },
                        "additionalProperties": False
                    }
                }
            },
            "additionalProperties": False
        }
    }

    def __init__(self, scope, osc=None):
        super(DefaultScope, self).__init__(scope)
        self._osc = osc
        self.wrapper = nova_helper.NovaHelper(osc=self._osc)

    def remove_instance(self, cluster_model, instance, node_name):
        node = cluster_model.get_node_by_uuid(node_name)
        cluster_model.delete_instance(instance, node)

    def _check_wildcard(self, aggregate_list):
        if '*' in aggregate_list:
            if len(aggregate_list) == 1:
                return True
            else:
                raise exception.WildcardCharacterIsUsed(
                    resource="host aggregates")
        return False

    def _collect_aggregates(self, host_aggregates, allowed_nodes):
        aggregate_list = self.wrapper.get_aggregate_list()
        aggregate_ids = [aggregate['id'] for aggregate
                         in host_aggregates if 'id' in aggregate]
        aggregate_names = [aggregate['name'] for aggregate
                           in host_aggregates if 'name' in aggregate]
        include_all_nodes = any(self._check_wildcard(field)
                                for field in (aggregate_ids, aggregate_names))

        for aggregate in aggregate_list:
            detailed_aggregate = self.wrapper.get_aggregate_detail(
                aggregate.id)
            if (detailed_aggregate.id in aggregate_ids or
                detailed_aggregate.name in aggregate_names or
                    include_all_nodes):
                allowed_nodes.extend(detailed_aggregate.hosts)

    def _collect_zones(self, availability_zones, allowed_nodes):
        zone_list = self.wrapper.get_availability_zone_list()
        zone_names = [zone['name'] for zone
                      in availability_zones]
        include_all_nodes = False
        if '*' in zone_names:
            if len(zone_names) == 1:
                include_all_nodes = True
            else:
                raise exception.WildcardCharacterIsUsed(
                    resource="availability zones")
        for zone in zone_list:
            if zone.zoneName in zone_names or include_all_nodes:
                allowed_nodes.extend(zone.hosts.keys())

    def exclude_resources(self, resources, **kwargs):
        instances_to_exclude = kwargs.get('instances')
        nodes_to_exclude = kwargs.get('nodes')
        for resource in resources:
            if 'instances' in resource:
                instances_to_exclude.extend(
                    [instance['uuid'] for instance
                     in resource['instances']])
            elif 'compute_nodes' in resource:
                nodes_to_exclude.extend(
                    [host['name'] for host
                     in resource['compute_nodes']])

    def remove_nodes_from_model(self, nodes_to_remove, cluster_model):
        for node_uuid in nodes_to_remove:
            node = cluster_model.get_node_by_uuid(node_uuid)
            instances = cluster_model.get_node_instances(node)
            for instance in instances:
                self.remove_instance(cluster_model, instance, node_uuid)
            cluster_model.remove_node(node)

    def remove_instances_from_model(self, instances_to_remove, cluster_model):
        for instance_uuid in instances_to_remove:
            try:
                node_name = cluster_model.get_node_by_instance_uuid(
                    instance_uuid).uuid
            except exception.ComputeResourceNotFound:
                LOG.warning(_LW("The following instance %s cannot be found. "
                                "It might be deleted from CDM along with node"
                                " instance was hosted on."),
                            instance_uuid)
                continue
            self.remove_instance(
                cluster_model,
                cluster_model.get_instance_by_uuid(instance_uuid),
                node_name)

    def get_scoped_model(self, cluster_model):
        """Leave only nodes and instances proposed in the audit scope"""
        if not cluster_model:
            return None

        allowed_nodes = []
        nodes_to_exclude = []
        nodes_to_remove = set()
        instances_to_exclude = []
        model_hosts = list(cluster_model.get_all_compute_nodes().keys())

        if not self.scope:
            return cluster_model

        for rule in self.scope:
            if 'host_aggregates' in rule:
                self._collect_aggregates(rule['host_aggregates'],
                                         allowed_nodes)
            elif 'availability_zones' in rule:
                self._collect_zones(rule['availability_zones'],
                                    allowed_nodes)
            elif 'exclude' in rule:
                self.exclude_resources(
                    rule['exclude'], instances=instances_to_exclude,
                    nodes=nodes_to_exclude)

        instances_to_remove = set(instances_to_exclude)
        if allowed_nodes:
            nodes_to_remove = set(model_hosts) - set(allowed_nodes)
        nodes_to_remove.update(nodes_to_exclude)

        self.remove_nodes_from_model(nodes_to_remove, cluster_model)
        self.remove_instances_from_model(instances_to_remove, cluster_model)

        return cluster_model
