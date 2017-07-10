# -*- encoding: utf-8 -*-
# Copyright (c) 2017 ZTE Corporation
#
# Authors:Yumeng Bao <bao.yumeng@zte.com.cn>
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

from watcher.common import ironic_helper
from watcher.decision_engine.model.collector import base
from watcher.decision_engine.model import element
from watcher.decision_engine.model import model_root

LOG = log.getLogger(__name__)


class BaremetalClusterDataModelCollector(base.BaseClusterDataModelCollector):
    """Baremetal cluster data model collector

    The Baremetal cluster data model collector creates an in-memory
    representation of the resources exposed by the baremetal service.
    """

    def __init__(self, config, osc=None):
        super(BaremetalClusterDataModelCollector, self).__init__(config, osc)

    @property
    def notification_endpoints(self):
        """Associated notification endpoints

        :return: Associated notification endpoints
        :rtype: List of :py:class:`~.EventsNotificationEndpoint` instances
        """
        return None

    def get_audit_scope_handler(self, audit_scope):
        return None

    def execute(self):
        """Build the baremetal cluster data model"""
        LOG.debug("Building latest Baremetal cluster data model")

        builder = ModelBuilder(self.osc)
        return builder.execute()


class ModelBuilder(object):
    """Build the graph-based model

    This model builder adds the following data"

    - Baremetal-related knowledge (Ironic)
    """
    def __init__(self, osc):
        self.osc = osc
        self.model = model_root.BaremetalModelRoot()
        self.ironic_helper = ironic_helper.IronicHelper(osc=self.osc)

    def add_ironic_node(self, node):
        # Build and add base node.
        ironic_node = self.build_ironic_node(node)
        self.model.add_node(ironic_node)

    def build_ironic_node(self, node):
        """Build a Baremetal node from a Ironic node

        :param node: A ironic node
        :type node: :py:class:`~ironicclient.v1.node.Node`
        """
        # build up the ironic node.
        node_attributes = {
            "uuid": node.uuid,
            "power_state": node.power_state,
            "maintenance": node.maintenance,
            "maintenance_reason": node.maintenance_reason,
            "extra": {"compute_node_id": node.extra.compute_node_id}
            }

        ironic_node = element.IronicNode(**node_attributes)
        return ironic_node

    def execute(self):

        for node in self.ironic_helper.get_ironic_node_list():
            self.add_ironic_node(node)
        return self.model
