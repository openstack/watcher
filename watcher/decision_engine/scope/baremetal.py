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

from oslo_log import log

from watcher.decision_engine.scope import base


LOG = log.getLogger(__name__)


class BaremetalScope(base.BaseScope):
    """Baremetal Audit Scope Handler"""

    def __init__(self, scope, config, osc=None):
        super(BaremetalScope, self).__init__(scope, config)
        self._osc = osc

    def get_scoped_model(self, cluster_model):
        """Leave only nodes and instances proposed in the audit scope"""
        if not cluster_model:
            return None

        for scope in self.scope:
            baremetal_scope = scope.get('baremetal')

        if not baremetal_scope:
            return cluster_model

        # TODO(yumeng-bao): currently self.scope is always []
        # Audit scoper for baremetal data model will be implemented:
        # https://blueprints.launchpad.net/watcher/+spec/audit-scoper-for-baremetal-data-model
        return cluster_model
