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

from watcher.common import exception
from watcher.common import nova_helper
from watcher.decision_engine.scope import base


LOG = log.getLogger(__name__)


class ComputeScope(base.BaseScope):
    """Compute Audit Scope Handler"""

    def __init__(self, scope, config, osc=None):
        super(ComputeScope, self).__init__(scope, config)
        self._osc = osc
        self.wrapper = nova_helper.NovaHelper(osc=self._osc)

    def remove_instance(self, cluster_model, instance, node_uuid):
        node = cluster_model.get_node_by_uuid(node_uuid)
        cluster_model.delete_instance(instance, node)

    def update_exclude_instance(self, cluster_model, instance, node_uuid):
        node = cluster_model.get_node_by_uuid(node_uuid)
        cluster_model.unmap_instance(instance, node)
        instance.update({"watcher_exclude": True})
        cluster_model.map_instance(instance, node)

    def _check_wildcard(self, aggregate_list):
        if '*' in aggregate_list:
            if len(aggregate_list) == 1:
                return True
            else:
                raise exception.WildcardCharacterIsUsed(
                    resource="host aggregates")
        return False

    def _collect_aggregates(self, host_aggregates, compute_nodes):
        aggregate_list = self.wrapper.get_aggregate_list()
        aggregate_ids = [aggregate['id'] for aggregate
                         in host_aggregates if 'id' in aggregate]
        aggregate_names = [aggregate['name'] for aggregate
                           in host_aggregates if 'name' in aggregate]
        include_all_nodes = any(self._check_wildcard(field)
                                for field in (aggregate_ids, aggregate_names))

        for aggregate in aggregate_list:
            if (aggregate.id in aggregate_ids or
                aggregate.name in aggregate_names or
                    include_all_nodes):
                compute_nodes.extend(aggregate.hosts)

    def _collect_zones(self, availability_zones, allowed_nodes):
        service_list = self.wrapper.get_service_list()
        zone_names = [zone['name'] for zone
                      in availability_zones]
        include_all_nodes = False
        if '*' in zone_names:
            if len(zone_names) == 1:
                include_all_nodes = True
            else:
                raise exception.WildcardCharacterIsUsed(
                    resource="availability zones")
        for service in service_list:
            if service.zone in zone_names or include_all_nodes:
                allowed_nodes.extend(service.host)

    def exclude_resources(self, resources, **kwargs):
        instances_to_exclude = kwargs.get('instances')
        nodes_to_exclude = kwargs.get('nodes')
        instance_metadata = kwargs.get('instance_metadata')
        projects_to_exclude = kwargs.get('projects')

        for resource in resources:
            if 'instances' in resource:
                instances_to_exclude.extend(
                    [instance['uuid'] for instance
                     in resource['instances']])
            elif 'compute_nodes' in resource:
                nodes_to_exclude.extend(
                    [host['name'] for host
                     in resource['compute_nodes']])
            elif 'host_aggregates' in resource:
                prohibited_nodes = []
                self._collect_aggregates(resource['host_aggregates'],
                                         prohibited_nodes)
                nodes_to_exclude.extend(prohibited_nodes)
            elif 'instance_metadata' in resource:
                instance_metadata.extend(
                    [metadata for metadata in resource['instance_metadata']])
            elif 'projects' in resource:
                projects_to_exclude.extend(
                    [project['uuid'] for project in resource['projects']])

    def remove_nodes_from_model(self, nodes_to_remove, cluster_model):
        for node_name in nodes_to_remove:
            node = cluster_model.get_node_by_name(node_name)
            instances = cluster_model.get_node_instances(node)
            for instance in instances:
                self.remove_instance(cluster_model, instance, node.uuid)
            cluster_model.remove_node(node)

    def update_exclude_instance_in_model(
            self, instances_to_exclude, cluster_model):
        for instance_uuid in instances_to_exclude:
            try:
                node_uuid = cluster_model.get_node_by_instance_uuid(
                    instance_uuid).uuid
            except exception.ComputeResourceNotFound:
                LOG.warning("The following instance %s cannot be found. "
                            "It might be deleted from CDM along with node"
                            " instance was hosted on.",
                            instance_uuid)
                continue
            self.update_exclude_instance(
                cluster_model,
                cluster_model.get_instance_by_uuid(instance_uuid),
                node_uuid)

    def exclude_instances_with_given_metadata(
            self, instance_metadata, cluster_model, instances_to_remove):
        metadata_dict = {
            key: val for d in instance_metadata for key, val in d.items()}
        instances = cluster_model.get_all_instances()
        for uuid, instance in instances.items():
            metadata = instance.metadata
            common_metadata = set(metadata_dict) & set(metadata)
            if common_metadata and len(common_metadata) == len(metadata_dict):
                for key, value in metadata_dict.items():
                    if str(value).lower() == str(metadata.get(key)).lower():
                        instances_to_remove.add(uuid)

    def exclude_instances_with_given_project(
            self, projects_to_exclude, cluster_model, instances_to_exclude):
        all_instances = cluster_model.get_all_instances()
        for uuid, instance in all_instances.items():
            if instance.project_id in projects_to_exclude:
                instances_to_exclude.add(uuid)

    def get_scoped_model(self, cluster_model):
        """Leave only nodes and instances proposed in the audit scope"""
        if not cluster_model:
            return None

        allowed_nodes = []
        nodes_to_exclude = []
        nodes_to_remove = set()
        instances_to_exclude = []
        instance_metadata = []
        projects_to_exclude = []
        compute_scope = []
        found_nothing_flag = False
        model_hosts = [n.hostname for n in
                       cluster_model.get_all_compute_nodes().values()]

        if not self.scope:
            return cluster_model

        for scope in self.scope:
            compute_scope = scope.get('compute')
            if compute_scope:
                break

        if not compute_scope:
            return cluster_model

        for rule in compute_scope:
            if 'host_aggregates' in rule:
                self._collect_aggregates(rule['host_aggregates'],
                                         allowed_nodes)
                if not allowed_nodes:
                    found_nothing_flag = True
            elif 'availability_zones' in rule:
                self._collect_zones(rule['availability_zones'],
                                    allowed_nodes)
                if not allowed_nodes:
                    found_nothing_flag = True
            elif 'exclude' in rule:
                self.exclude_resources(
                    rule['exclude'], instances=instances_to_exclude,
                    nodes=nodes_to_exclude,
                    instance_metadata=instance_metadata,
                    projects=projects_to_exclude)

        instances_to_exclude = set(instances_to_exclude)
        if allowed_nodes:
            nodes_to_remove = set(model_hosts) - set(allowed_nodes)
        # This branch means user set host_aggregates and/or availability_zones
        # but can't find any nodes, so we should remove all nodes.
        elif found_nothing_flag:
            nodes_to_remove = set(model_hosts)
        nodes_to_remove.update(nodes_to_exclude)

        self.remove_nodes_from_model(nodes_to_remove, cluster_model)

        if instance_metadata and self.config.check_optimize_metadata:
            self.exclude_instances_with_given_metadata(
                instance_metadata, cluster_model, instances_to_exclude)

        if projects_to_exclude:
            self.exclude_instances_with_given_project(
                projects_to_exclude, cluster_model, instances_to_exclude)

        self.update_exclude_instance_in_model(instances_to_exclude,
                                              cluster_model)

        return cluster_model
