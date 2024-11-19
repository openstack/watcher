# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.
from unittest import mock

import eventlet

from apscheduler.schedulers import background

from watcher.common import scheduling
from watcher import eventlet as eventlet_helper
from watcher.tests import base


class TestSchedulerMonkeyPatching(base.BaseTestCase):

    def setUp(self):
        super().setUp()
        self.started = False
        self.test_scheduler = scheduling.BackgroundSchedulerService()
        self.addCleanup(self._cleanup_scheduler)

    def _cleanup_scheduler(self):
        if self.started:
            self.test_scheduler.shutdown()
            self.started = False

    def _start_scheduler(self):
        self.test_scheduler.start()
        self.started = True

    @mock.patch.object(scheduling.BackgroundSchedulerService, 'start')
    def test_scheduler_start(self, mock_start):
        self.test_scheduler.start()
        mock_start.assert_called_once_with()

    @mock.patch.object(scheduling.BackgroundSchedulerService, 'shutdown')
    def test_scheduler_stop(self, mock_shutdown):
        self._start_scheduler()
        self.test_scheduler.stop()
        mock_shutdown.assert_called_once_with()

    @mock.patch.object(scheduling.BackgroundSchedulerService, '_main_loop')
    def test_scheduler_main_loop(self, mock_main_loop):
        self._start_scheduler()
        mock_main_loop.assert_called_once_with()

    @mock.patch.object(background.BackgroundScheduler, '_main_loop')
    @mock.patch.object(eventlet, 'monkey_patch')
    def test_main_loop_is_monkey_patched(
            self, mock_monky_patch, mock_main_loop):
        self.test_scheduler._main_loop()
        self.assertEqual(
            eventlet_helper.is_patched(), self.test_scheduler.should_patch)
        mock_monky_patch.assert_called_once_with()
        mock_main_loop.assert_called_once_with()

    def test_scheduler_should_patch(self):
        self.assertEqual(
            eventlet_helper.is_patched(), self.test_scheduler.should_patch)
