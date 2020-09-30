# -*- encoding: utf-8 -*-
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
from oslo_config import cfg
import oslo_messaging as messaging
from oslo_serialization import jsonutils
from unittest import mock
from watcher.api.controllers import root
from watcher.api import hooks
from watcher.common import context
from watcher.tests.api import base


class FakeRequest(object):
    def __init__(self, headers, context, environ):
        self.headers = headers
        self.context = context
        self.environ = environ or {}
        self.version = (1, 0)
        self.host_url = 'http://127.0.0.1:6385'


class FakeRequestState(object):
    def __init__(self, headers=None, context=None, environ=None):
        self.request = FakeRequest(headers, context, environ)
        self.response = FakeRequest(headers, context, environ)

    def set_context(self):
        headers = self.request.headers
        creds = {
            'user': headers.get('X-User') or headers.get('X-User-Id'),
            'domain_id': headers.get('X-User-Domain-Id'),
            'domain_name': headers.get('X-User-Domain-Name'),
            'auth_token': headers.get('X-Auth-Token'),
            'roles': headers.get('X-Roles', '').split(','),
        }
        is_admin = ('admin' in creds['roles'] or
                    'administrator' in creds['roles'])
        is_public_api = self.request.environ.get('is_public_api', False)

        self.request.context = context.RequestContext(
            is_admin=is_admin, is_public_api=is_public_api, **creds)


def fake_headers(admin=False):
    headers = {
        'X-Auth-Token': '8d9f235ca7464dd7ba46f81515797ea0',
        'X-Domain-Id': 'None',
        'X-Domain-Name': 'None',
        'X-Project-Domain-Id': 'default',
        'X-Project-Domain-Name': 'Default',
        'X-Role': '_member_,admin',
        'X-Roles': '_member_,admin',
        # 'X-Tenant': 'foo',
        # 'X-Tenant-Id': 'b4efa69d4ffa4973863f2eefc094f7f8',
        # 'X-Tenant-Name': 'foo',
        'X-User': 'foo',
        'X-User-Domain-Id': 'default',
        'X-User-Domain-Name': 'Default',
        'X-User-Id': '604ab2a197c442c2a84aba66708a9e1e',
        'X-User-Name': 'foo',
    }
    if admin:
        headers.update({
            'X-Project-Name': 'admin',
            'X-Role': '_member_,admin',
            'X-Roles': '_member_,admin',
            'X-Tenant': 'admin',
            # 'X-Tenant-Name': 'admin',
            # 'X-Tenant': 'admin'
            'X-Tenant-Name': 'admin',
            'X-Tenant-Id': 'c2a3a69d456a412376efdd9dac38',
            'X-Project-Name': 'admin',
            'X-Project-Id': 'c2a3a69d456a412376efdd9dac38',
        })
    else:
        headers.update({
            'X-Role': '_member_',
            'X-Roles': '_member_',
            'X-Tenant': 'foo',
            'X-Tenant-Name': 'foo',
            'X-Tenant-Id': 'b4efa69d,4ffa4973863f2eefc094f7f8',
            'X-Project-Name': 'foo',
            'X-Project-Id': 'b4efa69d4ffa4973863f2eefc094f7f8',
        })
    return headers


