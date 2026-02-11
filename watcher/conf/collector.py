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
                default=['compute', 'storage'],
                help="""
The cluster data model plugin names.

Supported in-tree collectors include:

* ``compute`` - data model collector for nova
* ``storage`` - data model collector for cinder
* ``baremetal`` - data model collector for ironic

Custom data model collector plugins can be defined with the
``watcher_cluster_data_model_collectors`` extension point.
"""),
    cfg.IntOpt('api_query_max_retries',
               min=1,
               default=10,
               help="Number of retries before giving up on query to "
                    "external service.",
               deprecated_name="api_call_retries"),
    cfg.IntOpt('api_query_interval',
               min=0,
               default=1,
               help="Time before retry after failed query to "
                    "external service.",
               deprecated_name="api_query_timeout"),
    cfg.IntOpt("compute_resources_collector_timeout",
               min=30,
               default=600,
               help="Timeout in seconds for collecting multiple compute "
                    "resources from nova. Note that this timeout does not "
                    "represent the total time for collecting all resources. "
                    "Setting this value to 0 or small values will cause the "
                    "collector to abort and stop the collection process."),
]


def register_opts(conf):
    conf.register_group(collector)
    conf.register_opts(COLLECTOR_OPTS,
                       group=collector)


def list_opts():
    return [(collector, COLLECTOR_OPTS)]
