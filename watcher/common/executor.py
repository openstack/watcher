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

from apscheduler.executors import pool as pool_executor
import futurist

from oslo_config import cfg
from oslo_log import log
from watcher import eventlet as eventlet_helper

LOG = log.getLogger(__name__)

CONF = cfg.CONF


def get_futurist_pool_executor(max_workers=10):
    """Returns a futurist pool executor

    :param max_workers: the maximum number of spawned threads
    :return: a futurist pool executor
    :rtype: futurist.ThreadPoolExecutor or futurist.GreenThreadPoolExecutor
            depending if eventlet patching is enabled or not
    """
    if eventlet_helper.is_patched():
        return futurist.GreenThreadPoolExecutor(max_workers)
    else:
        return futurist.ThreadPoolExecutor(max_workers)


def log_executor_stats(executor, name="unknown"):
    """Log the statistics of the executor.

    This is usually called before submitting a new task.
    """
    if not CONF.print_thread_pool_stats:
        return

    stats: futurist.ExecutorStatistics = executor.statistics
    try:
        if isinstance(executor, futurist.ThreadPoolExecutor):
            LOG.debug(
                f"State of {name} ThreadPoolExecutor when submitting a new "
                f"task: max_workers: {executor._max_workers:d}, "
                f"workers: {len(executor._workers):d}, "
                "idle workers: "
                f"{len([w for w in executor._workers if w.idle]):d}, "
                f"queued work: {executor._work_queue.qsize():d}, "
                f"stats: {stats}")
        elif isinstance(executor, futurist.GreenThreadPoolExecutor):
            LOG.debug(
                f"State of {name} GreenThreadPoolExecutor when submitting a "
                "new task: "
                f"workers: {len(executor._pool.coroutines_running):d}, "
                f"max_workers: {executor._pool.size:d}, "
                f"work queued length: "
                f"{executor._delayed_work.unfinished_tasks:d}, "
                f"stats: {stats}")
    except Exception as e:
        LOG.debug(f"Failed to log executor stats for {name}: {e}")


class APSchedulerThreadPoolExecutor(pool_executor.BasePoolExecutor):
    """Thread pool executor for APScheduler based classes

    This will return an executor for APScheduler based class which
    will be constructed using the futurist.ThreadPoolExecutor or
    futurist.GreenThreadPoolExecutor as pool, depending if eventlet
    patching is enabled or not.

    :param max_workers: the maximum number of spawned threads
    :return: a thread pool executor
    :rtype: an APScheduler pool executor object
    """

    def __init__(self, max_workers=10):
        self._executor = get_futurist_pool_executor(max_workers)
        super().__init__(self._executor)

    @property
    def executor(self):
        return self._executor
