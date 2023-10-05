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

maas_client = cfg.OptGroup(name='maas_client',
                           title='Configuration Options for MaaS')

MAAS_CLIENT_OPTS = [
    cfg.StrOpt('url',
               help='MaaS URL, example: http://1.2.3.4:5240/MAAS'),
    cfg.StrOpt('api_key',
               help='MaaS API authentication key.'),
    cfg.IntOpt('timeout',
               default=60,
               help='MaaS client operation timeout in seconds.')]


def register_opts(conf):
    conf.register_group(maas_client)
    conf.register_opts(MAAS_CLIENT_OPTS, group=maas_client)


def list_opts():
    return [(maas_client, MAAS_CLIENT_OPTS)]
