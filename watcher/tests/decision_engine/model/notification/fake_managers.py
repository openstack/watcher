# -*- encoding: utf-8 -*-
# Copyright (c) 2016 b<>com
#
# Authors: Vincent FRANCOISE <vincent.francoise@b-com.com>
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#    http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or
# implied.
# See the License for the specific language governing permissions and
# limitations under the License.

from watcher.common import service_manager
from watcher.decision_engine.model.notification import cinder as cnotification
from watcher.decision_engine.model.notification import nova as novanotification
from watcher.tests.decision_engine.model import faker_cluster_state


class FakeManager(service_manager.ServiceManager):

    API_VERSION = '1.0'

    fake_cdmc = faker_cluster_state.FakerModelCollector()

    @property
    def service_name(self):
        return 'watcher-fake'

    @property
    def api_version(self):
        return self.API_VERSION

    @property
    def publisher_id(self):
        return 'test_publisher_id'

    @property
    def conductor_topic(self):
        return 'test_conductor_topic'

    @property
    def notification_topics(self):
        return ['nova']

    @property
    def conductor_endpoints(self):
        return []  # Disable audit endpoint

    @property
    def notification_endpoints(self):
        return [
            novanotification.VersionedNotification(self.fake_cdmc),
        ]


class FakeStorageManager(FakeManager):

    fake_cdmc = faker_cluster_state.FakerStorageModelCollector()

    @property
    def notification_endpoints(self):
        return [
            cnotification.CapacityNotificationEndpoint(self.fake_cdmc),
            cnotification.VolumeCreateEnd(self.fake_cdmc),
            cnotification.VolumeUpdateEnd(self.fake_cdmc),
            cnotification.VolumeDeleteEnd(self.fake_cdmc),
            cnotification.VolumeAttachEnd(self.fake_cdmc),
            cnotification.VolumeDetachEnd(self.fake_cdmc),
            cnotification.VolumeResizeEnd(self.fake_cdmc),
        ]
