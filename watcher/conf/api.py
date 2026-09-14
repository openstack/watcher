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


api = cfg.OptGroup(name='api', title='Options for the Watcher API service')

AUTH_OPTS = [
    cfg.BoolOpt(
        'enable_authentication',
        default=True,
        help='This option enables or disables user authentication '
        'via keystone. Default value is True.',
    )
]

API_SERVICE_OPTS = [
    cfg.IntOpt(
        'max_limit',
        default=1000,
        help='The maximum number of items returned in a single '
        'response from a collection resource',
    ),
    cfg.BoolOpt(
        'enable_webhooks_auth',
        default=True,
        help='This option enables or disables webhook request '
        'authentication via keystone. Default value is True.',
    ),
]


def register_opts(conf):
    conf.register_group(api)
    conf.register_opts(API_SERVICE_OPTS, group=api)
    conf.register_opts(AUTH_OPTS)


def list_opts():
    return [(api, API_SERVICE_OPTS), ('DEFAULT', AUTH_OPTS)]
