# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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
from oslo import messaging

from watcher.common.messaging.utils.observable import \
    Observable
from watcher.openstack.common import log


eventlet.monkey_patch()
LOG = log.getLogger(__name__)


class NotificationHandler(Observable):
    def __init__(self, publisher_id):
        Observable.__init__(self)
        self.publisher_id = publisher_id

    def info(self, ctx, publisher_id, event_type, payload, metadata):
        if publisher_id == self.publisher_id:
            self.set_changed()
            self.notify(ctx, publisher_id, event_type, metadata, payload)
            return messaging.NotificationResult.HANDLED

    def warn(self, ctx, publisher_id, event_type, payload, metadata):
        if publisher_id == self.publisher_id:
            self.set_changed()
            self.notify(ctx, publisher_id, event_type, metadata, payload)
            return messaging.NotificationResult.HANDLED

    def error(self, ctx, publisher_id, event_type, payload, metadata):
        if publisher_id == self.publisher_id:
            self.set_changed()
            self.notify(ctx, publisher_id, event_type, metadata, payload)
            return messaging.NotificationResult.HANDLED
