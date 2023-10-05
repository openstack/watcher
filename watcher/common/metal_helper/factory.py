# Copyright 2023 Cloudbase Solutions
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

from oslo_config import cfg

from watcher.common import clients
from watcher.common.metal_helper import ironic
from watcher.common.metal_helper import maas

CONF = cfg.CONF


def get_helper(osc=None):
    # TODO(lpetrut): consider caching this client.
    if not osc:
        osc = clients.OpenStackClients()

    if CONF.maas_client.url:
        return maas.MaasHelper(osc)
    else:
        return ironic.IronicHelper(osc)
