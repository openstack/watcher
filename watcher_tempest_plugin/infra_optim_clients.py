# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
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

import abc

import six
from tempest import clients
from tempest.common import credentials_factory as creds_factory
from tempest import config

from watcher_tempest_plugin.services.infra_optim.v1.json import client as ioc

CONF = config.CONF


@six.add_metaclass(abc.ABCMeta)
class BaseManager(clients.Manager):

    def __init__(self, credentials):
        super(BaseManager, self).__init__(credentials)
        self.io_client = ioc.InfraOptimClientJSON(
            self.auth_provider, 'infra-optim', CONF.identity.region)


class AdminManager(BaseManager):
    def __init__(self):
        super(AdminManager, self).__init__(
            creds_factory.get_configured_admin_credentials(),
        )
