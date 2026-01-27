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

import debtcollector
import microversion_parse
from oslo_config import cfg
import warnings

from cinderclient import client as ciclient
from gnocchiclient import client as gnclient
from ironicclient import client as irclient
from keystoneauth1 import adapter as ka_adapter
from keystoneauth1 import loading as ka_loading
from keystoneauth1 import session as ka_session
from keystoneclient import client as keyclient
from openstack import connection

from watcher.common import context
from watcher.common import exception
from watcher.common import utils

try:
    from maas import client as maas_client
except ImportError:
    maas_client = None


CONF = cfg.CONF

_CLIENTS_AUTH_GROUP = 'watcher_clients_auth'

# NOTE(mriedem): This is the minimum required version of the nova API for
# watcher features to work. If new features are added which require new
# versions, they should perform version discovery and be backward compatible
# for at least one release before raising the minimum required version.
MIN_NOVA_API_VERSION = '2.56'

warnings.simplefilter("once")


def get_sdk_connection(
        conf_group: str, session: ka_session.Session | None = None,
        context: context.RequestContext | None = None,
        interface: str | None = None, region_name: str | None = None
        ) -> connection.Connection:
    """Create and return an OpenStackSDK Connection object.

    :param conf_group: String name of the conf group to get connection
    information from.
    :param session: Optional keystone session. If not provided, a new session
                    will be created using the configured auth parameters.
    :param context: Optional context object, use to get user's token.
    :param interface: Interface to use when connecting to services.
    :param region_name: Region name to use when connecting to services.
    :returns: An OpenStackSDK Connection object
    """

    # NOTE(jgilaber): load the auth plugin from the config in case it's never
    # been loaded before. The auth plugin is only used when creating a new
    # session, but we need to ensure the auth_url config value is set to use
    # the user token from the context object
    auth = ka_loading.load_auth_from_conf_options(
        CONF, conf_group
    )
    if context is not None:
        if interface is None:
            if "valid_interfaces" in CONF[conf_group]:
                interface = CONF[conf_group].valid_interfaces[0]
            elif "interface" in CONF[conf_group]:
                interface = CONF[conf_group].interface
        if region_name is None and "region_name" in CONF[conf_group]:
            region_name = CONF[conf_group].region_name

        # create a connection using the user's token if available
        conn = connection.Connection(
            token=context.auth_token,
            auth_type="v3token",
            project_id=context.project_id,
            project_domain_id=context.project_domain_id,
            auth_url=CONF[conf_group].auth_url,
            region_name=region_name,
            interface=interface
        )
        return conn

    if session is None:
        # if we don't have a user token nor a created session, create a new
        # one
        session = ka_loading.load_session_from_conf_options(
            CONF, conf_group, auth=auth
        )

    return connection.Connection(session=session, oslo_conf=CONF)


def check_min_nova_api_version(config_version):
    """Validates the minimum required nova API version.

    :param config_version: The configured [nova_client]/api_version value
    :raises: ValueError if the configured version is less than the required
        minimum
    """
    min_required = microversion_parse.parse_version_string(
        MIN_NOVA_API_VERSION
    )

    if microversion_parse.parse_version_string(config_version) < min_required:
        raise ValueError(f'Invalid nova.api_version {config_version}. '
                         f'{MIN_NOVA_API_VERSION} or greater is required.')


