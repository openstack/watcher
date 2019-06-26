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

monasca_client = cfg.OptGroup(name='monasca_client',
                              title='Configuration Options for Monasca')

MONASCA_CLIENT_OPTS = [
    cfg.StrOpt('api_version',
               default='2_0',
               help='Version of Monasca API to use in monascaclient.'),
    cfg.StrOpt('interface',
               default='internal',
               help='Type of interface used for monasca endpoint. '
                    'Supported values: internal, public, admin. '
                    'The default is internal.'),
    cfg.StrOpt('region_name',
               help='Region in Identity service catalog to use for '
                    'communication with the OpenStack service.')]


def register_opts(conf):
    conf.register_group(monasca_client)
    conf.register_opts(MONASCA_CLIENT_OPTS, group=monasca_client)


def list_opts():
    return [(monasca_client, MONASCA_CLIENT_OPTS)]
