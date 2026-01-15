# Copyright (c) 2016 Intel Corp
#
# Authors: Prudhvi Rao Shedimbi <prudhvi.rao.shedimbi@intel.com>
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

from oslo_config import cfg

from watcher._i18n import _
from watcher.common import clients

nova_client = cfg.OptGroup(name='nova_client',
                           title='Configuration Options for Nova')

NOVA_CLIENT_OPTS = [
    cfg.StrOpt('api_version',
               default='2.56',
               deprecated_for_removal=True,
               deprecated_reason=_(
                   'To replace the frozen novaclient with the '
                   'openstacksdk compute proxy, the options need to '
                   'be under the [nova] group.'
               ),
               deprecated_since='2026.1',
               help=f"""
Version of Nova API to use in novaclient.

Minimum required version: {clients.MIN_NOVA_API_VERSION}

Certain Watcher features depend on a minimum version of the compute
API being available which is enforced with this option. See
https://docs.openstack.org/nova/latest/reference/api-microversion-history.html
for the compute API microversion history.
"""),
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               deprecated_for_removal=True,
               deprecated_reason=_(
                   'This option was replaced by the valid_interfaces '
                   'option defined by keystoneauth.'
               ),
               deprecated_since='2026.1',
               choices=['public', 'internal', 'admin',
                        'publicURL', 'internalURL', 'adminURL'],
               help='Type of endpoint to use in novaclient.'),
    cfg.StrOpt('region_name',
               deprecated_for_removal=True,
               deprecated_reason=_(
                   'This option was replaced by the region_name '
                   'option defined by keystoneauth.'
               ),
               deprecated_since='2026.1',
               help='Region in Identity service catalog to use for '
                    'communication with the OpenStack service.')]


def register_opts(conf):
    conf.register_group(nova_client)
    conf.register_opts(NOVA_CLIENT_OPTS, group=nova_client)


def list_opts():
    return [(nova_client, NOVA_CLIENT_OPTS)]
