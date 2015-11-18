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
import datetime

from keystoneclient.auth.identity import v3
from keystoneclient import session
import keystoneclient.v3.client as ksclient
from oslo_config import cfg
from oslo_log import log

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


class Client(object):
    def __init__(self):
        ks_args = self.get_credentials()
        self.ks_client = ksclient.Client(**ks_args)

    def get_endpoint(self, **kwargs):
        attr = None
        filter_value = None
        if kwargs.get('region_name'):
            attr = 'region'
            filter_value = kwargs.get('region_name')
        return self.ks_client.service_catalog.url_for(
            service_type=kwargs.get('service_type') or 'metering',
            attr=attr,
            filter_value=filter_value,
            endpoint_type=kwargs.get('endpoint_type') or 'publicURL')

    def get_token(self):
        return self.ks_client.auth_token

    @staticmethod
    def get_credentials():
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
        auth = v3.Password(**creds)
        return session.Session(auth=auth)

    def is_token_expired(self, token):
        expires = datetime.datetime.strptime(token['expires'],
                                             '%Y-%m-%dT%H:%M:%SZ')
        return datetime.datetime.now() >= expires
