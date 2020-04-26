# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
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

from watcher.decision_engine import gmr
from watcher.decision_engine.model.collector import manager
from watcher.tests import base


class TestGmrPlugin(base.TestCase):

    @mock.patch.object(manager.CollectorManager, "get_collectors")
    def test_show_models(self, m_get_collectors):
        m_to_string = mock.Mock(return_value="<TESTMODEL />")
        m_get_collectors.return_value = {
            "test_model": mock.Mock(
                cluster_data_model=mock.Mock(to_string=m_to_string))}
        output = gmr.show_models()
        self.assertEqual(1, m_to_string.call_count)
        self.assertIn("<TESTMODEL />", output)
