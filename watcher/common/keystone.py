# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
#
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

from oslo_config import cfg
from oslo_log import log

from urlparse import urljoin
from urlparse import urlparse

from keystoneclient.auth.identity import generic
from keystoneclient import session as keystone_session

from watcher.common.exception import KeystoneFailure


LOG = log.getLogger(__name__)
CONF = cfg.CONF

CONF.import_opt('admin_user', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('admin_tenant_name', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('admin_password', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('auth_uri', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('auth_version', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')
CONF.import_opt('insecure', 'keystonemiddleware.auth_token',
                group='keystone_authtoken')


class KeystoneClient(object):
    def __init__(self):
        self._ks_client = None
        self._session = None
        self._auth = None
        self._token = None

    def get_endpoint(self, **kwargs):
        kc = self._get_ksclient()
        if not kc.has_service_catalog():
            raise KeystoneFailure('No Keystone service catalog '
                                  'loaded')
        attr = None
        filter_value = None
        if kwargs.get('region_name'):
            attr = 'region'
            filter_value = kwargs.get('region_name')
        return self._get_ksclient().service_catalog.url_for(
            service_type=kwargs.get('service_type') or 'metering',
            attr=attr,
            filter_value=filter_value,
            endpoint_type=kwargs.get('endpoint_type') or 'publicURL')

    def _is_apiv3(self, auth_url, auth_version):
        return auth_version == 'v3.0' or '/v3' in urlparse(auth_url).path

    def get_keystone_url(self, auth_url, auth_version):
        """Gives an http/https url to contact keystone.
        """
        api_v3 = self._is_apiv3(auth_url, auth_version)
        api_version = 'v3' if api_v3 else 'v2.0'
        # NOTE(lucasagomes): Get rid of the trailing '/' otherwise urljoin()
        #   fails to override the version in the URL
        return urljoin(auth_url.rstrip('/'), api_version)

    def _get_ksclient(self):
        """Get an endpoint and auth token from Keystone.
        """
        ks_args = self.get_credentials()
        auth_version = CONF.keystone_authtoken.auth_version
        auth_url = CONF.keystone_authtoken.auth_uri
        api_version = self._is_apiv3(auth_url, auth_version)

        if api_version:
            from keystoneclient.v3 import client
        else:
            from keystoneclient.v2_0 import client
        # generic
        # ksclient = client.Client(version=api_version,
        # session=session,**ks_args)

        return client.Client(**ks_args)

    def get_credentials(self):
        creds = \
            {'auth_url': CONF.keystone_authtoken.auth_uri,
             'username': CONF.keystone_authtoken.admin_user,
             'password': CONF.keystone_authtoken.admin_password,
             'project_name': CONF.keystone_authtoken.admin_tenant_name,
             'user_domain_name': "default",
             'project_domain_name': "default"}
        LOG.debug(creds)
        return creds

    def get_session(self):
        creds = self.get_credentials()
        self._auth = generic.Password(**creds)
        session = keystone_session.Session(auth=self._auth)
        return session
