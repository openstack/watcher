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

from apscheduler import events
from apscheduler.schedulers import background

from oslo_service import service

from watcher.common import executor
from watcher import eventlet as eventlet_helper

job_events = events

executors = {
    'default': executor.APSchedulerThreadPoolExecutor(),
}


class BackgroundSchedulerService(
        service.ServiceBase, background.BackgroundScheduler):
    def __init__(self, gconfig=None, **options):
        if options is None:
            options = {'executors': executors}
        else:
            if 'executors' not in options.keys():
                options['executors'] = executors
        super().__init__(gconfig or {}, **options)

    def _main_loop(self):
        # NOTE(dviroel): to make sure that we monkey patch when needed.
        # helper patch() now checks a environment variable to see if
        # the service should or not be patched.
        eventlet_helper.patch()
        super()._main_loop()

    def add_job(self, *args, **kwargs):
        executor.log_executor_stats(executors['default'].executor,
                                    name="background-scheduler-pool")
        return super().add_job(*args, **kwargs)

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
