# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
#

from watcher.metrics_engine.framework.datasources.sql_ast.sql_ast import From
from watcher.metrics_engine.framework.datasources.sql_ast.sql_ast import \
    GroupBy
from watcher.metrics_engine.framework.datasources.sql_ast.sql_ast import Limit
from watcher.metrics_engine.framework.datasources.sql_ast.sql_ast import List
from watcher.metrics_engine.framework.datasources.sql_ast.sql_ast import Select
from watcher.metrics_engine.framework.datasources.sql_ast.sql_ast import Where


class DBQuery(object):
    def __init__(self, _from):
        self._select = Select(_from)
        self.inline = False

    def select_from(self, _from):
        self._select._from = From(_from)
        return self

    def where(self, where):
        self._select.where = Where(where)
        return self

    def groupby(self, g):
        self._select.groupby = GroupBy(g)
        return self

    def limit(self, limit):
        self._select.limit = Limit(limit)
        return self

    def select(self, *args):
        self._select.what = List(*args)
        return self

    def __str__(self):
        self._select.inline = self.inline
        s = str(self._select)
        if not self.inline:
            s += ';'
        return s
