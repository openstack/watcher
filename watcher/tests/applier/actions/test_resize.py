# -*- encoding: utf-8 -*-
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from __future__ import unicode_literals
import jsonschema
import mock

from watcher.applier.actions import base as baction
from watcher.applier.actions import resize
from watcher.common import clients
from watcher.common import nova_helper
from watcher.tests import base


class TestResize(base.TestCase):

    INSTANCE_UUID = "94ae2f92-b7fd-4da7-9e97-f13504ae98c4"

    def setUp(self):
        super(TestResize, self).setUp()

        self.r_osc_cls = mock.Mock()
        self.r_helper_cls = mock.Mock()
        self.r_helper = mock.Mock(spec=nova_helper.NovaHelper)
        self.r_helper_cls.return_value = self.r_helper
        self.r_osc = mock.Mock(spec=clients.OpenStackClients)
        self.r_osc_cls.return_value = self.r_osc

        r_openstack_clients = mock.patch.object(
            clients, "OpenStackClients", self.r_osc_cls)
        r_nova_helper = mock.patch.object(
            nova_helper, "NovaHelper", self.r_helper_cls)

        r_openstack_clients.start()
        r_nova_helper.start()

        self.addCleanup(r_openstack_clients.stop)
        self.addCleanup(r_nova_helper.stop)

        self.input_parameters = {
            "flavor": "x1",
            baction.BaseAction.RESOURCE_ID: self.INSTANCE_UUID,
        }
        self.action = resize.Resize(mock.Mock())
        self.action.input_parameters = self.input_parameters

    def test_parameters(self):
        params = {baction.BaseAction.RESOURCE_ID:
                  self.INSTANCE_UUID,
                  self.action.FLAVOR: 'x1'}
        self.action.input_parameters = params
        self.assertTrue(self.action.validate_parameters())

    def test_parameters_exception_empty_fields(self):
        parameters = {baction.BaseAction.RESOURCE_ID:
                      self.INSTANCE_UUID,
                      self.action.FLAVOR: None}
        self.action.input_parameters = parameters
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_exception_flavor(self):
        parameters = {baction.BaseAction.RESOURCE_ID:
                      self.INSTANCE_UUID,
                      self.action.FLAVOR: None}
        self.action.input_parameters = parameters
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_parameters_exception_resource_id(self):
        parameters = {baction.BaseAction.RESOURCE_ID: "EFEF",
                      self.action.FLAVOR: 'x1'}
        self.action.input_parameters = parameters
        self.assertRaises(jsonschema.ValidationError,
                          self.action.validate_parameters)

    def test_execute_resize(self):
        self.r_helper.find_instance.return_value = self.INSTANCE_UUID
        self.action.execute()
        self.r_helper.resize_instance.assert_called_once_with(
            instance_id=self.INSTANCE_UUID, flavor='x1')
