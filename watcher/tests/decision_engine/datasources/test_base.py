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

from unittest import mock

from oslo_config import cfg

from watcher.decision_engine.datasources import base as datasource
from watcher.tests import base

CONF = cfg.CONF


class TestBaseDatasourceHelper(base.BaseTestCase):

    def test_query_retry(self):
        exc = Exception()
        method = mock.Mock()
        # first call will fail but second will succeed
        method.side_effect = [exc, True]
        # Max 2 attempts
        CONF.set_override("query_max_retries", 2,
                          group='watcher_datasources')
        # Reduce sleep time to 0
        CONF.set_override("query_timeout", 0,
                          group='watcher_datasources')

        helper = datasource.DataSourceBase()
        helper.query_retry_reset = mock.Mock()

        self.assertTrue(helper.query_retry(f=method))
        helper.query_retry_reset.assert_called_once_with(exc)

    def test_query_retry_exception(self):
        exc = Exception()
        method = mock.Mock()
        # only third call will succeed
        method.side_effect = [exc, exc, True]
        # Max 2 attempts
        CONF.set_override("query_max_retries", 2,
                          group='watcher_datasources')
        # Reduce sleep time to 0
        CONF.set_override("query_timeout", 0,
                          group='watcher_datasources')

        helper = datasource.DataSourceBase()
        helper.query_retry_reset = mock.Mock()

        # Maximum number of retries exceeded query_retry should return None
        self.assertIsNone(helper.query_retry(f=method))
        # query_retry_reset should be called twice
        helper.query_retry_reset.assert_has_calls(
            [mock.call(exc), mock.call(exc)])
