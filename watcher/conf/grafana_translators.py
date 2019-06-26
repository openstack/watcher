# -*- encoding: utf-8 -*-
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

grafana_translators = cfg.OptGroup(name='grafana_translators',
                                   title='Configuration Options for Grafana '
                                   'transalators')

GRAFANA_TRANSLATOR_INFLUX_OPTS = [
    cfg.DictOpt('retention_periods',
                default={
                    'one_week': 604800,
                    'one_month': 2592000,
                    'five_years': 31556952
                },
                help="Keys are the names of retention periods in InfluxDB and "
                     "the values should correspond with the maximum time they "
                     "can retain in seconds. Example: {'one_day': 86400}")]


def register_opts(conf):
    conf.register_group(grafana_translators)
    conf.register_opts(GRAFANA_TRANSLATOR_INFLUX_OPTS,
                       group=grafana_translators)


def list_opts():
    return [(grafana_translators, GRAFANA_TRANSLATOR_INFLUX_OPTS)]
