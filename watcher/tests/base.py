# Copyright 2010-2011 OpenStack Foundation
# Copyright (c) 2013 Hewlett-Packard Development Company, L.P.
#
# Licensed under the Apache License, Version 2.0 (the "License"); you may
# not use this file except in compliance with the License. You may obtain
# a copy of the License at
#
#      http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS, WITHOUT
# WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied. See the
# License for the specific language governing permissions and limitations
# under the License.

import copy
import os
from unittest import mock

import fixtures
from oslo_config import cfg
from oslo_log import log
from oslo_messaging import conffixture
from oslotest import base
import pecan
from pecan import testing
import testscenarios

from watcher.common import context as watcher_context
from watcher.common import service
from watcher.objects import base as objects_base
from watcher.tests import conf_fixture
from watcher.tests.fixtures import watcher as watcher_fixtures
from watcher.tests import policy_fixture


CONF = cfg.CONF
try:
    log.register_options(CONF)
except cfg.ArgsAlreadyParsedError:
    pass
CONF.set_override('use_stderr', False)


class BaseTestCase(testscenarios.WithScenarios, base.BaseTestCase):
    """Test base class."""

    def setUp(self):
        # Ensure BaseTestCase's ConfigureLogging fixture is disabled since
        # we're using our own (StandardLogging).
        with fixtures.EnvironmentVariable('OS_LOG_CAPTURE', '0'):
            super(BaseTestCase, self).setUp()
        self.stdlog = self.useFixture(watcher_fixtures.StandardLogging())
        self.addCleanup(cfg.CONF.reset)


class TestCase(BaseTestCase):
    """Test case base class for all unit tests."""

    def setUp(self):
        super(TestCase, self).setUp()
        self.useFixture(conf_fixture.ConfReloadFixture())
        self.policy = self.useFixture(policy_fixture.PolicyFixture())
        self.messaging_conf = self.useFixture(conffixture.ConfFixture(CONF))
        self.messaging_conf.transport_url = 'fake:/'

        cfg.CONF.set_override("auth_type", "admin_token",
                              group='keystone_authtoken')

        app_config_path = os.path.join(os.path.dirname(__file__), 'config.py')
        self.app = testing.load_test_app(app_config_path)
        self.token_info = {
            'token': {
                'project': {
                    'id': 'fake_project'
                },
                'user': {
                    'id': 'fake_user'
                }
            }
        }

        objects_base.WatcherObject.indirection_api = None

        self.context = watcher_context.RequestContext(
            auth_token_info=self.token_info,
            project_id='fake_project',
            user_id='fake_user')

        self.policy = self.useFixture(policy_fixture.PolicyFixture())

        def make_context(*args, **kwargs):
            # If context hasn't been constructed with token_info
            if not kwargs.get('auth_token_info'):
                kwargs['auth_token_info'] = copy.deepcopy(self.token_info)
            if not kwargs.get('project_id'):
                kwargs['project_id'] = 'fake_project'
            if not kwargs.get('user_id'):
                kwargs['user_id'] = 'fake_user'

            context = watcher_context.RequestContext(*args, **kwargs)
            return watcher_context.RequestContext.from_dict(context.to_dict())

        p = mock.patch.object(watcher_context, 'make_context',
                              side_effect=make_context)
        self.mock_make_context = p.start()
        self.addCleanup(p.stop)

        self.useFixture(conf_fixture.ConfFixture(cfg.CONF))
        self._reset_singletons()

        self._base_test_obj_backup = copy.copy(
            objects_base.WatcherObjectRegistry._registry._obj_classes)
        self.addCleanup(self._restore_obj_registry)
        self.addCleanup(self._reset_singletons)

    def _reset_singletons(self):
        service.Singleton._instances.clear()

        def reset_pecan():
            pecan.set_config({}, overwrite=True)

        self.addCleanup(reset_pecan)

    def _restore_obj_registry(self):
        objects_base.WatcherObjectRegistry._registry._obj_classes = (
            self._base_test_obj_backup)

    def config(self, **kw):
        """Override config options for a test."""
        group = kw.pop('group', None)
        for k, v in kw.items():
            CONF.set_override(k, v, group)

    def get_path(self, project_file=None):
        """Get the absolute path to a file. Used for testing the API.

        :param project_file: File whose path to return. Default: None.
        :returns: path to the specified file, or path to project root.
        """
        root = os.path.abspath(
            os.path.join(os.path.dirname(__file__), '..', '..'))
        if project_file:
            return os.path.join(root, project_file)
        else:
            return root
