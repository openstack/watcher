# -*- encoding: utf-8 -*-
# Copyright (c) 2015 b<>com
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

import types
from unittest import mock

from oslo_config import cfg
from oslo_service import service

from watcher.cmd import decisionengine
from watcher.common import service as watcher_service
from watcher.decision_engine.audit import continuous
from watcher.decision_engine import sync
from watcher.tests import base


class TestDecisionEngine(base.BaseTestCase):

    def setUp(self):
        super(TestDecisionEngine, self).setUp()

        self.conf = cfg.CONF
        self._parse_cli_opts = self.conf._parse_cli_opts

        def _fake_parse(self, args=[]):
            return cfg.ConfigOpts._parse_cli_opts(self, [])

        _fake_parse_method = types.MethodType(_fake_parse, self.conf)
        self.conf._parse_cli_opts = _fake_parse_method

        p_heartbeat = mock.patch.object(
            watcher_service.ServiceHeartbeat, "send_beat")
        self.m_heartbeat = p_heartbeat.start()
        self.addCleanup(p_heartbeat.stop)
        p_continuoushandler = mock.patch.object(
            continuous.ContinuousAuditHandler, "start")
        self.m_continuoushandler = p_continuoushandler.start()
        self.addCleanup(p_continuoushandler.stop)

    def tearDown(self):
        super(TestDecisionEngine, self).tearDown()
        self.conf._parse_cli_opts = self._parse_cli_opts

    @mock.patch.object(sync.Syncer, "sync", mock.Mock())
    @mock.patch.object(service, "launch")
    def test_run_de_app(self, m_launch):
        decisionengine.main()
        self.assertEqual(1, m_launch.call_count)
