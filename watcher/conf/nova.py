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

from oslo_config import cfg

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
]


def register_opts(conf):
    conf.register_group(nova)
    conf.register_opts(NOVA_OPTS, group=nova)


def list_opts():
    return [(nova, NOVA_OPTS)]
