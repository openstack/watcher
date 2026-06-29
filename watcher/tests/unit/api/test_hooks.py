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

"""Tests for the Pecan API hooks."""

from http import client as http_client
from unittest import mock

import oslo_messaging as messaging

from oslo_config import cfg
from oslo_serialization import jsonutils

from watcher.api.controllers import root
from watcher.tests.unit.api import base


class TestNoExceptionTracebackHook(base.FunctionalTest):
    TRACE = [
        'Traceback (most recent call last):',
        '  File "/opt/stack/watcher/watcher/common/rpc/amqp.py",'
        ' line 434, in _process_data\\n   **args)',
        '  File "/opt/stack/watcher/watcher/common/rpc/'
        'dispatcher.py", line 172, in dispatch\\n   result ='
        ' getattr(proxyobj, method)(ctxt, **kwargs)',
    ]
    MSG_WITHOUT_TRACE = "Test exception message."
    MSG_WITH_TRACE = MSG_WITHOUT_TRACE + "\n" + "\n".join(TRACE)

    def setUp(self):
        super().setUp()
        p = mock.patch.object(root.Root, 'convert')
        self.root_convert_mock = p.start()
        self.addCleanup(p.stop)
        cfg.CONF.set_override('debug', False)

    def test_hook_exception_success(self):
        self.root_convert_mock.side_effect = Exception(self.MSG_WITH_TRACE)

        response = self.get_json('/', path_prefix='', expect_errors=True)

        actual_msg = jsonutils.loads(response.json['error_message'])[
            'faultstring'
        ]
        self.assertEqual(self.MSG_WITHOUT_TRACE, actual_msg)

    def test_hook_remote_error_success(self):
        test_exc_type = 'TestException'
        self.root_convert_mock.side_effect = messaging.rpc.RemoteError(
            test_exc_type, self.MSG_WITHOUT_TRACE, self.TRACE
        )

        response = self.get_json('/', path_prefix='', expect_errors=True)

        # NOTE(max_lobur): For RemoteError the client message will still have
        # some garbage because in RemoteError traceback is serialized as a list
        # instead of'\n'.join(trace). But since RemoteError is kind of very
        # rare thing (happens due to wrong deserialization settings etc.)
        # we don't care about this garbage.
        expected_msg = (
            f"Remote error: {test_exc_type} {self.MSG_WITHOUT_TRACE}\n['"
        )
        actual_msg = jsonutils.loads(response.json['error_message'])[
            'faultstring'
        ]
        self.assertEqual(expected_msg, actual_msg)

    def _test_hook_without_traceback(self):
        msg = "Error message without traceback \n but \n multiline"
        self.root_convert_mock.side_effect = Exception(msg)

        response = self.get_json('/', path_prefix='', expect_errors=True)

        actual_msg = jsonutils.loads(response.json['error_message'])[
            'faultstring'
        ]
        self.assertEqual(msg, actual_msg)

    def test_hook_without_traceback(self):
        self._test_hook_without_traceback()

    def test_hook_without_traceback_debug(self):
        cfg.CONF.set_override('debug', True)
        self._test_hook_without_traceback()

    def _test_hook_on_serverfault(self):
        self.root_convert_mock.side_effect = Exception(self.MSG_WITH_TRACE)

        response = self.get_json('/', path_prefix='', expect_errors=True)

        actual_msg = jsonutils.loads(response.json['error_message'])[
            'faultstring'
        ]
        return actual_msg

    def test_hook_on_serverfault(self):
        cfg.CONF.set_override('debug', False)
        msg = self._test_hook_on_serverfault()
        self.assertEqual(self.MSG_WITHOUT_TRACE, msg)

    def test_hook_on_serverfault_debug(self):
        cfg.CONF.set_override('debug', True)
        msg = self._test_hook_on_serverfault()
        self.assertEqual(self.MSG_WITH_TRACE, msg)

    def _test_hook_on_clientfault(self):
        client_error = Exception(self.MSG_WITH_TRACE)
        client_error.code = http_client.BAD_REQUEST
        self.root_convert_mock.side_effect = client_error

        response = self.get_json('/', path_prefix='', expect_errors=True)

        actual_msg = jsonutils.loads(response.json['error_message'])[
            'faultstring'
        ]
        return actual_msg

    def test_hook_on_clientfault(self):
        msg = self._test_hook_on_clientfault()
        self.assertEqual(self.MSG_WITHOUT_TRACE, msg)

    def test_hook_on_clientfault_debug_tracebacks(self):
        cfg.CONF.set_override('debug', True)
        msg = self._test_hook_on_clientfault()
        self.assertEqual(self.MSG_WITH_TRACE, msg)
