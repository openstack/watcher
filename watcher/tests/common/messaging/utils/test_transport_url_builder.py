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


from oslo_config import cfg
import re
from watcher.common.messaging.utils.transport_url_builder import \
    TransportUrlBuilder
from watcher.tests import base

CONF = cfg.CONF


class TestTransportUrlBuilder(base.TestCase):

    def setUp(self):
        super(TestTransportUrlBuilder, self).setUp()

    def test_transport_url_not_none(self):
        url = TransportUrlBuilder().url
        print(url)
        self.assertIsNotNone(url, "The transport url must not be none")

    def test_transport_url_valid_pattern(self):
        url = TransportUrlBuilder().url
        url_pattern = r'(\D+)://(\D+):(\D+)@(\D+):(\d+)'
        pattern = re.compile(url_pattern)
        match = re.search(url_pattern, url)
        self.assertEqual('rabbit', match.group(1))
        self.assertEqual('guest', match.group(2))
        self.assertEqual('guest', match.group(3))
        self.assertEqual('localhost', match.group(4))
        self.assertEqual('5672', match.group(5))
        self.assertIsNotNone(pattern.match(url))
