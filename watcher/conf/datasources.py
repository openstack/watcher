# Copyright (c) 2019 European Organization for Nuclear Research (CERN)
#
# Authors: Corne Lukken <info@dantalion.nl>
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

from watcher.decision_engine.datasources import manager
from watcher.decision_engine.datasources import prometheus

datasources = cfg.OptGroup(name='watcher_datasources',
                           title='Configuration Options for watcher'
                                 ' datasources')

possible_datasources = list(manager.DataSourceManager.metric_map.keys())

# NOTE(jwysogla): Having the Aetos and Prometheus datasources specified at the
# same time raises a DataSourceConfigConflict exception. The Prometheus
# datasource is deprecated in favor of Aetos, so we remove Prometheus from
# the default configuration.
default_datasources = list(possible_datasources)
default_datasources.remove(prometheus.PrometheusHelper.NAME)

DATASOURCES_OPTS = [
    cfg.ListOpt("datasources",
                help="Datasources to use in order to query the needed metrics."
                     " If one of strategy metric is not available in the first"
                     " datasource, the next datasource will be chosen. This is"
                     " the default for all strategies unless a strategy has a"
                     " specific override.",
                item_type=cfg.types.String(choices=possible_datasources),
                default=default_datasources),
    cfg.IntOpt('query_max_retries',
               min=1,
               default=10,
               mutable=True,
               help='How many times Watcher is trying to query again'),
    cfg.IntOpt('query_interval',
               min=0,
               default=1,
               mutable=True,
               help='How many seconds Watcher should wait to do query again',
               deprecated_name="query_timeout")
    ]


def register_opts(conf):
    conf.register_group(datasources)
    conf.register_opts(DATASOURCES_OPTS, group=datasources)


def list_opts():
    return [(datasources, DATASOURCES_OPTS)]