class TestNoExceptionTracebackHook(base.FunctionalTest):

    TRACE = ['Traceback (most recent call last):',
             '  File "/opt/stack/watcher/watcher/common/rpc/amqp.py",'
             ' line 434, in _process_data\\n   **args)',
             '  File "/opt/stack/watcher/watcher/common/rpc/'
             'dispatcher.py", line 172, in dispatch\\n   result ='
             ' getattr(proxyobj, method)(ctxt, **kwargs)']
    MSG_WITHOUT_TRACE = "Test exception message."
    MSG_WITH_TRACE = MSG_WITHOUT_TRACE + "\n" + "\n".join(TRACE)

    def setUp(self):
        super(TestNoExceptionTracebackHook, self).setUp()
        p = mock.patch.object(root.Root, 'convert')
        self.root_convert_mock = p.start()
        self.addCleanup(p.stop)
        cfg.CONF.set_override('debug', False)

    def test_hook_exception_success(self):
        self.root_convert_mock.side_effect = Exception(self.MSG_WITH_TRACE)

        response = self.get_json('/', path_prefix='', expect_errors=True)

        actual_msg = jsonutils.loads(
            response.json['error_message'])['faultstring']
        self.assertEqual(self.MSG_WITHOUT_TRACE, actual_msg)

    def test_hook_remote_error_success(self):
        test_exc_type = 'TestException'
        self.root_convert_mock.side_effect = messaging.rpc.RemoteError(
            test_exc_type, self.MSG_WITHOUT_TRACE, self.TRACE)

        response = self.get_json('/', path_prefix='', expect_errors=True)

        # NOTE(max_lobur): For RemoteError the client message will still have
        # some garbage because in RemoteError traceback is serialized as a list
        # instead of'\n'.join(trace). But since RemoteError is kind of very
        # rare thing (happens due to wrong deserialization settings etc.)
        # we don't care about this garbage.
        expected_msg = ("Remote error: %s %s"
                        % (test_exc_type, self.MSG_WITHOUT_TRACE) +
                        "\n['")
        actual_msg = jsonutils.loads(
            response.json['error_message'])['faultstring']
        self.assertEqual(expected_msg, actual_msg)

    def _test_hook_without_traceback(self):
        msg = "Error message without traceback \n but \n multiline"
        self.root_convert_mock.side_effect = Exception(msg)

        response = self.get_json('/', path_prefix='', expect_errors=True)

        actual_msg = jsonutils.loads(
            response.json['error_message'])['faultstring']
        self.assertEqual(msg, actual_msg)

    def test_hook_without_traceback(self):
        self._test_hook_without_traceback()

    def test_hook_without_traceback_debug(self):
        cfg.CONF.set_override('debug', True)
        self._test_hook_without_traceback()

    def _test_hook_on_serverfault(self):
        self.root_convert_mock.side_effect = Exception(self.MSG_WITH_TRACE)

        response = self.get_json('/', path_prefix='', expect_errors=True)

        actual_msg = jsonutils.loads(
            response.json['error_message'])['faultstring']
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

        actual_msg = jsonutils.loads(
            response.json['error_message'])['faultstring']
        return actual_msg

    def test_hook_on_clientfault(self):
        msg = self._test_hook_on_clientfault()
        self.assertEqual(self.MSG_WITHOUT_TRACE, msg)

    def test_hook_on_clientfault_debug_tracebacks(self):
        cfg.CONF.set_override('debug', True)
        msg = self._test_hook_on_clientfault()
        self.assertEqual(self.MSG_WITH_TRACE, msg)


class TestContextHook(base.FunctionalTest):
    @mock.patch.object(context, 'RequestContext')
    def test_context_hook_not_admin(self, mock_ctx):
        cfg.CONF.set_override(
            'auth_type', 'password', group='watcher_clients_auth')
        headers = fake_headers(admin=False)
        reqstate = FakeRequestState(headers=headers)
        context_hook = hooks.ContextHook()
        context_hook.before(reqstate)
        mock_ctx.assert_called_with(
            auth_token=headers['X-Auth-Token'],
            user=headers['X-User'],
            user_id=headers['X-User-Id'],
            domain_id=headers['X-User-Domain-Id'],
            domain_name=headers['X-User-Domain-Name'],
            project=headers['X-Project-Name'],
            project_id=headers['X-Project-Id'],
            show_deleted=None,
            auth_token_info=self.token_info,
            roles=headers['X-Roles'].split(','))

    @mock.patch.object(context, 'RequestContext')
    def test_context_hook_admin(self, mock_ctx):
        cfg.CONF.set_override(
            'auth_type', 'password', group='watcher_clients_auth')
        headers = fake_headers(admin=True)
        reqstate = FakeRequestState(headers=headers)
        context_hook = hooks.ContextHook()
        context_hook.before(reqstate)
        mock_ctx.assert_called_with(
            auth_token=headers['X-Auth-Token'],
            user=headers['X-User'],
            user_id=headers['X-User-Id'],
            domain_id=headers['X-User-Domain-Id'],
            domain_name=headers['X-User-Domain-Name'],
            project=headers['X-Project-Name'],
            project_id=headers['X-Project-Id'],
            show_deleted=None,
            auth_token_info=self.token_info,
            roles=headers['X-Roles'].split(','))

    @mock.patch.object(context, 'RequestContext')
    def test_context_hook_public_api(self, mock_ctx):
        cfg.CONF.set_override(
            'auth_type', 'password', group='watcher_clients_auth')
        headers = fake_headers(admin=True)
        env = {'is_public_api': True}
        reqstate = FakeRequestState(headers=headers, environ=env)
        context_hook = hooks.ContextHook()
        context_hook.before(reqstate)
        mock_ctx.assert_called_with(
            auth_token=headers['X-Auth-Token'],
            user=headers['X-User'],
            user_id=headers['X-User-Id'],
            domain_id=headers['X-User-Domain-Id'],
            domain_name=headers['X-User-Domain-Name'],
            project=headers['X-Project-Name'],
            project_id=headers['X-Project-Id'],
            show_deleted=None,
            auth_token_info=self.token_info,
            roles=headers['X-Roles'].split(','))
