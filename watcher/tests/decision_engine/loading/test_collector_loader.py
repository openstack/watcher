# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

from stevedore import driver as drivermanager
from stevedore import extension as stevedore_extension
from unittest import mock

from watcher.common import clients
from watcher.common import exception
from watcher.decision_engine.loading import default as default_loading
from watcher.tests import base
from watcher.tests import conf_fixture
from watcher.tests.decision_engine.model import faker_cluster_state


class TestClusterDataModelCollectorLoader(base.TestCase):

    def setUp(self):
        super(TestClusterDataModelCollectorLoader, self).setUp()
        self.useFixture(conf_fixture.ConfReloadFixture())
        self.collector_loader = (
            default_loading.ClusterDataModelCollectorLoader())

    def test_load_collector_with_empty_model(self):
        self.assertRaises(
            exception.LoadingError, self.collector_loader.load, None)

    def test_collector_loader(self):
        fake_driver = "fake"
        # Set up the fake Stevedore extensions
        fake_driver_call = drivermanager.DriverManager.make_test_instance(
            extension=stevedore_extension.Extension(
                name=fake_driver,
                entry_point="%s:%s" % (
                    faker_cluster_state.FakerModelCollector.__module__,
                    faker_cluster_state.FakerModelCollector.__name__),
                plugin=faker_cluster_state.FakerModelCollector,
                obj=None,
            ),
            namespace="watcher_cluster_data_model_collectors",
        )

        with mock.patch.object(drivermanager,
                               "DriverManager") as m_driver_manager:
            m_driver_manager.return_value = fake_driver_call
            loaded_collector = self.collector_loader.load("fake")

        self.assertIsInstance(
            loaded_collector, faker_cluster_state.FakerModelCollector)


class TestLoadClusterDataModelCollectors(base.TestCase):

    collector_loader = default_loading.ClusterDataModelCollectorLoader()

    scenarios = [
        (collector_name,
         {"collector_name": collector_name, "collector_cls": collector_cls})
        for collector_name, collector_cls
        in collector_loader.list_available().items()]

    def setUp(self):
        super(TestLoadClusterDataModelCollectors, self).setUp()
        self.useFixture(conf_fixture.ConfReloadFixture())

    @mock.patch.object(clients, 'OpenStackClients', mock.Mock())
    def test_load_cluster_data_model_collectors(self):
        collector = self.collector_loader.load(self.collector_name)
        self.assertIsNotNone(collector)
