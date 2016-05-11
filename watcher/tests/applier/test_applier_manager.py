# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
#
# Authors: Jean-Emile DARTOIS <jean-emile.dartois@b-com.com>
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
#

from mock import patch

from watcher.applier import manager as applier_manager
from watcher.common.messaging import messaging_handler
from watcher.common import service
from watcher.tests import base


class TestApplierManager(base.TestCase):
    def setUp(self):
        super(TestApplierManager, self).setUp()
        self.applier = service.Service(applier_manager.ApplierManager)

    @patch.object(messaging_handler.MessagingHandler, "stop")
    @patch.object(messaging_handler.MessagingHandler, "start")
    def test_start(self, m_messaging_start, m_messaging_stop):
        self.applier.start()
        self.applier.stop()
        self.assertEqual(2, m_messaging_start.call_count)
        self.assertEqual(2, m_messaging_stop.call_count)
