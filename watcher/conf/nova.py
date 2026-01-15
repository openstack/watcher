# Copyright (c) 2025 OpenStack Foundation
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

from keystoneauth1 import loading as ks_loading
from oslo_config import cfg

from watcher.common import clients

nova = cfg.OptGroup(name='nova',
                    title='Options for the Nova integration '
                    'configuration')

NOVA_OPTS = [
    cfg.IntOpt('migration_max_retries',
               default=180,
               min=1,
               help='Maximum number of retries for Nova migrations '
                    'before giving up and considering the operation failed. '
                    'Default value is 180, which for the default '
                    'migration_interval (5 seconds), makes a default '
                    'migration timeout of 900 seconds (15 minutes).'
                    'This is an upper bound on the maximum expected. This '
                    'should not be decreased or increased over 3600s '
                    '(one hour). Shorter values may cause the actions to '
                    'fail and higher values may hide infrastructure issues.'),
    cfg.FloatOpt('migration_interval',
                 default=5.0,
                 min=0.1,
                 help='Interval in seconds to check the status in Nova VM '
                      'migrations (value is float). Default value is 5.0 '
                      'seconds.'),
    cfg.IntOpt('http_retries',
               default=3,
               min=1,
               help='Maximum number of retries for HTTP requests to the Nova '
                    'service when connection errors occur. Default is 3'),
    cfg.FloatOpt('http_retry_interval',
                 default=2.0,
                 min=0.1,
                 help='Interval in seconds to retry HTTP requests to the Nova '
                      'service when connection errors occur. Default is 2 '
                      'seconds.'),
    # Options migrated from nova_client group (deprecated in 2026.1)
    cfg.StrOpt('api_version',
               default='2.56',
               deprecated_group='nova_client',
               help=f"""
Version of Nova API to use in novaclient.

Minimum required version: {clients.MIN_NOVA_API_VERSION}

Certain Watcher features depend on a minimum version of the compute
API being available which is enforced with this option. See
https://docs.openstack.org/nova/latest/reference/api-microversion-history.html
for the compute API microversion history.
"""),
]


def _deprecations():
    # NOTE(jgilaber): match the adapter options that were previously passed
    # through the [nova_client] group, except for endpoint_type which needs to
    # be handled after the configuration is parsed because it might need a
    # string manipulation in case the configuration contains a *URL value (e.g
    # publicURL)
    deprecations = {
        'region_name': [cfg.DeprecatedOpt('region_name', 'nova_client')]
    }
    return deprecations


def register_opts(conf):
    conf.register_group(nova)
    conf.register_opts(NOVA_OPTS, group=nova)
    deprecated_opts = _deprecations()
    ks_loading.register_adapter_conf_options(
        conf, nova.name,
        deprecated_opts=deprecated_opts
    )
    ks_loading.register_session_conf_options(conf, nova.name,)
    ks_loading.register_auth_conf_options(conf, nova.name)


def list_opts():
    deprecated_opts = _deprecations()
    return [(
        nova,
        NOVA_OPTS +
        ks_loading.get_adapter_conf_options(
            include_deprecated=False, deprecated_opts=deprecated_opts
        ) +
        ks_loading.get_session_conf_options() +
        ks_loading.get_auth_common_conf_options()
    )]
