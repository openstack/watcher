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

from watcher._i18n import _


placement_group = cfg.OptGroup(
    'placement_client',
    title='Placement Service Options',
    help="Configuration options for connecting to the placement API service",
)

placement_opts = [
    cfg.StrOpt(
        'api_version',
        default='1.29',
        deprecated_for_removal=True,
        deprecated_reason=_(
            'To replace the calls to placement api with the '
            'openstacksdk placement proxy, the options need to '
            'be under the [placement] group.'
        ),
        deprecated_since='2026.2',
        help='microversion of placement API when using placement service.',
    ),
    cfg.StrOpt(
        'interface',
        default='public',
        choices=['internal', 'public', 'admin'],
        deprecated_for_removal=True,
        deprecated_reason=_(
            'This option was replaced by the valid_interfaces '
            'option defined by keystoneauth.'
        ),
        deprecated_since='2026.2',
        help='Type of endpoint when using placement service.',
    ),
    cfg.StrOpt(
        'region_name',
        deprecated_for_removal=True,
        deprecated_reason=_(
            'This option was replaced by the region_name '
            'option defined by keystoneauth.'
        ),
        deprecated_since='2026.2',
        help='Region in Identity service catalog to use for '
        'communication with the OpenStack service.',
    ),
]


def register_opts(conf):
    conf.register_group(placement_group)
    conf.register_opts(placement_opts, group=placement_group)


def list_opts():
    return [(placement_group, placement_opts)]
