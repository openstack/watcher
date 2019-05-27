# Copyright (c) 2018 NEC, Corp.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

from oslo_upgradecheck.upgradecheck import Code

from watcher.cmd import status
from watcher import conf
from watcher.tests import base

CONF = conf.CONF


class TestUpgradeChecks(base.TestCase):

    def setUp(self):
        super(TestUpgradeChecks, self).setUp()
        self.cmd = status.Checks()

    def test_minimum_nova_api_version_ok(self):
        # Tests that the default [nova_client]/api_version meets the minimum
        # required version.
        result = self.cmd._minimum_nova_api_version()
        self.assertEqual(Code.SUCCESS, result.code)

    def test_minimum_nova_api_version_fail(self):
        # Tests the scenario that [nova_client]/api_version is less than the
        # minimum required version.
        CONF.set_override('api_version', '2.47', group='nova_client')
        result = self.cmd._minimum_nova_api_version()
        self.assertEqual(Code.FAILURE, result.code)
        self.assertIn('Invalid nova_client.api_version 2.47.', result.details)
