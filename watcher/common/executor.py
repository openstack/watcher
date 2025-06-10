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

from watcher import eventlet as eventlet_helper


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
        pool = get_futurist_pool_executor(max_workers)
        super(APSchedulerThreadPoolExecutor, self).__init__(pool)
