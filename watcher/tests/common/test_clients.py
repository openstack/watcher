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
from cinderclient.v3 import client as ciclient_v3
from glanceclient import client as glclient
from gnocchiclient import client as gnclient
from gnocchiclient.v1 import client as gnclient_v1
from ironicclient import client as irclient
from ironicclient.v1 import client as irclient_v1
from keystoneauth1 import adapter as ka_adapter
from keystoneauth1 import loading as ka_loading
import mock
from monascaclient import client as monclient
from monascaclient.v2_0 import client as monclient_v2
from neutronclient.neutron import client as netclient
from neutronclient.v2_0 import client as netclient_v2
from novaclient import client as nvclient
import six

from watcher.common import clients
from watcher import conf
from watcher.tests import base

CONF = conf.CONF


class TestClients(base.TestCase):

    def _register_watcher_clients_auth_opts(self):
        _AUTH_CONF_GROUP = 'watcher_clients_auth'
        ka_loading.register_auth_conf_options(CONF, _AUTH_CONF_GROUP)
        ka_loading.register_session_conf_options(CONF, _AUTH_CONF_GROUP)
        CONF.set_override('auth_type', 'password', group=_AUTH_CONF_GROUP)

        # ka_loading.load_auth_from_conf_options(CONF, _AUTH_CONF_GROUP)
        # ka_loading.load_session_from_conf_options(CONF, _AUTH_CONF_GROUP)
        # CONF.set_override(
        #     'auth-url', 'http://server.ip:5000', group=_AUTH_CONF_GROUP)

        # If we don't clean up the _AUTH_CONF_GROUP conf options, then other
        # tests that run after this one will fail, complaining about required
        # options that _AUTH_CONF_GROUP wants.
        def cleanup_conf_from_loading():
            # oslo_config doesn't seem to allow unregistering groups through a
            # single method, so we do this instead
            CONF.reset()
            del CONF._groups[_AUTH_CONF_GROUP]

        self.addCleanup(cleanup_conf_from_loading)

        def reset_register_opts_mock(conf_obj, original_method):
            conf_obj.register_opts = original_method

        original_register_opts = CONF.register_opts
        self.addCleanup(reset_register_opts_mock,
                        CONF,
                        original_register_opts)

        expected = {'username': 'foousername',
                    'password': 'foopassword',
                    'auth_url': 'http://server.ip:5000',
                    'cafile': None,
                    'certfile': None,
                    'keyfile': None,
                    'insecure': False,
                    'user_domain_id': 'foouserdomainid',
                    'project_domain_id': 'fooprojdomainid'}

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
                    CONF.set_override(key, value, group=_AUTH_CONF_GROUP)
            return ret

        CONF.register_opts = mock_register_opts

    def test_get_keystone_session(self):
        self._register_watcher_clients_auth_opts()

        osc = clients.OpenStackClients()

        expected = {'username': 'foousername',
                    'password': 'foopassword',
                    'auth_url': 'http://server.ip:5000',
                    'user_domain_id': 'foouserdomainid',
                    'project_domain_id': 'fooprojdomainid'}

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
        mock_call.assert_called_once_with(
            CONF.nova_client.api_version,
            endpoint_type=CONF.nova_client.endpoint_type,
            region_name=CONF.nova_client.region_name,
            session=mock_session)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_nova_diff_vers(self, mock_session):
        CONF.set_override('api_version', '2.60', group='nova_client')
        osc = clients.OpenStackClients()
        osc._nova = None
        osc.nova()
        self.assertEqual('2.60', osc.nova().api_version.get_string())

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_nova_bad_min_version(self, mock_session):
        CONF.set_override('api_version', '2.47', group='nova_client')
        osc = clients.OpenStackClients()
        osc._nova = None
        ex = self.assertRaises(ValueError, osc.nova)
        self.assertIn('Invalid nova_client.api_version 2.47',
                      six.text_type(ex))

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_nova_diff_endpoint(self, mock_session):
        CONF.set_override('endpoint_type', 'publicURL', group='nova_client')
        osc = clients.OpenStackClients()
        osc._nova = None
        osc.nova()
        self.assertEqual('publicURL', osc.nova().client.interface)

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
        mock_call.assert_called_once_with(
            CONF.glance_client.api_version,
            interface=CONF.glance_client.endpoint_type,
            region_name=CONF.glance_client.region_name,
            session=mock_session)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_glance_diff_vers(self, mock_session):
        CONF.set_override('api_version', '1', group='glance_client')
        osc = clients.OpenStackClients()
        osc._glance = None
        osc.glance()
        self.assertEqual(1.0, osc.glance().version)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_glance_diff_endpoint(self, mock_session):
        CONF.set_override('endpoint_type',
                          'internalURL', group='glance_client')
        osc = clients.OpenStackClients()
        osc._glance = None
        osc.glance()
        self.assertEqual('internalURL', osc.glance().http_client.interface)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_glance_cached(self, mock_session):
        osc = clients.OpenStackClients()
        osc._glance = None
        glance = osc.glance()
        glance_cached = osc.glance()
        self.assertEqual(glance, glance_cached)

    @mock.patch.object(gnclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_gnocchi(self, mock_session, mock_call):
        osc = clients.OpenStackClients()
        osc._gnocchi = None
        osc.gnocchi()
        mock_call.assert_called_once_with(
            CONF.gnocchi_client.api_version,
            adapter_options={
                "interface": CONF.gnocchi_client.endpoint_type,
                "region_name": CONF.gnocchi_client.region_name},
            session=mock_session)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_gnocchi_diff_vers(self, mock_session):
        # gnocchiclient currently only has one version (v1)
        CONF.set_override('api_version', '1', group='gnocchi_client')
        osc = clients.OpenStackClients()
        osc._gnocchi = None
        osc.gnocchi()
        self.assertEqual(gnclient_v1.Client, type(osc.gnocchi()))

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_gnocchi_diff_endpoint(self, mock_session):
        # gnocchiclient currently only has one version (v1)
        CONF.set_override('endpoint_type', 'publicURL', group='gnocchi_client')
        osc = clients.OpenStackClients()
        osc._gnocchi = None
        osc.gnocchi()
        self.assertEqual('publicURL', osc.gnocchi().api.interface)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_gnocchi_cached(self, mock_session):
        osc = clients.OpenStackClients()
        osc._gnocchi = None
        gnocchi = osc.gnocchi()
        gnocchi_cached = osc.gnocchi()
        self.assertEqual(gnocchi, gnocchi_cached)

    @mock.patch.object(ciclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_cinder(self, mock_session, mock_call):
        osc = clients.OpenStackClients()
        osc._cinder = None
        osc.cinder()
        mock_call.assert_called_once_with(
            CONF.cinder_client.api_version,
            endpoint_type=CONF.cinder_client.endpoint_type,
            region_name=CONF.cinder_client.region_name,
            session=mock_session)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_cinder_diff_vers(self, mock_session):
        CONF.set_override('api_version', '3', group='cinder_client')
        osc = clients.OpenStackClients()
        osc._cinder = None
        osc.cinder()
        self.assertEqual(ciclient_v3.Client, type(osc.cinder()))

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_cinder_diff_endpoint(self, mock_session):
        CONF.set_override('endpoint_type',
                          'internalURL', group='cinder_client')
        osc = clients.OpenStackClients()
        osc._cinder = None
        osc.cinder()
        self.assertEqual('internalURL', osc.cinder().client.interface)

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
            CONF.ceilometer_client.api_version,
            None,
            endpoint_type=CONF.ceilometer_client.endpoint_type,
            region_name=CONF.ceilometer_client.region_name,
            session=mock_session)

    @mock.patch.object(clients.OpenStackClients, 'session')
    @mock.patch.object(ceclient_v2.Client, '_get_redirect_client')
    def test_clients_ceilometer_diff_vers(self, mock_get_redirect_client,
                                          mock_session):
        '''ceilometerclient currently only has one version (v2)'''
        mock_get_redirect_client.return_value = [mock.Mock(), mock.Mock()]
        CONF.set_override('api_version', '2',
                          group='ceilometer_client')
        osc = clients.OpenStackClients()
        osc._ceilometer = None
        osc.ceilometer()
        self.assertEqual(ceclient_v2.Client,
                         type(osc.ceilometer()))

    @mock.patch.object(clients.OpenStackClients, 'session')
    @mock.patch.object(ceclient_v2.Client, '_get_redirect_client')
    def test_clients_ceilometer_diff_endpoint(self, mock_get_redirect_client,
                                              mock_session):
        mock_get_redirect_client.return_value = [mock.Mock(), mock.Mock()]
        CONF.set_override('endpoint_type', 'publicURL',
                          group='ceilometer_client')
        osc = clients.OpenStackClients()
        osc._ceilometer = None
        osc.ceilometer()
        self.assertEqual('publicURL', osc.ceilometer().http_client.interface)

    @mock.patch.object(clients.OpenStackClients, 'session')
    @mock.patch.object(ceclient_v2.Client, '_get_redirect_client')
    def test_clients_ceilometer_cached(self, mock_get_redirect_client,
                                       mock_session):
        mock_get_redirect_client.return_value = [mock.Mock(), mock.Mock()]
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
        mock_call.assert_called_once_with(
            CONF.neutron_client.api_version,
            endpoint_type=CONF.neutron_client.endpoint_type,
            region_name=CONF.neutron_client.region_name,
            session=mock_session)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_neutron_diff_vers(self, mock_session):
        '''neutronclient currently only has one version (v2)'''
        CONF.set_override('api_version', '2.0',
                          group='neutron_client')
        osc = clients.OpenStackClients()
        osc._neutron = None
        osc.neutron()
        self.assertEqual(netclient_v2.Client,
                         type(osc.neutron()))

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_neutron_diff_endpoint(self, mock_session):
        '''neutronclient currently only has one version (v2)'''
        CONF.set_override('endpoint_type', 'internalURL',
                          group='neutron_client')
        osc = clients.OpenStackClients()
        osc._neutron = None
        osc.neutron()
        self.assertEqual('internalURL', osc.neutron().httpclient.interface)

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_neutron_cached(self, mock_session):
        osc = clients.OpenStackClients()
        osc._neutron = None
        neutron = osc.neutron()
        neutron_cached = osc.neutron()
        self.assertEqual(neutron, neutron_cached)

    @mock.patch.object(monclient, 'Client')
    @mock.patch.object(ka_loading, 'load_session_from_conf_options')
    def test_clients_monasca(self, mock_session, mock_call):
        mock_session.return_value = mock.Mock(
            get_endpoint=mock.Mock(return_value='test_endpoint'),
            get_token=mock.Mock(return_value='test_token'),)

        self._register_watcher_clients_auth_opts()

        osc = clients.OpenStackClients()
        osc._monasca = None
        osc.monasca()
        mock_call.assert_called_once_with(
            CONF.monasca_client.api_version,
            'test_endpoint',
            auth_url='http://server.ip:5000', cert_file=None, insecure=False,
            key_file=None, keystone_timeout=None, os_cacert=None,
            password='foopassword', service_type='monitoring',
            token='test_token', username='foousername')

    @mock.patch.object(ka_loading, 'load_session_from_conf_options')
    def test_clients_monasca_diff_vers(self, mock_session):
        mock_session.return_value = mock.Mock(
            get_endpoint=mock.Mock(return_value='test_endpoint'),
            get_token=mock.Mock(return_value='test_token'),)

        self._register_watcher_clients_auth_opts()

        CONF.set_override('api_version', '2_0', group='monasca_client')
        osc = clients.OpenStackClients()
        osc._monasca = None
        osc.monasca()
        self.assertEqual(monclient_v2.Client, type(osc.monasca()))

    @mock.patch.object(ka_loading, 'load_session_from_conf_options')
    def test_clients_monasca_cached(self, mock_session):
        mock_session.return_value = mock.Mock(
            get_endpoint=mock.Mock(return_value='test_endpoint'),
            get_token=mock.Mock(return_value='test_token'),)

        self._register_watcher_clients_auth_opts()

        osc = clients.OpenStackClients()
        osc._monasca = None
        monasca = osc.monasca()
        monasca_cached = osc.monasca()
        self.assertEqual(monasca, monasca_cached)

    @mock.patch.object(irclient, 'Client')
    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_ironic(self, mock_session, mock_call):
        ironic_url = 'http://localhost:6385/'
        mock_session.get_endpoint.return_value = ironic_url
        osc = clients.OpenStackClients()
        osc._ironic = None
        osc.ironic()
        mock_call.assert_called()

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_ironic_diff_vers(self, mock_session):
        ironic_url = 'http://localhost:6385/'
        mock_session.get_endpoint.return_value = ironic_url
        CONF.set_override('api_version', '1', group='ironic_client')
        osc = clients.OpenStackClients()
        osc._ironic = None
        osc.ironic()
        self.assertEqual(irclient_v1.Client, type(osc.ironic()))

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_ironic_diff_endpoint(self, mock_session):
        ironic_url = 'http://localhost:6385/'
        mock_session.get_endpoint.return_value = ironic_url
        osc = clients.OpenStackClients()
        osc._ironic = None
        osc.ironic()
        mock_session.get_endpoint.assert_called_with(
            interface='publicURL',
            region_name=None,
            service_type='baremetal')

        CONF.set_override('endpoint_type', 'internalURL',
                          group='ironic_client')
        osc._ironic = None
        osc.ironic()
        mock_session.get_endpoint.assert_called_with(
            interface='internalURL',
            region_name=None,
            service_type='baremetal')

    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_ironic_cached(self, mock_session):
        ironic_url = 'http://localhost:6385/'
        mock_session.get_endpoint.return_value = ironic_url
        osc = clients.OpenStackClients()
        osc._ironic = None
        ironic = osc.ironic()
        ironic_cached = osc.ironic()
        self.assertEqual(ironic, ironic_cached)

    @mock.patch.object(ka_adapter, 'Adapter')
    @mock.patch.object(clients.OpenStackClients, 'session')
    def test_clients_placement(self, mock_session, mock_call):
        osc = clients.OpenStackClients()
        osc.placement()
        headers = {'accept': 'application/json'}
        mock_call.assert_called_once_with(
            session=mock_session,
            service_type='placement',
            default_microversion=CONF.placement_client.api_version,
            interface=CONF.placement_client.interface,
            region_name=CONF.placement_client.region_name,
            additional_headers=headers)
