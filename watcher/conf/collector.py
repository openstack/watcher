# Copyright (c) 2017 NEC Corporation
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


collector = cfg.OptGroup(name='collector',
                         title='Defines the parameters of '
                         'the module model collectors')

COLLECTOR_OPTS = [
    cfg.ListOpt('collector_plugins',
                default=['compute'],
                help='The cluster data model plugin names'),
]


def register_opts(conf):
    conf.register_group(collector)
    conf.register_opts(COLLECTOR_OPTS,
                       group=collector)


def list_opts():
    return [('collector', COLLECTOR_OPTS)]
