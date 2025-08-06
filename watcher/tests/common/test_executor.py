# Copyright 2025 Red Hat, Inc.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import futurist
from unittest import mock

from watcher.common import executor
from watcher import eventlet as eventlet_helper
from watcher.tests import base


@mock.patch.object(eventlet_helper, 'is_patched')
class TestFuturistPoolExecutor(base.TestCase):

    def test_get_futurist_pool_executor_eventlet(self, eventlet_patched_mock):
        eventlet_patched_mock.return_value = True

        pool_executor = executor.get_futurist_pool_executor(max_workers=1)

        self.assertIsInstance(pool_executor, futurist.GreenThreadPoolExecutor)

    def test_get_futurist_pool_executor_threading(self, eventlet_patched_mock):
        eventlet_patched_mock.return_value = False

        pool_executor = executor.get_futurist_pool_executor(max_workers=1)

        self.assertIsInstance(pool_executor, futurist.ThreadPoolExecutor)
