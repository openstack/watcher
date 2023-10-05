# Copyright 2023 Cloudbase Solutions
# All Rights Reserved.
#
#    Licensed under the Apache License, Version 2.0 (the "License"); you may
#    not use this file except in compliance with the License. You may obtain
#    a copy of the License at
#
#         http://www.apache.org/licenses/LICENSE-2.0
#
#    Unless required by applicable law or agreed to in writing, software
#    distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
#    WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
#    License for the specific language governing permissions and limitations
#    under the License.

import asyncio
import time
from unittest import mock

from watcher.common import utils
from watcher.tests import base


class TestCommonUtils(base.TestCase):
    async def test_coro(self, sleep=0, raise_exc=None):
        time.sleep(sleep)
        if raise_exc:
            raise raise_exc
        return mock.sentinel.ret_val

    def test_async_compat(self):
        ret_val = utils.async_compat_call(self.test_coro)
        self.assertEqual(mock.sentinel.ret_val, ret_val)

    def test_async_compat_exc(self):
        self.assertRaises(
            IOError,
            utils.async_compat_call,
            self.test_coro,
            raise_exc=IOError('fake error'))

    def test_async_compat_timeout(self):
        # Timeout not reached.
        ret_val = utils.async_compat_call(self.test_coro, timeout=10)
        self.assertEqual(mock.sentinel.ret_val, ret_val)

        # Timeout reached.
        self.assertRaises(
            asyncio.TimeoutError,
            utils.async_compat_call,
            self.test_coro,
            sleep=0.5, timeout=0.1)
