# -*- encoding: utf-8 -*-
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
from oslo_db import options as oslo_db_options

from watcher.conf import paths

_DEFAULT_SQL_CONNECTION = 'sqlite:///{0}'.format(
    paths.state_path_def('watcher.sqlite'))

database = cfg.OptGroup(name='database',
                        title='Configuration Options for database')

SQL_OPTS = [
    cfg.StrOpt('mysql_engine',
               default='InnoDB',
               help='MySQL engine to use.')
]


def register_opts(conf):
    oslo_db_options.set_defaults(conf, connection=_DEFAULT_SQL_CONNECTION)
    conf.register_group(database)
    conf.register_opts(SQL_OPTS, group=database)


def list_opts():
    return [(database, SQL_OPTS)]
