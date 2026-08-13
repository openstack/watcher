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

import logging as std_logging
import os
import warnings

from unittest import mock

import fixtures

from oslo_config import cfg
from oslo_log import log
from oslo_log.fixture import logging_error
from oslotest import output
from sqlalchemy import exc as sqla_exc

from watcher import objects
from watcher.common import context as watcher_context
from watcher.common import service as watcher_service
from watcher.decision_engine import sync
from watcher.decision_engine.model import model_root
from watcher.objects import base as objects_base
from watcher.tests import base as watcher_base
from watcher.tests.functional.api.client import WatcherTestClient
from watcher.tests.local_fixtures import conf_fixture
from watcher.tests.local_fixtures import db as db_fixture
from watcher.tests.local_fixtures import policy_fixture
from watcher.tests.local_fixtures import rpc as rpc_fixture
from watcher.tests.local_fixtures import watcher as watcher_fixtures
from watcher.tests.local_fixtures.api import APIFixture
from watcher.tests.local_fixtures.cast_as_call import CastAsCallFixture
from watcher.tests.local_fixtures.service import ServiceFixture


FAKE_USER_UUID = 'bbbbbbbb-1111-2222-3333-444444444444'
FAKE_PROJECT_UUID = 'aaaaaaaa-1111-2222-3333-444444444444'

CONF = cfg.CONF
try:
    log.register_options(CONF)
except cfg.ArgsAlreadyParsedError:
    pass
CONF.set_override('use_stderr', False)


class WatcherEnvironment(fixtures.Fixture):
    """Shared Watcher test environment.

    Sets up messaging, configuration, policy, database, OVO classes,
    goal/strategy sync, collectors, RPC cast-as-call, Keystone mock,
    optional services, and an admin context.

    Used by both WatcherFunctionalTestCase (Python tests) and
    WatcherGabbiFixture (YAML-driven gabbi tests).
    """

    def __init__(
        self,
        start_de=True,
        start_applier=True,
        log_name=None,
        cast_as_call=True,
    ):
        super().__init__()
        self.start_de = start_de
        self.start_applier = start_applier
        self.log_name = log_name
        self._cast_as_call = cast_as_call
        self.dbapi = None
        self.context = None

    def setUp(self):
        super().setUp()

        # 0. Logging, output capture, and warnings
        self.stdlog = self.useFixture(watcher_fixtures.StandardLogging())
        self.useFixture(output.CaptureOutput())
        self.useFixture(logging_error.get_logging_handle_error_fixture())
        self.useFixture(WarningsFixture())

        log_dir = os.environ.get('WATCHER_FUNC_TEST_LOG_DIR')
        if log_dir and self.log_name:
            os.makedirs(log_dir, exist_ok=True)
            safe_name = self.log_name.replace('/', '_')
            log_path = os.path.join(log_dir, '%s.log' % safe_name)
            handler = std_logging.FileHandler(log_path)
            handler.setLevel(std_logging.DEBUG)
            handler.setFormatter(
                std_logging.Formatter(
                    '%(asctime)s %(levelname)s [%(name)s] %(message)s'
                )
            )
            std_logging.getLogger().addHandler(handler)
            self.addCleanup(std_logging.getLogger().removeHandler, handler)
            self.addCleanup(handler.close)

        # 1. Messaging — MUST be before ConfReloadFixture because
        #    config.parse_args() calls rpc.init(CONF) which needs
        #    the fake:/ transport URL already configured.
        self.useFixture(rpc_fixture.RPCFixture())

        # 2. Configuration — calls config.parse_args → rpc.init
        self.useFixture(conf_fixture.ConfReloadFixture())

        # 3. Policy
        self.useFixture(policy_fixture.PolicyFixture())

        # 4. Database
        CONF.set_override('enable_authentication', False)
        self._db = self.useFixture(db_fixture.WatcherDatabase())
        self.dbapi = self._db.dbapi

        # 5. Register OVO classes
        objects_base.WatcherObject.indirection_api = None
        objects.register_all()

        # 6. Sync goals and strategies from stevedore plugins to DB
        syncer = sync.Syncer()
        syncer.sync()

        # 7. Disable all collectors — functional tests don't need real
        #    OpenStack services. Provide a fake empty model so strategies
        #    that check self.compute_model in pre_execute() don't fail.
        #    These fake model will be remove once we have nova fixtures
        #    in place.
        CONF.set_override('collector_plugins', [], group='collector')
        fake_model = model_root.ModelRoot(stale=False)
        fake_scope_handler = mock.Mock()
        fake_scope_handler.get_scoped_model.return_value = fake_model
        fake_collector = mock.Mock()
        fake_collector.get_latest_cluster_data_model.return_value = fake_model
        fake_collector.get_audit_scope_handler.return_value = (
            fake_scope_handler
        )
        self.useFixture(
            fixtures.MockPatch(
                'watcher.decision_engine.model.collector.manager'
                '.CollectorManager.get_cluster_model_collector',
                return_value=fake_collector,
            )
        )

        # 8. Make RPC casts synchronous for deterministic tests
        if self._cast_as_call:
            self.useFixture(CastAsCallFixture())

        # 9. Mock Keystone client
        self.useFixture(watcher_fixtures.KeystoneClient())

        # 10. Services
        if self.start_de:
            self.de_fixture = self.useFixture(
                ServiceFixture('watcher-decision-engine')
            )
        if self.start_applier:
            self.applier_fixture = self.useFixture(
                ServiceFixture('watcher-applier')
            )

        # 11. Admin context for direct DB operations
        self.context = watcher_context.make_context(
            user_id=FAKE_USER_UUID, project_id=FAKE_PROJECT_UUID, is_admin=True
        )

        # Reset singletons on cleanup
        self.addCleanup(watcher_service.Singleton._instances.clear)


