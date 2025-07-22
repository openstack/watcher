# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
#

from oslo_config import cfg

aetos_client = cfg.OptGroup(name='aetos_client',
                            title='Configuration Options for Aetos',
                            help="See https://docs.openstack.org/watcher/"
                                 "latest/datasources/aetos.html for "
                                 "details on how these options are used.")

AETOS_CLIENT_OPTS = [
    cfg.StrOpt('interface',
               default='public',
               choices=['internal', 'public', 'admin'],
               help="Type of endpoint to use in keystoneclient."),
    cfg.StrOpt('region_name',
               help="Region in Identity service catalog to use for "
                    "communication with the OpenStack service."),
    cfg.StrOpt('fqdn_label',
               default='fqdn',
               help="The label that Prometheus uses to store the fqdn of "
                    "exporters. Defaults to 'fqdn'."),
    cfg.StrOpt('instance_uuid_label',
               default='resource',
               help="The label that Prometheus uses to store the uuid of "
                    "OpenStack instances. Defaults to 'resource'."),
]


def register_opts(conf):
    conf.register_group(aetos_client)
    conf.register_opts(AETOS_CLIENT_OPTS, group=aetos_client)


def list_opts():
    return [(aetos_client, AETOS_CLIENT_OPTS)]
