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
from watcher.tests.unit import base


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


@mock.patch.object(executor.CONF, 'print_thread_pool_stats', True)
class TestLogExecutorStats(base.TestCase):

    @mock.patch.object(executor.LOG, 'debug')
    def test_log_executor_stats_eventlet(self, m_log_debug):
        workers = 2
        pool_executor = futurist.GreenThreadPoolExecutor(workers)

        executor.log_executor_stats(pool_executor,
                                    name="test-threadpool-eventlet")

        m_log_debug.assert_called_once_with(
            f"State of test-threadpool-eventlet GreenThreadPoolExecutor when "
            f"submitting a new task: "
            f"workers: {len(pool_executor._pool.coroutines_running):d}, "
            f"max_workers: {workers:d}, "
            f"work queued length: "
            f"{pool_executor._delayed_work.unfinished_tasks:d}, "
            f"stats: {pool_executor.statistics}")

    @mock.patch.object(executor.LOG, 'debug')
    def test_log_executor_stats_threading(self, m_log_debug):
        workers = 3
        pool_executor = futurist.ThreadPoolExecutor(workers)

        executor.log_executor_stats(pool_executor,
                                    name="test-threadpool-threading")

        m_log_debug.assert_called_once_with(
            f"State of test-threadpool-threading ThreadPoolExecutor when "
            f"submitting a new task: "
            f"max_workers: {workers:d}, "
            f"workers: {len(pool_executor._workers):d}, "
            f"idle workers: "
            f"{len([w for w in pool_executor._workers if w.idle]):d}, "
            f"queued work: {pool_executor._work_queue.qsize():d}, "
            f"stats: {pool_executor.statistics}")
