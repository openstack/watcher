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

from watcher.decision_engine.scope import base


LOG = log.getLogger(__name__)


class StorageScope(base.BaseScope):
    """Storage Audit Scope Handler"""

    def __init__(self, scope, config, osc=None):
        super(StorageScope, self).__init__(scope, config)
        self._osc = osc

    def get_scoped_model(self, cluster_model):
        """Leave only nodes and instances proposed in the audit scope"""
        if not cluster_model:
            return None

        for scope in self.scope:
            storage_scope = scope.get('storage')

        if not storage_scope:
            return cluster_model

        # TODO(hidekazu): currently self.scope is always []
        # Audit scoper for storage data model will be implemented:
        # https://blueprints.launchpad.net/watcher/+spec/audit-scoper-for-storage-data-model
        return cluster_model
