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
from cinderclient import client as ciclient
from glanceclient import client as glclient
from keystoneauth1 import loading as ka_loading
from keystoneclient import client as keyclient
from neutronclient.neutron import client as netclient
from novaclient import client as nvclient
from oslo_config import cfg

from watcher._i18n import _
from watcher.common import exception


NOVA_CLIENT_OPTS = [
    cfg.StrOpt('api_version',
               default='2',
               help=_('Version of Nova API to use in novaclient.'))]

GLANCE_CLIENT_OPTS = [
    cfg.StrOpt('api_version',
               default='2',
               help=_('Version of Glance API to use in glanceclient.'))]

CINDER_CLIENT_OPTS = [
    cfg.StrOpt('api_version',
               default='2',
               help=_('Version of Cinder API to use in cinderclient.'))]

CEILOMETER_CLIENT_OPTS = [
    cfg.StrOpt('api_version',
               default='2',
               help=_('Version of Ceilometer API to use in '
                      'ceilometerclient.'))]

NEUTRON_CLIENT_OPTS = [
    cfg.StrOpt('api_version',
               default='2.0',
               help=_('Version of Neutron API to use in neutronclient.'))]

cfg.CONF.register_opts(NOVA_CLIENT_OPTS, group='nova_client')
cfg.CONF.register_opts(GLANCE_CLIENT_OPTS, group='glance_client')
cfg.CONF.register_opts(CINDER_CLIENT_OPTS, group='cinder_client')
cfg.CONF.register_opts(CEILOMETER_CLIENT_OPTS, group='ceilometer_client')
cfg.CONF.register_opts(NEUTRON_CLIENT_OPTS, group='neutron_client')

_CLIENTS_AUTH_GROUP = 'watcher_clients_auth'

ka_loading.register_auth_conf_options(cfg.CONF, _CLIENTS_AUTH_GROUP)
ka_loading.register_session_conf_options(cfg.CONF, _CLIENTS_AUTH_GROUP)


class OpenStackClients(object):
    """Convenience class to create and cache client instances."""

    def __init__(self):
        self.reset_clients()

    def reset_clients(self):
        self._session = None
        self._keystone = None
        self._nova = None
        self._glance = None
        self._cinder = None
        self._ceilometer = None
        self._neutron = None

    def _get_keystone_session(self):
        auth = ka_loading.load_auth_from_conf_options(cfg.CONF,
                                                      _CLIENTS_AUTH_GROUP)
        sess = ka_loading.load_session_from_conf_options(cfg.CONF,
                                                         _CLIENTS_AUTH_GROUP,
                                                         auth=auth)
        return sess

    @property
    def auth_url(self):
        return self.keystone().auth_url

    @property
    def session(self):
        if not self._session:
            self._session = self._get_keystone_session()
        return self._session

    def _get_client_option(self, client, option):
        return getattr(getattr(cfg.CONF, '%s_client' % client), option)

    @exception.wrap_keystone_exception
    def keystone(self):
        if not self._keystone:
            self._keystone = keyclient.Client(session=self.session)

        return self._keystone

    @exception.wrap_keystone_exception
    def nova(self):
        if self._nova:
            return self._nova

        novaclient_version = self._get_client_option('nova', 'api_version')
        self._nova = nvclient.Client(novaclient_version,
                                     session=self.session)
        return self._nova

    @exception.wrap_keystone_exception
    def glance(self):
        if self._glance:
            return self._glance

        glanceclient_version = self._get_client_option('glance', 'api_version')
        self._glance = glclient.Client(glanceclient_version,
                                       session=self.session)
        return self._glance

    @exception.wrap_keystone_exception
    def cinder(self):
        if self._cinder:
            return self._cinder

        cinderclient_version = self._get_client_option('cinder', 'api_version')
        self._cinder = ciclient.Client(cinderclient_version,
                                       session=self.session)
        return self._cinder

    @exception.wrap_keystone_exception
    def ceilometer(self):
        if self._ceilometer:
            return self._ceilometer

        ceilometerclient_version = self._get_client_option('ceilometer',
                                                           'api_version')
        self._ceilometer = ceclient.get_client(ceilometerclient_version,
                                               session=self.session)
        return self._ceilometer

    @exception.wrap_keystone_exception
    def neutron(self):
        if self._neutron:
            return self._neutron

        neutronclient_version = self._get_client_option('neutron',
                                                        'api_version')
        self._neutron = netclient.Client(neutronclient_version,
                                         session=self.session)
        self._neutron.format = 'json'
        return self._neutron
