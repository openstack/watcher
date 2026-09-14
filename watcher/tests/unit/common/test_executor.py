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

from unittest import mock

import futurist

from watcher.common import executor
from watcher.tests.unit import base


class TestFuturistPoolExecutor(base.TestCase):
    def test_get_futurist_pool_executor_threading(self):

        pool_executor = executor.get_futurist_pool_executor(max_workers=1)

        self.assertIsInstance(pool_executor, futurist.ThreadPoolExecutor)


@mock.patch.object(executor.CONF, 'print_thread_pool_stats', True)
class TestLogExecutorStats(base.TestCase):
    @mock.patch.object(executor.LOG, 'debug')
    def test_log_executor_stats_threading(self, m_log_debug):
        workers = 3
        pool_executor = futurist.ThreadPoolExecutor(workers)

        executor.log_executor_stats(
            pool_executor, name="test-threadpool-threading"
        )

        m_log_debug.assert_called_once_with(
            "State of %s ThreadPoolExecutor when submitting a new "
            "task: max_workers: %d, workers: %d, idle workers: %d, "
            "queued work: %d, stats: %s",
            "test-threadpool-threading",
            workers,
            len(pool_executor._workers),
            len([w for w in pool_executor._workers if w.idle]),
            pool_executor._work_queue.qsize(),
            pool_executor.statistics,
        )
