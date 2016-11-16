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

from watcher.notifications import base as notificationbase
from watcher.objects import base
from watcher.objects import fields as wfields


@base.WatcherObjectRegistry.register_notification
class StrategyPayload(notificationbase.NotificationPayloadBase):
    SCHEMA = {
        'uuid': ('strategy', 'uuid'),
        'name': ('strategy', 'name'),
        'display_name': ('strategy', 'display_name'),
        'parameters_spec': ('strategy', 'parameters_spec'),

        'created_at': ('strategy', 'created_at'),
        'updated_at': ('strategy', 'updated_at'),
        'deleted_at': ('strategy', 'deleted_at'),
    }

    # Version 1.0: Initial version
    VERSION = '1.0'

    fields = {
        'uuid': wfields.UUIDField(),
        'name': wfields.StringField(),
        'display_name': wfields.StringField(),
        'parameters_spec': wfields.FlexibleDictField(nullable=True),

        'created_at': wfields.DateTimeField(nullable=True),
        'updated_at': wfields.DateTimeField(nullable=True),
        'deleted_at': wfields.DateTimeField(nullable=True),
    }

    def __init__(self, strategy, **kwargs):
        super(StrategyPayload, self).__init__(**kwargs)
        self.populate_schema(strategy=strategy)
