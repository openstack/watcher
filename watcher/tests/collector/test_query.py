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
from watcher.metrics_engine.framework.datasources.sql_ast.build_db_query import \
    DBQuery

from watcher.tests import base


class TestDBQuery(base.TestCase):

    def test_query(self):
        expected = "SELECT * FROM \"cpu_compute.cpu.user.percent_gauge\" ;"
        query = DBQuery("cpu_compute.cpu.user.percent_gauge")
        self.assertEqual(str(query), expected)

    def test_query_where(self):
        expected = "SELECT * FROM" \
                   " \"cpu_compute.cpu.user.percent_gauge\" WHERE host=jed;"
        query = DBQuery("cpu_compute.cpu.user.percent_gauge").where(
            "host=jed")
        self.assertEqual(str(query), expected)

    def test_query_filter(self):
        expected = "SELECT mean(value) FROM" \
                   " \"cpu_compute.cpu.user.percent_gauge\" WHERE host=jed;"
        query = DBQuery("cpu_compute.cpu.user.percent_gauge").where(
            "host=jed").select("mean(value)")
        self.assertEqual(str(query), expected)

    def test_query_groupby(self):
        expected = "SELECT * FROM" \
                   " \"cpu_compute.cpu.user.percent_gauge\"  " \
                   "group by time(5m);"
        query = DBQuery("cpu_compute.cpu.user.percent_gauge").groupby(
            "time(5m)")
        self.assertEqual(str(query), expected)
