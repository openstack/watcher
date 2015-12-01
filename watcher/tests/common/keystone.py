# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

from __future__ import absolute_import
from __future__ import unicode_literals
from keystoneclient.auth.identity import Password

from keystoneclient.session import Session
from mock import mock

from watcher.common.keystone import KeystoneClient

from watcher.tests.base import BaseTestCase


class TestKeyStone(BaseTestCase):
    def setUp(self):
        super(TestKeyStone, self).setUp()
        self.ckeystone = KeystoneClient()

    @mock.patch('keystoneclient.client.Client')
    def test_get_endpoint(self, keystone):
        expected_endpoint = "http://IP:PORT"
        ks = mock.Mock()
        ks.service_catalog.url_for.return_value = expected_endpoint
        keystone.return_value = ks
        ep = self.ckeystone.get_endpoint(service_type='metering',
                                         endpoint_type='publicURL',
                                         region_name='RegionOne')

        self.assertEqual(ep, expected_endpoint)

    def test_get_session(self):
        k = KeystoneClient()
        session = k.get_session()
        self.assertIsInstance(session.auth, Password)
        self.assertIsInstance(session, Session)

    def test_get_credentials(self):
        expected_creds = {'auth_url': None,
                          'password': None,
                          'project_domain_name': 'default',
                          'project_name': 'admin',
                          'user_domain_name': 'default',
                          'username': None}
        creds = self.ckeystone.get_credentials()
        self.assertEqual(creds, expected_creds)