class OpenStackClients:
    """Convenience class to create and cache client instances."""

    def __init__(self):
        self.reset_clients()

    def reset_clients(self):
        self._session = None
        self._keystone = None
        self._gnocchi = None
        self._cinder = None
        self._ironic = None
        self._maas = None
        self._placement = None

    def _get_keystone_session(self):
        auth = ka_loading.load_auth_from_conf_options(CONF,
                                                      _CLIENTS_AUTH_GROUP)
        sess = ka_loading.load_session_from_conf_options(CONF,
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
        return getattr(getattr(CONF, f'{client}_client'), option)

    @exception.wrap_keystone_exception
    def keystone(self):
        if self._keystone:
            return self._keystone
        keystone_interface = self._get_client_option('keystone',
                                                     'interface')
        keystone_region_name = self._get_client_option('keystone',
                                                       'region_name')
        self._keystone = keyclient.Client(
            interface=keystone_interface,
            region_name=keystone_region_name,
            session=self.session)

        return self._keystone

    @exception.wrap_keystone_exception
    def gnocchi(self):
        if self._gnocchi:
            return self._gnocchi

        gnocchiclient_version = self._get_client_option('gnocchi',
                                                        'api_version')
        gnocchiclient_interface = self._get_client_option('gnocchi',
                                                          'endpoint_type')
        gnocchiclient_region_name = self._get_client_option('gnocchi',
                                                            'region_name')
        adapter_options = {
            "interface": gnocchiclient_interface,
            "region_name": gnocchiclient_region_name
        }

        self._gnocchi = gnclient.Client(gnocchiclient_version,
                                        adapter_options=adapter_options,
                                        session=self.session)
        return self._gnocchi

    @exception.wrap_keystone_exception
    def cinder(self):
        if self._cinder:
            return self._cinder

        cinderclient_version = self._get_client_option('cinder', 'api_version')
        cinder_endpoint_type = self._get_client_option('cinder',
                                                       'endpoint_type')
        cinder_region_name = self._get_client_option('cinder', 'region_name')
        self._cinder = ciclient.Client(cinderclient_version,
                                       endpoint_type=cinder_endpoint_type,
                                       region_name=cinder_region_name,
                                       session=self.session)
        return self._cinder

    @exception.wrap_keystone_exception
    def ironic(self):
        if self._ironic:
            return self._ironic

        # NOTE(dviroel): This integration is classified as Experimental due to
        # the lack of documentation and CI testing. It can be marked as
        # supported or deprecated in future releases, based on improvements.
        debtcollector.deprecate(
            ("Ironic is an experimental integration and may be "
             "deprecated in future releases."),
            version="2025.2", category=PendingDeprecationWarning)

        ironicclient_version = self._get_client_option('ironic', 'api_version')
        endpoint_type = self._get_client_option('ironic', 'endpoint_type')
        ironic_region_name = self._get_client_option('ironic', 'region_name')
        self._ironic = irclient.get_client(ironicclient_version,
                                           interface=endpoint_type,
                                           region_name=ironic_region_name,
                                           session=self.session)
        return self._ironic

    def maas(self):
        if self._maas:
            return self._maas

        # NOTE(dviroel): This integration is deprecated due to the lack of
        # maintenance and support. It has eventlet code that is required to be
        # removed/replaced in future releases.
        debtcollector.deprecate(
            ("MAAS integration is deprecated and it will be removed in a "
             "future release."), version="2026.1", category=DeprecationWarning)

        if not maas_client:
            raise exception.UnsupportedError(
                "MAAS client unavailable. Please install python-libmaas.")

        url = self._get_client_option('maas', 'url')
        api_key = self._get_client_option('maas', 'api_key')
        timeout = self._get_client_option('maas', 'timeout')
        self._maas = utils.async_compat_call(
            maas_client.connect,
            url, apikey=api_key,
            timeout=timeout)
        return self._maas

    @exception.wrap_keystone_exception
    def placement(self):
        if self._placement:
            return self._placement

        placement_version = self._get_client_option('placement',
                                                    'api_version')
        placement_interface = self._get_client_option('placement',
                                                      'interface')
        placement_region_name = self._get_client_option('placement',
                                                        'region_name')
        # Set accept header on every request to ensure we notify placement
        # service of our response body media type preferences.
        headers = {'accept': 'application/json'}
        self._placement = ka_adapter.Adapter(
            session=self.session,
            service_type='placement',
            default_microversion=placement_version,
            interface=placement_interface,
            region_name=placement_region_name,
            additional_headers=headers)

        return self._placement