class WarningsFixture(fixtures.Fixture):
    """Filter or escalate warnings during test runs.

    Escalates certain warnings to errors so tests fail loudly
    on real problems (unmapped SQLAlchemy columns, invalid UUIDs).
    Silences noisy but harmless warnings (policy scope, SA
    deprecations from vendored code).
    """

    def setUp(self):
        super().setUp()
        self._original_filters = warnings.filters[:]
        self.addCleanup(self._reset)

        warnings.simplefilter('once', DeprecationWarning)

        # Escalate SQLAlchemy warnings from Watcher code to errors
        warnings.filterwarnings('error', category=sqla_exc.SAWarning)
        warnings.filterwarnings(
            'error', module='watcher', category=sqla_exc.SADeprecationWarning
        )

        # But ignore SA deprecation warnings from third-party code
        warnings.filterwarnings(
            'ignore', category=sqla_exc.SADeprecationWarning
        )

        # Ignore policy scope warnings (new RBAC system)
        warnings.filterwarnings(
            'ignore',
            message='Policy .* failed scope check',
            category=UserWarning,
        )

    def _reset(self):
        warnings.filters[:] = self._original_filters


class WatcherFunctionalTestCase(watcher_base.WatcherBaseTestCase):
    """Base class for Watcher functional tests.

    Provides a fully wired test environment with:
    - Real database (file-backed SQLite with WAL journaling)
    - Real RPC messaging (oslo.messaging fake:/ driver)
    - Real Pecan WSGI application (via wsgi-intercept)
    - Optional in-process decision engine and applier services

    External services (Nova, Gnocchi, Keystone) are mocked.

    Override START_DECISION_ENGINE / START_APPLIER in subclasses
    to control which services are started.
    """

    START_DECISION_ENGINE = True
    START_APPLIER = True
    CAST_AS_CALL = True

    def setUp(self):
        super().setUp()

        self.env = self.useFixture(
            WatcherEnvironment(
                start_de=self.START_DECISION_ENGINE,
                start_applier=self.START_APPLIER,
                log_name=self.id(),
                cast_as_call=self.CAST_AS_CALL,
            )
        )
        self.dbapi = self.env.dbapi
        self.context = self.env.context
        if self.START_DECISION_ENGINE:
            self.de_fixture = self.env.de_fixture
        if self.START_APPLIER:
            self.applier_fixture = self.env.applier_fixture

        # 3. API via wsgi-intercept
        self.api_fixture = self.useFixture(APIFixture())
        self.api = WatcherTestClient(self.api_fixture.base_url)
        self.admin_api = WatcherTestClient(
            self.api_fixture.base_url, user_id=FAKE_USER_UUID, roles=['admin']
        )
