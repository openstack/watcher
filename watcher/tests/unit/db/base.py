# Copyright (c) 2012 NTT DOCOMO, INC.
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

"""Watcher DB test base class."""
import os
import sqlite3
import tempfile

import fixtures
from oslo_config import cfg
from oslo_db.sqlalchemy import enginefacade
from oslo_db.sqlalchemy import test_fixtures


from watcher.db import api as dbapi
from watcher.db.sqlalchemy import migration
from watcher.tests.fixtures import db_lock as db_fixture
from watcher.tests.unit import base
from watcher.tests.unit.db import utils


CONF = cfg.CONF

CONF.import_opt('enable_authentication', 'watcher.api.acl')


class SqliteDatabaseFixture(test_fixtures.GeneratesSchema,
                            test_fixtures.AdHocDbFixture):
    """oslo_db-based fixture for SQLite-backed tests.

    This uses oslo_db's AdHocDbFixture to provision a per-test (or per-run)
    SQLite database and GenerateSchema to build the Watcher schema via the
    normal migration helpers.
    """

    def __init__(self):
        # Use the configured database connection URL
        # (set to sqlite:// in tests)
        super().__init__(url=CONF.database.connection)

    def generate_schema_create_all(self, engine):
        """Generate the database schema for tests using migrations helpers."""
        migration.create_schema(engine=engine)


class DbTestCase(base.TestCase):

    def get_next_id(self):
        return next(self._id_gen)

    def setUp(self):
        CONF.set_override("enable_authentication", False)
        # Creates a temporary dir to hold sqlite temp files
        # and patch tempile to use it as default dir.
        self.useFixture(fixtures.NestedTempfile())

        # NOTE(dviroel): Using file-backed database to support multiple
        # native thread, since each one can have its own connection to
        # the database. Files created by SQLite will be cleaned up
        # by the NestedTempfile fixture.
        fd, dbfile_path = tempfile.mkstemp(prefix="watcher_test_",
                                           suffix=".db")
        # close the file descriptor before SQLite connects
        os.close(fd)
        CONF.set_override(
            "connection", f"sqlite:///{dbfile_path}", group="database")

        # Enable WAL journaling mode: "WAL provides more concurrency as
        # readers do not block writers and a writer does not block readers."
        # Note that WAL journal mode is persistent, if we close and reopen
        # the database, it will come back in WAL mode.
        # More info at: https://www.sqlite.org/wal.html
        with sqlite3.connect(dbfile_path) as conn:
            res = conn.execute("PRAGMA journal_mode=WAL")
            self.assertEqual(res.fetchone()[0], 'wal')

        super().setUp()

        # NOTE(dviroel): Creates a new enginefacade for each test,
        # and use the fixture to replace the application level factory
        # with the local one. This avoids issue with factory global flags
        # that can avoid re-configuring the database.
        local_enginefacade = enginefacade.transaction_context()
        local_enginefacade.configure(
            connection=CONF.database.connection,
            sqlite_synchronous=CONF.database.sqlite_synchronous)

        self.useFixture(
            test_fixtures.ReplaceEngineFacadeFixture(
                enginefacade._context_manager, local_enginefacade))

        # Provision and configure a SQLite database for this test using
        # oslo_db's fixtures.
        self.useFixture(SqliteDatabaseFixture())
        # NOTE(dviroel): SQLite support only a single writer per database
        # and we still miss the support retrying on a "Database is Locked"
        # error.
        self.useFixture(db_fixture.DatabaseWriteLock())
        self.dbapi = dbapi.get_instance()
        self._id_gen = utils.id_generator()


class MySQLDbTestCase(test_fixtures.OpportunisticDBTestMixin, base.TestCase):

    FIXTURE = test_fixtures.MySQLOpportunisticFixture

    def setUp(self):
        conn_str = "mysql+pymysql://root:insecure_slave@127.0.0.1"
        # to use mysql db
        cfg.CONF.set_override("connection", conn_str,
                              group="database")
        super().setUp()
        self.engine = enginefacade.writer.get_engine()
        self.dbapi = dbapi.get_instance()
        migration.create_schema()
