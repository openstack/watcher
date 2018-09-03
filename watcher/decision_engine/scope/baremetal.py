# -*- encoding: utf-8 -*-
# Copyright (c) 2018 ZTE Corporation
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

from watcher.decision_engine.scope import base


class BaremetalScope(base.BaseScope):
    """Baremetal Audit Scope Handler"""

    def __init__(self, scope, config, osc=None):
        super(BaremetalScope, self).__init__(scope, config)
        self._osc = osc

    def exclude_resources(self, resources, **kwargs):
        nodes_to_exclude = kwargs.get('nodes')
        for resource in resources:
            if 'ironic_nodes' in resource:
                nodes_to_exclude.extend(
                    [node['uuid'] for node
                     in resource['ironic_nodes']])

    def remove_nodes_from_model(self, nodes_to_exclude, cluster_model):
        for node_uuid in nodes_to_exclude:
            node = cluster_model.get_node_by_uuid(node_uuid)
            cluster_model.remove_node(node)

    def get_scoped_model(self, cluster_model):
        """Leave only nodes and instances proposed in the audit scope"""
        if not cluster_model:
            return None

        nodes_to_exclude = []
        baremetal_scope = []

        if not self.scope:
            return cluster_model

        for scope in self.scope:
            baremetal_scope = scope.get('baremetal')
            if baremetal_scope:
                break

        if not baremetal_scope:
            return cluster_model

        for rule in baremetal_scope:
            if 'exclude' in rule:
                self.exclude_resources(
                    rule['exclude'], nodes=nodes_to_exclude)

        self.remove_nodes_from_model(nodes_to_exclude, cluster_model)

        return cluster_model
