# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

import mock

from watcher.decision_engine.model.collector import base
from watcher.decision_engine.model.collector import cinder
from watcher.decision_engine.model.collector import ironic
from watcher.decision_engine.model.collector import nova
from watcher.decision_engine.model import model_root
from watcher.tests import base as test_base


class DummyClusterDataModelCollector(base.BaseClusterDataModelCollector):

    @property
    def notification_endpoints(self):
        return []

    def get_audit_scope_handler(self, audit_scope):
        return None

    def execute(self):
        model = model_root.ModelRoot()
        # Do something here...
        return model


class TestClusterDataModelCollector(test_base.TestCase):

    def test_is_singleton(self):
        m_config = mock.Mock()
        inst1 = DummyClusterDataModelCollector(config=m_config)
        inst2 = DummyClusterDataModelCollector(config=m_config)

        self.assertIs(inst1, inst2)

    def test_in_memory_model_is_copied(self):
        m_config = mock.Mock()
        collector = DummyClusterDataModelCollector(config=m_config)
        collector.synchronize()

        self.assertIs(
            collector._cluster_data_model, collector.cluster_data_model)
        self.assertIsNot(
            collector.cluster_data_model,
            collector.get_latest_cluster_data_model())


class TestComputeDataModelCollector(test_base.TestCase):

    def test_model_scope_is_none(self):
        m_config = mock.Mock()
        collector = nova.NovaClusterDataModelCollector(config=m_config)

        collector._audit_scope_handler = mock.Mock()
        collector._data_model_scope = None
        self.assertIsNone(collector.execute())


class TestStorageDataModelCollector(test_base.TestCase):

    def test_model_scope_is_none(self):
        m_config = mock.Mock()
        collector = cinder.CinderClusterDataModelCollector(config=m_config)

        collector._audit_scope_handler = mock.Mock()
        collector._data_model_scope = None
        self.assertIsNone(collector.execute())


class TestBareMetalDataModelCollector(test_base.TestCase):

    def test_model_scope_is_none(self):
        m_config = mock.Mock()
        collector = ironic.BaremetalClusterDataModelCollector(config=m_config)

        collector._audit_scope_handler = mock.Mock()
        collector._data_model_scope = None
        self.assertIsNone(collector.execute())
