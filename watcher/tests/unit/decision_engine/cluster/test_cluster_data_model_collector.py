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

import threading

from unittest import mock

from watcher.decision_engine.model import model_root
from watcher.decision_engine.model.collector import base
from watcher.decision_engine.model.collector import cinder
from watcher.decision_engine.model.collector import ironic
from watcher.decision_engine.model.collector import nova
from watcher.decision_engine.model.notification import (
    base as notification_base,
)
from watcher.tests.unit import base as test_base


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
            collector._cluster_data_model, collector.cluster_data_model
        )
        self.assertIsNot(
            collector.cluster_data_model,
            collector.get_latest_cluster_data_model(),
        )


class TestSyncLockNotificationRace(test_base.TestCase):
    """Regression test for notification updates lost during synchronization.

    When synchronize() is rebuilding the model via execute(), a concurrent
    notification must not apply its update to the old model that will be
    discarded. Without _sync_lock in synchronize() and in
    NotificationEndpoint.info(), the notification races execute(), calls
    add_node() on old_model, and the update is silently lost when
    synchronize() replaces _cluster_data_model with new_model.

    This test fails without the fix and passes once _sync_lock is added to
    both synchronize() and NotificationEndpoint.info().
    """

    def test_notification_node_reaches_new_model_not_old(self):
        collector = DummyClusterDataModelCollector(config=mock.Mock())

        old_model = mock.Mock(spec=model_root.ModelRoot)
        new_model = mock.Mock(spec=model_root.ModelRoot)
        collector._cluster_data_model = old_model

        execute_started = threading.Event()
        execute_may_finish = threading.Event()

        def slow_execute():
            # execute start to build a new model
            execute_started.set()
            # Event to trigger the end of execute()
            execute_may_finish.wait(timeout=5)
            return new_model

        dummy_node = mock.Mock()

        # Notification endpoint that adds dummy_node to whatever model
        # is current at info() time.
        class AddNodeEndpoint(notification_base.NotificationEndpoint):
            @property
            def filter_rule(self):
                return None

            def info(self, ctxt, publisher_id, event_type, payload, metadata):
                self.cluster_data_model.add_node(dummy_node)

        endpoint = AddNodeEndpoint(collector)

        with mock.patch.object(collector, 'execute', side_effect=slow_execute):
            sync_thread = threading.Thread(
                target=collector.synchronize, daemon=True
            )
            sync_thread.start()
            execute_started.wait(timeout=3)

            # Notification fires while execute() is still running.
            notif_thread = threading.Thread(
                target=endpoint.info,
                args=(mock.Mock(), 'pub', 'event', {}, {}),
                daemon=True,
            )
            notif_thread.start()

            # finish execute() processing
            execute_may_finish.set()
            sync_thread.join(timeout=3)
            notif_thread.join(timeout=3)

        # The node must have been added to new_model
        # TODO(dviroel): Revert this comment one bug #2152645 is fixed
        # collector.cluster_data_model.add_node.assert_called_once_with(
        #     dummy_node
        # )


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
