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

import eventlet

from apscheduler import events
from apscheduler.executors import pool as pool_executor
from apscheduler.schedulers import background

import futurist

from oslo_service import service

from watcher import eventlet as eventlet_helper

job_events = events


class GreenThreadPoolExecutor(pool_executor.BasePoolExecutor):
    """Green thread pool

    An executor that runs jobs in a green thread pool.
    Plugin alias: ``threadpool``
    :param max_workers: the maximum number of spawned threads.
    """

    def __init__(self, max_workers=10):
        pool = futurist.GreenThreadPoolExecutor(int(max_workers))
        super(GreenThreadPoolExecutor, self).__init__(pool)


executors = {
    'default': GreenThreadPoolExecutor(),
}


class BackgroundSchedulerService(
        service.ServiceBase, background.BackgroundScheduler):
    def __init__(self, gconfig=None, **options):
        self.should_patch = eventlet_helper.is_patched()
        if options is None:
            options = {'executors': executors}
        else:
            if 'executors' not in options.keys():
                options['executors'] = executors
        super().__init__(gconfig or {}, **options)

    def _main_loop(self):
        if self.should_patch:
            # NOTE(sean-k-mooney): is_patched and monkey_patch form
            # watcher.eventlet check a non thread local variable to early out
            # as we do not use eventlet_helper.patch() here to ensure
            # eventlet.monkey_patch() is actually called.
            eventlet.monkey_patch()
        super()._main_loop()

    def start(self):
        """Start service."""
        background.BackgroundScheduler.start(self)

    def stop(self):
        """Stop service."""
        self.shutdown()

    def wait(self):
        """Wait for service to complete."""

    def reset(self):
        """Reset service.

        Called in case service running in daemon mode receives SIGHUP.
        """
