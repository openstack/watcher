# -*- encoding: utf-8 -*-
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

from watcher.common import clients

nova_client = cfg.OptGroup(name='nova_client',
                           title='Configuration Options for Nova')

NOVA_CLIENT_OPTS = [
    cfg.StrOpt('api_version',
               default='2.56',
               help="""
Version of Nova API to use in novaclient.

Minimum required version: %s

Certain Watcher features depend on a minimum version of the compute
API being available which is enforced with this option. See
https://docs.openstack.org/nova/latest/reference/api-microversion-history.html
for the compute API microversion history.
""" % clients.MIN_NOVA_API_VERSION),
    cfg.StrOpt('endpoint_type',
               default='publicURL',
               help='Type of endpoint to use in novaclient. '
                    'Supported values: internalURL, publicURL, adminURL. '
                    'The default is publicURL.'),
    cfg.StrOpt('region_name',
               help='Region in Identity service catalog to use for '
                    'communication with the OpenStack service.')]


def register_opts(conf):
    conf.register_group(nova_client)
    conf.register_opts(NOVA_CLIENT_OPTS, group=nova_client)


def list_opts():
    return [(nova_client, NOVA_CLIENT_OPTS)]
