# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

from unittest import mock

import keystoneclient.v3.services as ks_service

from watcher.common import keystone_helper
from watcher.tests.fixtures import watcher as watcher_fixtures
from watcher.tests.unit import base as test


class TestKeystoneHelper(test.TestCase):
    def setUp(self):
        super().setUp()
        self.fake_keystone = self.useFixture(watcher_fixtures.KeystoneClient())
        self.keystone_svs = self.fake_keystone.m_keystone.return_value.services

        self.keystone_helper = keystone_helper.KeystoneHelper()

    def test_is_service_enabled(self):
        self.keystone_svs.list.return_value = [mock.MagicMock(
            spec=ks_service.Service, enabled=True)]
        self.assertTrue(
            self.keystone_helper.is_service_enabled_by_type('block-storage'))
        self.keystone_svs.list.assert_called_once_with(type='block-storage')

    def test_is_service_enabled_not_found(self):
        self.keystone_svs.list.return_value = []
        self.assertFalse(
            self.keystone_helper.is_service_enabled_by_type('block-storage'))
        self.keystone_svs.list.assert_called_once_with(type='block-storage')

    def test_is_service_enabled_with_multiple_services_one_enabled(self):
        self.keystone_svs.list.return_value = [
            mock.MagicMock(spec=ks_service.Service, enabled=True),
            mock.MagicMock(spec=ks_service.Service, enabled=False)]
        self.assertTrue(
            self.keystone_helper.is_service_enabled_by_type('block-storage'))
        self.keystone_svs.list.assert_called_once_with(type='block-storage')

    def test_is_service_enabled_multiple_services_two_enabled(self):
        self.keystone_svs.list.return_value = [
            mock.MagicMock(spec=ks_service.Service, enabled=True),
            mock.MagicMock(spec=ks_service.Service, enabled=True)]
        self.assertFalse(
            self.keystone_helper.is_service_enabled_by_type('block-storage'))
        self.keystone_svs.list.assert_called_once_with(type='block-storage')
