# -*- encoding: utf-8 -*-
# Copyright (c) 2017 Servionica
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

from unittest import mock

import freezegun
import oslo_messaging as om
from oslo_utils import timeutils

from watcher.common import rpc
from watcher import notifications
from watcher.objects import service as w_service
from watcher.tests.db import base
from watcher.tests.objects import utils


@freezegun.freeze_time('2016-10-18T09:52:05.219414')
class TestActionPlanNotification(base.DbTestCase):

    def setUp(self):
        super(TestActionPlanNotification, self).setUp()
        p_get_notifier = mock.patch.object(rpc, 'get_notifier')
        m_get_notifier = p_get_notifier.start()
        self.addCleanup(p_get_notifier.stop)
        self.m_notifier = mock.Mock(spec=om.Notifier)

        def fake_get_notifier(publisher_id):
            self.m_notifier.publisher_id = publisher_id
            return self.m_notifier

        m_get_notifier.side_effect = fake_get_notifier

    def test_service_failed(self):
        service = utils.get_test_service(mock.Mock(),
                                         created_at=timeutils.utcnow())
        state = w_service.ServiceStatus.FAILED
        notifications.service.send_service_update(mock.MagicMock(),
                                                  service,
                                                  state,
                                                  host='node0')
        notification = self.m_notifier.warning.call_args[1]
        payload = notification['payload']
        self.assertEqual("infra-optim:node0", self.m_notifier.publisher_id)
        self.assertDictEqual({
            'watcher_object.data': {
                'last_seen_up': '2016-09-22T08:32:06Z',
                'name': 'watcher-service',
                'sevice_host': 'controller',
                'status_update': {
                    'watcher_object.data': {
                        'old_state': 'ACTIVE',
                        'state': 'FAILED'
                    },
                    'watcher_object.name': 'ServiceStatusUpdatePayload',
                    'watcher_object.namespace': 'watcher',
                    'watcher_object.version': '1.0'
                }
            },
            'watcher_object.name': 'ServiceUpdatePayload',
            'watcher_object.namespace': 'watcher',
            'watcher_object.version': '1.0'
        },
            payload
        )
