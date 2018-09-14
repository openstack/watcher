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

from watcher.common import cinder_helper
from watcher.common import exception

from watcher.decision_engine.scope import base


class StorageScope(base.BaseScope):
    """Storage Audit Scope Handler"""

    def __init__(self, scope, config, osc=None):
        super(StorageScope, self).__init__(scope, config)
        self._osc = osc
        self.wrapper = cinder_helper.CinderHelper(osc=self._osc)

    def _collect_vtype(self, volume_types, allowed_nodes):
        service_list = self.wrapper.get_storage_node_list()

        vt_names = [volume_type['name'] for volume_type in volume_types]
        include_all_nodes = False
        if '*' in vt_names:
            if len(vt_names) == 1:
                include_all_nodes = True
            else:
                raise exception.WildcardCharacterIsUsed(
                    resource="volume_types")
        for service in service_list:
            if include_all_nodes:
                allowed_nodes.append(service.host)
                continue
            backend = service.host.split('@')[1]
            v_types = self.wrapper.get_volume_type_by_backendname(
                backend)
            for volume_type in v_types:
                if volume_type in vt_names:
                    # Note(adisky): It can generate duplicate values
                    # but it will later converted to set
                    allowed_nodes.append(service.host)

    def _collect_zones(self, availability_zones, allowed_nodes):
        service_list = self.wrapper.get_storage_node_list()
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
                allowed_nodes.append(service.host)

    def exclude_resources(self, resources, **kwargs):
        pools_to_exclude = kwargs.get('pools')
        volumes_to_exclude = kwargs.get('volumes')
        projects_to_exclude = kwargs.get('projects')

        for resource in resources:
            if 'storage_pools' in resource:
                pools_to_exclude.extend(
                    [storage_pool['name'] for storage_pool
                     in resource['storage_pools']])

            elif 'volumes' in resource:
                volumes_to_exclude.extend(
                    [volume['uuid'] for volume in
                     resource['volumes']])

            elif 'projects' in resource:
                projects_to_exclude.extend(
                    [project['uuid'] for project in
                     resource['projects']])

    def exclude_pools(self, pools_to_exclude, cluster_model):
        for pool_name in pools_to_exclude:
            pool = cluster_model.get_pool_by_pool_name(pool_name)
            volumes = cluster_model.get_pool_volumes(pool)
            for volume in volumes:
                cluster_model.remove_volume(volume)
            cluster_model.remove_pool(pool)

    def exclude_volumes(self, volumes_to_exclude, cluster_model):
        for volume_uuid in volumes_to_exclude:
            volume = cluster_model.get_volume_by_uuid(volume_uuid)
            cluster_model.remove_volume(volume)

    def exclude_projects(self, projects_to_exclude, cluster_model):
        all_volumes = cluster_model.get_all_volumes()
        for volume_uuid in all_volumes:
            volume = all_volumes.get(volume_uuid)
            if volume.project_id in projects_to_exclude:
                cluster_model.remove_volume(volume)

    def remove_nodes_from_model(self, nodes_to_remove, cluster_model):
        for hostname in nodes_to_remove:
            node = cluster_model.get_node_by_name(hostname)
            pools = cluster_model.get_node_pools(node)
            for pool in pools:
                volumes = cluster_model.get_pool_volumes(pool)
                for volume in volumes:
                    cluster_model.remove_volume(volume)
                cluster_model.remove_pool(pool)
            cluster_model.remove_node(node)

    def get_scoped_model(self, cluster_model):
        """Leave only nodes, pools and volumes proposed in the audit scope"""
        if not cluster_model:
            return None

        allowed_nodes = []
        nodes_to_remove = set()
        volumes_to_exclude = []
        projects_to_exclude = []
        pools_to_exclude = []

        model_hosts = list(cluster_model.get_all_storage_nodes().keys())

        storage_scope = []

        for scope in self.scope:
            storage_scope = scope.get('storage')
            if storage_scope:
                break

        if not storage_scope:
            return cluster_model

        for rule in storage_scope:
            if 'volume_types' in rule:
                self._collect_vtype(rule['volume_types'],
                                    allowed_nodes, cluster_model)
            elif 'availability_zones' in rule:
                self._collect_zones(rule['availability_zones'],
                                    allowed_nodes)
            elif 'exclude' in rule:
                self.exclude_resources(
                    rule['exclude'], pools=pools_to_exclude,
                    volumes=volumes_to_exclude,
                    projects=projects_to_exclude)

        if allowed_nodes:
            nodes_to_remove = set(model_hosts) - set(allowed_nodes)

        self.remove_nodes_from_model(nodes_to_remove, cluster_model)
        self.exclude_pools(pools_to_exclude, cluster_model)
        self.exclude_volumes(volumes_to_exclude, cluster_model)
        self.exclude_projects(projects_to_exclude, cluster_model)

        return cluster_model
