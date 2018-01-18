# -*- encoding: utf-8 -*-
# Copyright (c) 2017 ZTE Corporation
#
# Authors:Yumeng Bao <bao.yumeng@zte.com.cn>

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
#

from oslo_log import log

from watcher.common import clients
from watcher.common import exception
from watcher.common import utils

LOG = log.getLogger(__name__)


class IronicHelper(object):

    def __init__(self, osc=None):
        """:param osc: an OpenStackClients instance"""
        self.osc = osc if osc else clients.OpenStackClients()
        self.ironic = self.osc.ironic()

    def get_ironic_node_list(self):
        return self.ironic.node.list()

    def get_ironic_node_by_uuid(self, node_uuid):
        """Get ironic node by node UUID"""
        try:
            node = self.ironic.node.get(utils.Struct(uuid=node_uuid))
            if not node:
                raise exception.IronicNodeNotFound(uuid=node_uuid)
        except Exception as exc:
            LOG.exception(exc)
            raise exception.IronicNodeNotFound(uuid=node_uuid)
        # We need to pass an object with an 'uuid' attribute to make it work
        return node
