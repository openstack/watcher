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

from watcher.decision_engine.model.notification import nova as novanotification
from watcher.tests.decision_engine.strategy.strategies \
    import faker_cluster_state


class FakeManager(object):

    API_VERSION = '1.0'

    def __init__(self):
        self.api_version = self.API_VERSION

        # fake cluster instead on Nova CDM
        self.fake_cdmc = faker_cluster_state.FakerModelCollector()

        self.publisher_id = 'test_publisher_id'
        self.conductor_topic = 'test_conductor_topic'
        self.status_topic = 'test_status_topic'
        self.notification_topics = ['nova']

        self.conductor_endpoints = []  # Disable audit endpoint
        self.status_endpoints = []

        self.notification_endpoints = [
            novanotification.ServiceUpdated(self.fake_cdmc),

            novanotification.InstanceCreated(self.fake_cdmc),
            novanotification.InstanceUpdated(self.fake_cdmc),
            novanotification.InstanceDeletedEnd(self.fake_cdmc),

            novanotification.LegacyInstanceCreatedEnd(self.fake_cdmc),
            novanotification.LegacyInstanceUpdated(self.fake_cdmc),
            novanotification.LegacyLiveMigratedEnd(self.fake_cdmc),
            novanotification.LegacyInstanceDeletedEnd(self.fake_cdmc),
        ]
