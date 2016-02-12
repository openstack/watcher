# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

from ceilometerclient import client as ceclient
import ceilometerclient.v2.client as ceclient_v2
from cinderclient import client as ciclient
from cinderclient.v1 import client as ciclient_v1
from glanceclient import client as glclient
from keystoneauth1 import loading as ka_loading
import mock
from neutronclient.neutron import client as netclient
from neutronclient.v2_0 import client as netclient_v2
from novaclient import client as nvclient
from oslo_config import cfg

from watcher.common import clients
from watcher.tests import base


class TestClients(base.BaseTestCase):

    def setUp(self):
        super(TestClients, self).setUp()

        cfg.CONF.import_opt('api_version', 'watcher.common.clients',
                            group='nova_client')
        cfg.CONF.import_opt('api_version', 'watcher.common.clients',
                            group='glance_client')
        cfg.CONF.import_opt('api_version', 'watcher.common.clients',
                            group='cinder_client')
        cfg.CONF.import_opt('api_version', 'watcher.common.clients',
                            group='ceilometer_client')
        cfg.CONF.import_opt('api_version', 'watcher.common.clients',
                            group='neutron_client')

    def test_get_keystone_session(self):
        _AUTH_CONF_GROUP = 'watcher_clients_auth'
        ka_loading.register_auth_conf_options(cfg.CONF, _AUTH_CONF_GROUP)
        ka_loading.register_session_conf_options(cfg.CONF, _AUTH_CONF_GROUP)

        cfg.CONF.set_override('auth_type', 'password',
                              group=_AUTH_CONF_GROUP)

        # If we don't clean up the _AUTH_CONF_GROUP conf options, then other
        # tests that run after this one will fail, complaining about required
        # options that _AUTH_CONF_GROUP wants.
        def cleanup_conf_from_loading():
            # oslo_config doesn't seem to allow unregistering groups through a
            # single method, so we do this instead
            cfg.CONF.reset()
            del cfg.CONF._groups[_AUTH_CONF_GROUP]

        self.addCleanup(cleanup_conf_from_loading)

        osc = clients.OpenStackClients()

        expected = {'username': 'foousername',
                    'password': 'foopassword',
                    'auth_url': 'http://server.ip:35357',
                    'user_domain_id': 'foouserdomainid',
                    'project_domain_id': 'fooprojdomainid'}

        def reset_register_opts_mock(conf_obj, original_method):
            conf_obj.register_opts = original_method

        original_register_opts = cfg.CONF.register_opts
        self.addCleanup(reset_register_opts_mock,
                        cfg.CONF,
                        original_register_opts)

        # Because some of the conf options for auth plugins are not registered
        # until right before they are loaded, and because the method that does
        # the actual loading of the conf option values is an anonymous method
        # (see _getter method of load_from_conf_options in
        # keystoneauth1.loading.conf.py), we need to manually monkey patch
        # the register opts method so that we can override the conf values to
        # our custom values.
        def mock_register_opts(*args, **kwargs):
            ret = original_register_opts(*args, **kwargs)
            if 'group' in kwargs and kwargs['group'] == _AUTH_CONF_GROUP:
                for key, value in expected.items():
                    cfg.CONF.set_override(key, value, group=_AUTH_CONF_GROUP)
            return ret

        cfg.CONF.register_opts = mock_register_opts

        sess = osc.session
        self.assertEqual(expected['auth_url'], sess.auth.auth_url)
        self.assertEqual(expected['username'], sess.auth._username)
        self.assertEqual(expected['password'], sess.auth._password)
        self.assertEqual(expected['user_domain_id'], sess.auth._user_domain_id)
        self.assertEqual(expected['project_domain_id'],
                         sess.auth._project_domain_id)

    @mock.patch.object(nvclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_nova(self, mock_session, mock_call):
        osc = clients.OpenStackClients()
        osc._nova = None
        osc.nova()
        mock_call.assert_called_once_with(cfg.CONF.nova_client.api_version,
                                          session=mock_session)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_nova_diff_vers(self, mock_session):
        cfg.CONF.set_override('api_version', '2.3',
                              group='nova_client')
        osc = clients.OpenStackClients()
        osc._nova = None
        osc.nova()
        self.assertEqual('2.3', osc.nova().api_version.get_string())

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_nova_cached(self, mock_session):
        osc = clients.OpenStackClients()
        osc._nova = None
        nova = osc.nova()
        nova_cached = osc.nova()
        self.assertEqual(nova, nova_cached)

    @mock.patch.object(glclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_glance(self, mock_session, mock_call):
        osc = clients.OpenStackClients()
        osc._glance = None
        osc.glance()
        mock_call.assert_called_once_with(cfg.CONF.glance_client.api_version,
                                          session=mock_session)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_glance_diff_vers(self, mock_session):
        cfg.CONF.set_override('api_version', '1',
                              group='glance_client')
        osc = clients.OpenStackClients()
        osc._glance = None
        osc.glance()
        self.assertEqual(1.0, osc.glance().version)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_glance_cached(self, mock_session):
        osc = clients.OpenStackClients()
        osc._glance = None
        glance = osc.glance()
        glance_cached = osc.glance()
        self.assertEqual(glance, glance_cached)

    @mock.patch.object(ciclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_cinder(self, mock_session, mock_call):
        osc = clients.OpenStackClients()
        osc._cinder = None
        osc.cinder()
        mock_call.assert_called_once_with(cfg.CONF.cinder_client.api_version,
                                          session=mock_session)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_cinder_diff_vers(self, mock_session):
        cfg.CONF.set_override('api_version', '1',
                              group='cinder_client')
        osc = clients.OpenStackClients()
        osc._cinder = None
        osc.cinder()
        self.assertEqual(ciclient_v1.Client, type(osc.cinder()))

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_cinder_cached(self, mock_session):
        osc = clients.OpenStackClients()
        osc._cinder = None
        cinder = osc.cinder()
        cinder_cached = osc.cinder()
        self.assertEqual(cinder, cinder_cached)

    @mock.patch.object(ceclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_ceilometer(self, mock_session, mock_call):
        osc = clients.OpenStackClients()
        osc._ceilometer = None
        osc.ceilometer()
        mock_call.assert_called_once_with(
            cfg.CONF.ceilometer_client.api_version,
            None,
            session=mock_session)

    @mock.patch.object(clients.OpenStackClients, 'session')
    @mock.patch.object(ceclient_v2.Client, '_get_alarm_client')
    def test_clients_ceilometer_diff_vers(self, mock_get_alarm_client,
                                          mock_session):
        '''ceilometerclient currently only has one version (v2)'''
        mock_get_alarm_client.return_value = [mock.Mock(), mock.Mock()]
        cfg.CONF.set_override('api_version', '2',
                              group='ceilometer_client')
        osc = clients.OpenStackClients()
        osc._ceilometer = None
        osc.ceilometer()
        self.assertEqual(ceclient_v2.Client,
                         type(osc.ceilometer()))

    @mock.patch.object(clients.OpenStackClients, 'session')
    @mock.patch.object(ceclient_v2.Client, '_get_alarm_client')
    def test_clients_ceilometer_cached(self, mock_get_alarm_client,
                                       mock_session):
        mock_get_alarm_client.return_value = [mock.Mock(), mock.Mock()]
        osc = clients.OpenStackClients()
        osc._ceilometer = None
        ceilometer = osc.ceilometer()
        ceilometer_cached = osc.ceilometer()
        self.assertEqual(ceilometer, ceilometer_cached)

    @mock.patch.object(netclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_neutron(self, mock_session, mock_call):
        osc = clients.OpenStackClients()
        osc._neutron = None
        osc.neutron()
        mock_call.assert_called_once_with(cfg.CONF.neutron_client.api_version,
                                          session=mock_session)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_neutron_diff_vers(self, mock_session):
        '''neutronclient currently only has one version (v2)'''
        cfg.CONF.set_override('api_version', '2.0',
                              group='neutron_client')
        osc = clients.OpenStackClients()
        osc._neutron = None
        osc.neutron()
        self.assertEqual(netclient_v2.Client,
                         type(osc.neutron()))

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_neutron_cached(self, mock_session):
        osc = clients.OpenStackClients()
        osc._neutron = None
        neutron = osc.neutron()
        neutron_cached = osc.neutron()
        self.assertEqual(neutron, neutron_cached)
