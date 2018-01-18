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

import mock

from watcher.common import clients
from watcher.common import exception
from watcher.common import ironic_helper
from watcher.common import utils as w_utils
from watcher.tests import base


class TestIronicHelper(base.TestCase):

    def setUp(self):
        super(TestIronicHelper, self).setUp()

        osc = clients.OpenStackClients()
        p_ironic = mock.patch.object(osc, 'ironic')
        p_ironic.start()
        self.addCleanup(p_ironic.stop)
        self.ironic_util = ironic_helper.IronicHelper(osc=osc)

    @staticmethod
    def fake_ironic_node():
        node = mock.MagicMock()
        node.uuid = w_utils.generate_uuid()
        return node

    def test_get_ironic_node_list(self):
        node1 = self.fake_ironic_node()
        self.ironic_util.ironic.node.list.return_value = [node1]
        rt_nodes = self.ironic_util.get_ironic_node_list()
        self.assertEqual(rt_nodes, [node1])

    def test_get_ironic_node_by_uuid_success(self):
        node1 = self.fake_ironic_node()
        self.ironic_util.ironic.node.get.return_value = node1
        node = self.ironic_util.get_ironic_node_by_uuid(node1.uuid)
        self.assertEqual(node, node1)

    def test_get_ironic_node_by_uuid_failure(self):
        self.ironic_util.ironic.node.get.return_value = None
        self.assertRaisesRegex(
            exception.IronicNodeNotFound,
            "The ironic node node1 could not be found",
            self.ironic_util.get_ironic_node_by_uuid, 'node1')
