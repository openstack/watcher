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

from unittest import mock

from keystoneauth1 import loading as ks_loading

from watcher.common import base_helper
from watcher.common import clients
from watcher.conf import clients_auth
from watcher.tests.unit import base


class FakeHelper(base_helper.BaseConnectionMixin):
    pass


class TestBaseConnectionMixin(base.TestCase):
    @mock.patch.object(clients, 'get_sdk_connection', autospec=True)
    @mock.patch.object(
        ks_loading, 'load_auth_from_conf_options', autospec=True
    )
    def test_create_sdk_connection(self, m_load_auth, m_get_conn):
        """Test connection is created using the service config group."""
        m_load_auth.return_value = mock.sentinel.auth
        helper = FakeHelper()
        helper._create_sdk_connection('keystone')

        m_load_auth.assert_called_once_with(base_helper.CONF, 'keystone')
        m_get_conn.assert_called_once_with(
            'keystone',
            context=None,
            session=None,
            interface=base_helper.CONF.keystone.valid_interfaces,
            region_name=base_helper.CONF.keystone.region_name,
        )
        self.assertEqual(m_get_conn.return_value, helper.connection)

    @mock.patch.object(clients, 'get_sdk_connection', autospec=True)
    @mock.patch.object(
        ks_loading, 'load_auth_from_conf_options', autospec=True
    )
    def test_create_sdk_connection_with_session(self, m_load_auth, m_get_conn):
        """Test session is forwarded to get_sdk_connection."""
        m_load_auth.return_value = mock.sentinel.auth
        session = mock.sentinel.session
        helper = FakeHelper()
        helper._create_sdk_connection('keystone', session=session)

        m_get_conn.assert_called_once_with(
            'keystone',
            context=None,
            session=session,
            interface=base_helper.CONF.keystone.valid_interfaces,
            region_name=base_helper.CONF.keystone.region_name,
        )

    @mock.patch.object(clients, 'get_sdk_connection', autospec=True)
    @mock.patch.object(
        ks_loading, 'load_auth_from_conf_options', autospec=True
    )
    def test_create_sdk_connection_with_context(self, m_load_auth, m_get_conn):
        """Test context is forwarded to get_sdk_connection."""
        m_load_auth.return_value = mock.sentinel.auth
        context = mock.sentinel.context
        helper = FakeHelper()
        helper._create_sdk_connection('keystone', context=context)

        m_get_conn.assert_called_once_with(
            'keystone',
            context=context,
            session=None,
            interface=base_helper.CONF.keystone.valid_interfaces,
            region_name=base_helper.CONF.keystone.region_name,
        )

    @mock.patch.object(clients, 'get_sdk_connection', autospec=True)
    @mock.patch.object(
        ks_loading, 'load_auth_from_conf_options', autospec=True
    )
    def test_create_sdk_connection_fallback(self, m_load_auth, m_get_conn):
        """Test fallback to watcher_clients_auth when auth is None."""
        m_load_auth.return_value = None
        helper = FakeHelper()
        helper._create_sdk_connection('keystone')

        m_get_conn.assert_called_once_with(
            clients_auth.WATCHER_CLIENTS_AUTH,
            context=None,
            session=None,
            interface=base_helper.CONF.keystone.valid_interfaces,
            region_name=base_helper.CONF.keystone.region_name,
        )
