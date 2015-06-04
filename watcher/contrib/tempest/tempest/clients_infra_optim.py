# Copyright 2014 Mirantis Inc.
# All Rights Reserved.
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

from tempest import clients
from tempest.common import cred_provider
from tempest import config
from tempest.services.infra_optim.v1.json import infra_optim_client as ioc

CONF = config.CONF


class Manager(clients.Manager):
    def __init__(self, credentials=None, service=None):
        super(Manager, self).__init__(credentials, service)
        self.io_client = ioc.InfraOptimClientJSON(self.auth_provider,
                                                  'infra-optim',
                                                  CONF.identity.region)


class AltManager(Manager):
    def __init__(self, service=None):
        super(AltManager, self).__init__(
            cred_provider.get_configured_credentials('alt_user'), service)


class AdminManager(Manager):
    def __init__(self, service=None):
        super(AdminManager, self).__init__(
            cred_provider.get_configured_credentials('identity_admin'),
            service)
