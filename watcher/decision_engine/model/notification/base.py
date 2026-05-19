# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <Vincent.FRANCOISE@b-com.com>
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

import abc

from oslo_log import log


LOG = log.getLogger(__name__)


class NotificationEndpoint(metaclass=abc.ABCMeta):
    def __init__(self, collector):
        super().__init__()
        self.collector = collector
        self._notifier = None

    @property
    @abc.abstractmethod
    def filter_rule(self):
        """Notification Filter"""
        raise NotImplementedError()

    @property
    def cluster_data_model(self):
        return self.collector.cluster_data_model

    def info(self, ctxt, publisher_id, event_type, payload, metadata):
        """oslo.messaging entry point.

        Acquires the collector sync lock before processing to ensure
        notifications are never applied to a model that is about to be
        replaced by an in-progress synchronization.
        """
        with self.collector.sync_lock:
            self.process_info(
                ctxt, publisher_id, event_type, payload, metadata
            )

    @abc.abstractmethod
    def process_info(self, ctxt, publisher_id, event_type, payload, metadata):
        """Process the notification. Subclasses must implement this."""
        raise NotImplementedError()
